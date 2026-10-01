const { Op } = require('sequelize')
const { Comment, Project, User, CommentLike } = require('../models')
const ApiError = require('../utils/ApiError')
const { stripEmoji, hasEmoji } = require('../utils/textSanitize')
const { bumpCounter } = require('../utils/counter')
const notificationService = require('./notification.service')
const activityLogService = require('./activityLog.service')
const { clampInt, MAX_PAGE } = require('../utils/pagination')

const MAX_CONTENT_LEN = 500

// 数据库行 -> 前端数据形状
const toClientComment = (comment, extra = {}) => {
  const row = comment.toJSON ? comment.toJSON() : comment
  return {
    id: row.id,
    parentId: row.parent_id || null,
    content: row.content,
    createdAt: row.created_at,
    likeCount: row.like_count || 0,
    user: row.user
      ? { id: row.user.id, username: row.user.username, avatar: row.user.avatar || '' }
      : null,
    ...extra
  }
}

// 组装带作者信息的评论行
const withUser = { model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }

// ---------- @ 提及 ----------
// 提及语法：@ 到空白或常见标点为止。用户名本身可含中文/字母/数字（2-20 字符），
// 含空格的名字无法被 @ 完整表达（@张 三 只会命中 @张）——识别口径以这里为准，
// 前端高亮只认响应里的 mentions，不会出现假高亮。
const MENTION_RE = /@([^\s@，。！？；、：,.;:!?"'（）【】《》<>{}()]+)/g

// 从文本提取候选名：去重 + 长度与用户名上下限对齐（2-20），
// 超长 token 截断后大概率查不到 -> 静默忽略，不会误伤
const extractMentionNames = (content) => {
  const names = new Set()
  for (const m of String(content || '').matchAll(MENTION_RE)) {
    const name = m[1].slice(0, 20)
    if (name.length >= 2) names.add(name)
  }
  return [...names]
}

// 候选名 -> 真实存在的用户（排除作者本人）。查不到的名字静默忽略：
// @ 错名字不该拦住评论发布；识别结果也是前端高亮的唯一口径
exports.resolveMentions = async (content, authorUserId) => {
  const names = extractMentionNames(content)
  if (!names.length) return []
  const users = await User.findAll({
    where: { username: { [Op.in]: names } },
    attributes: ['id', 'username']
  })
  return users.filter((u) => u.id !== authorUserId)
}

exports.listComments = async ({ projectId, page = 1, pageSize = 20, currentUserId }) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 20 })
  const offset = (page - 1) * limit

  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const isProjectOwner = currentUserId != null && project.creator_id === currentUserId
  const canDelete = (userId) => isProjectOwner || (currentUserId != null && userId === currentUserId)

  // 两级结构：根评论分页，回复一次性取回并按根分组
  const { rows: rootRows } = await Comment.findAndCountAll({
    where: { project_id: projectId, parent_id: null },
    include: [withUser],
    // id 兜底排序：同一秒内发的多条评论顺序必须稳定可复现，
    // 否则 locateComment 算出的页号会和实际分页错位
    order: [['created_at', 'DESC'], ['id', 'DESC']],
    limit,
    offset,
    distinct: true
  })

  const rootIds = rootRows.map((r) => r.id)
  const replyRows = rootIds.length
    ? await Comment.findAll({
        where: { project_id: projectId, parent_id: { [Op.in]: rootIds } },
        include: [withUser],
        order: [['created_at', 'ASC']]
      })
    : []

  const repliesByRoot = new Map()
  for (const reply of replyRows) {
    const list = repliesByRoot.get(reply.parent_id) || []
    list.push(toClientComment(reply, { canDelete: canDelete(reply.user_id) }))
    repliesByRoot.set(reply.parent_id, list)
  }

  // 当前用户的点赞状态（一次查出本页所有评论的点赞记录）
  const allIds = [...rootIds, ...replyRows.map((r) => r.id)]
  let likedSet = new Set()
  if (currentUserId != null && allIds.length) {
    const likes = await CommentLike.findAll({
      where: { user_id: currentUserId, comment_id: { [Op.in]: allIds } },
      attributes: ['comment_id']
    })
    likedSet = new Set(likes.map((l) => l.comment_id))
  }
  const liked = (id) => likedSet.has(id)

  // @ 提及高亮口径：整页评论（根 + 回复）的候选名一次查库，
  // 只有真实存在的用户名才进 mentionNames —— 前端高亮与后端识别同口径，不会假高亮
  const allNames = [...rootRows, ...replyRows].flatMap((r) => extractMentionNames(r.content))
  const mentionNames = allNames.length
    ? (
        await User.findAll({
          where: { username: { [Op.in]: [...new Set(allNames)] } },
          attributes: ['username']
        })
      ).map((u) => u.username)
    : []

  const total = await Comment.count({ where: { project_id: projectId } })

  return {
    comments: rootRows.map((row) =>
      toClientComment(row, {
        canDelete: canDelete(row.user_id),
        liked: liked(row.id),
        replyCount: (repliesByRoot.get(row.id) || []).length,
        replies: (repliesByRoot.get(row.id) || []).map((r) => ({ ...r, liked: liked(r.id) }))
      })
    ),
    total,
    // 顶层带本页真实存在的 @ 用户名，前端对根评论与回复统一用它高亮
    mentionNames,
    // 根评论数：分页只翻根评论，「还有没有下一页」必须按它算。
    // 拿 total（含回复）算的话，有回复的项目会出现永远点不完的假「加载更多」
    rootTotal: await Comment.count({ where: { project_id: projectId, parent_id: null } }),
    page,
    pageSize: limit
  }
}

// 深链定位：算出目标评论落在评论列表的第几页。
// 列表是「根评论分页 + 回复挂在根下」，所以回复要按它父级的位置算；
// 前端据此把「加载更多」连续点到那一页，再滚动高亮 —— 否则深链只能命中第一页
exports.locateComment = async ({ projectId, commentId, pageSize = 10 }) => {
  const limit = clampInt(pageSize, { max: 50, fallback: 10 })
  const comment = await Comment.findByPk(commentId)
  // 评论被删 / 不属于这个项目时（defaultScope 已过滤 status=0）一律当不存在
  if (!comment || Number(comment.project_id) !== Number(projectId)) {
    throw ApiError.notFound('评论不存在')
  }

  const rootId = comment.parent_id || comment.id
  const root = rootId === comment.id ? comment : await Comment.findByPk(rootId)
  if (!root) throw ApiError.notFound('评论不存在')

  // 排在它前面的根评论条数，排序规则与 listComments 一致（created_at DESC、同秒 id DESC）
  const ahead = await Comment.count({
    where: {
      project_id: projectId,
      parent_id: null,
      [Op.or]: [
        { created_at: { [Op.gt]: root.created_at } },
        { created_at: root.created_at, id: { [Op.gt]: root.id } }
      ]
    }
  })

  return {
    commentId: comment.id,
    parentId: comment.parent_id || null,
    rootId,
    page: Math.floor(ahead / limit) + 1,
    pageSize: limit
  }
}

exports.createComment = async ({ projectId, content, userId, parentId, req }) => {
  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const cleaned = stripEmoji(content)
  if (!cleaned) throw ApiError.badRequest('评论内容不能为空')
  if (cleaned.length > MAX_CONTENT_LEN) {
    throw ApiError.badRequest(`评论最多 ${MAX_CONTENT_LEN} 个字符`)
  }

  // 回复：校验目标评论属于同一项目；回复回复时展平挂到根评论（仅两级）
  let rootId = null
  let recipientUserId = project.creator_id // 评论通知项目创建者
  if (parentId) {
    let parent = await Comment.findOne({ where: { id: parentId, project_id: projectId } })
    if (!parent) throw ApiError.badRequest('回复的评论不存在或已被删除')
    if (parent.parent_id) parent = await Comment.findByPk(parent.parent_id)
    rootId = parent.id
    recipientUserId = parent.user_id // 回复通知根评论作者
  }

  const comment = await Comment.create({
    project_id: Number(projectId),
    user_id: userId,
    parent_id: rootId,
    content: cleaned
  })

  // 原子自增（并发下不丢更新，见 utils/counter.js）
  const commentCount = await bumpCounter(Project, Number(projectId), 'comment_count', 1)

  // 站内通知（自己触发的不通知自己，服务内部处理）
  notificationService.notify({
    userId: recipientUserId,
    type: rootId ? 'reply' : 'comment',
    actorId: userId,
    projectId: Number(projectId),
    commentId: comment.id
  })

  // @ 提及：逐个通知被提及的人。与评论/回复通知独立——同一个人既被回复又被 @
  // 会收两条，语义不同；notify 内部已挡「自己 @ 自己」
  const mentions = await exports.resolveMentions(cleaned, userId)
  for (const mentioned of mentions) {
    notificationService.notify({
      userId: mentioned.id,
      type: 'mention',
      actorId: userId,
      projectId: Number(projectId),
      commentId: comment.id
    })
  }

  const full = await Comment.findByPk(comment.id, { include: [withUser] })

  // 操作日志：内容用的是**净化后**的文本（cleaned），与库里存的一致
  await activityLogService.logCommentCreated({
    userId,
    comment,
    project,
    isReply: rootId !== null,
    req
  })

  return {
    comment: toClientComment(full, { canDelete: true, liked: false, replyCount: 0, replies: [] }),
    hadEmoji: hasEmoji(content),
    mentions: mentions.map((m) => ({ id: m.id, username: m.username })),
    commentCount
  }
}

exports.deleteComment = async ({ projectId, commentId, userId, req }) => {
  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const comment = await Comment.findOne({
    where: { id: commentId, project_id: projectId }
  })
  if (!comment) throw ApiError.notFound('评论不存在或已被删除')

  // 仅评论作者或项目创建者可删除
  if (comment.user_id !== userId && project.creator_id !== userId) {
    throw ApiError.forbidden('无权删除此评论')
  }

  // 删除根评论时，回复由外键 ON DELETE CASCADE 级联清理
  const replyCount = await Comment.count({ where: { parent_id: comment.id } })
  // 日志摘要要留下「被删的是哪条」，所以先把内容摘出来（destroy 之后就取不到了）
  const removedSnapshot = { id: comment.id, content: comment.content }
  await comment.destroy()

  const removed = 1 + replyCount
  const commentCount = await bumpCounter(Project, Number(projectId), 'comment_count', -removed)

  await activityLogService.logCommentDeleted({
    userId,
    comment: removedSnapshot,
    project,
    req
  })

  return { commentCount }
}

exports.likeComment = async ({ projectId, commentId, userId }) => {
  const comment = await getCommentOr404(projectId, commentId)

  const existing = await CommentLike.findOne({ where: { comment_id: commentId, user_id: userId } })
  if (existing) throw ApiError.conflict('已点赞过该评论')

  await CommentLike.create({ comment_id: commentId, user_id: userId })
  const likeCount = await bumpCounter(Comment, comment.id, 'like_count', 1)

  // 通知评论作者（自己点赞自己不通知）
  notificationService.notify({
    userId: comment.user_id,
    type: 'like',
    actorId: userId,
    projectId: Number(projectId),
    commentId: comment.id
  })

  return { likeCount }
}

exports.unlikeComment = async ({ projectId, commentId, userId }) => {
  const comment = await getCommentOr404(projectId, commentId)

  const existing = await CommentLike.findOne({ where: { comment_id: commentId, user_id: userId } })
  if (!existing) throw ApiError.badRequest('尚未点赞该评论')

  await existing.destroy()
  const likeCount = await bumpCounter(Comment, comment.id, 'like_count', -1)
  return { likeCount }
}

const getCommentOr404 = async (projectId, commentId) => {
  const comment = await Comment.findOne({ where: { id: commentId, project_id: projectId } })
  if (!comment) throw ApiError.notFound('评论不存在或已被删除')
  return comment
}

// 评论计数与真实条数对账（供管理/修复用）
exports.recountComments = async (projectId) => {
  const count = await Comment.count({ where: { project_id: { [Op.eq]: projectId } } })
  await Project.update({ comment_count: count }, { where: { id: projectId } })
  return count
}

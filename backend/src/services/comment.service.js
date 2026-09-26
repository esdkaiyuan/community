const { Op } = require('sequelize')
const { Comment, Project, User, CommentLike } = require('../models')
const ApiError = require('../utils/ApiError')
const { stripEmoji, hasEmoji } = require('../utils/textSanitize')
const notificationService = require('./notification.service')

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

exports.listComments = async ({ projectId, page = 1, pageSize = 20, currentUserId }) => {
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize, 10) || 20))
  const offset = (page - 1) * limit

  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const isProjectOwner = currentUserId != null && project.creator_id === currentUserId
  const canDelete = (userId) => isProjectOwner || (currentUserId != null && userId === currentUserId)

  // 两级结构：根评论分页，回复一次性取回并按根分组
  const { rows: rootRows } = await Comment.findAndCountAll({
    where: { project_id: projectId, parent_id: null },
    include: [withUser],
    order: [['created_at', 'DESC']],
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
    page,
    pageSize: limit
  }
}

exports.createComment = async ({ projectId, content, userId, parentId }) => {
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

  project.comment_count += 1
  await project.save()

  // 站内通知（自己触发的不通知自己，服务内部处理）
  notificationService.notify({
    userId: recipientUserId,
    type: rootId ? 'reply' : 'comment',
    actorId: userId,
    projectId: Number(projectId),
    commentId: comment.id
  })

  const full = await Comment.findByPk(comment.id, { include: [withUser] })

  return {
    comment: toClientComment(full, { canDelete: true, liked: false, replyCount: 0, replies: [] }),
    hadEmoji: hasEmoji(content),
    commentCount: project.comment_count
  }
}

exports.deleteComment = async ({ projectId, commentId, userId }) => {
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
  await comment.destroy()

  const removed = 1 + replyCount
  project.comment_count = Math.max(0, project.comment_count - removed)
  await project.save()

  return { commentCount: project.comment_count }
}

exports.likeComment = async ({ projectId, commentId, userId }) => {
  const comment = await getCommentOr404(projectId, commentId)

  const existing = await CommentLike.findOne({ where: { comment_id: commentId, user_id: userId } })
  if (existing) throw ApiError.conflict('已点赞过该评论')

  await CommentLike.create({ comment_id: commentId, user_id: userId })
  comment.like_count += 1
  await comment.save()

  // 通知评论作者（自己点赞自己不通知）
  notificationService.notify({
    userId: comment.user_id,
    type: 'like',
    actorId: userId,
    projectId: Number(projectId),
    commentId: comment.id
  })

  return { likeCount: comment.like_count }
}

exports.unlikeComment = async ({ projectId, commentId, userId }) => {
  const comment = await getCommentOr404(projectId, commentId)

  const existing = await CommentLike.findOne({ where: { comment_id: commentId, user_id: userId } })
  if (!existing) throw ApiError.badRequest('尚未点赞该评论')

  await existing.destroy()
  if (comment.like_count > 0) {
    comment.like_count -= 1
    await comment.save()
  }
  return { likeCount: comment.like_count }
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

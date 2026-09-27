const { Op } = require('sequelize')
const sequelize = require('../config/database')
const { Project, Category, User, ProjectParticipant, ProjectLike, ProjectFavorite } = require('../models')
const ApiError = require('../utils/ApiError')
const { stripEmoji } = require('../utils/textSanitize')
const { toClientUser } = require('./user.service')
const notificationService = require('./notification.service')

// 数据库行 -> 前端数据形状（camelCase）
const toClientProject = (p, extra = {}) => {
  const row = p.toJSON ? p.toJSON() : p
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    coverImage: row.cover_image,
    categoryId: row.category_id,
    categoryName: row.category ? row.category.name : null,
    tags: Array.isArray(row.tags) ? row.tags : [],
    participantCount: row.participant_count || 0,
    likeCount: row.like_count || 0,
    commentCount: row.comment_count || 0,
    viewCount: row.view_count || 0,
    isRecommend: !!row.is_recommend,
    isHot: !!row.is_hot,
    createdAt: row.created_at,
    creator: row.creator ? toClientUser(row.creator) : null,
    ...extra
  }
}

// 共创者预览条数（详情页头像堆叠）
const PARTICIPANT_PREVIEW = 8

// 中间表行 -> 前端共创者形状（用户已注销时兜底，避免渲染空头像）
const toClientParticipant = (p) => {
  const row = p.toJSON ? p.toJSON() : p
  const user = row.user
  return {
    id: user ? user.id : row.user_id,
    username: user && user.username ? user.username : '已注销用户',
    avatar: user ? user.avatar || '' : '',
    role: row.role,
    joinedAt: row.joined_at
  }
}

// 发起人永远置顶，其余按加入时间升序
const sortParticipants = (rows) =>
  rows.slice().sort((a, b) => {
    const ac = a.role === 'creator' ? 0 : 1
    const bc = b.role === 'creator' ? 0 : 1
    if (ac !== bc) return ac - bc
    return new Date(a.joined_at).getTime() - new Date(b.joined_at).getTime()
  })

const SORT_MAP = {
  latest: [['created_at', 'DESC']],
  hot: [['like_count', 'DESC']],
  participants: [['participant_count', 'DESC']],
  recommend: [
    ['is_recommend', 'DESC'],
    ['like_count', 'DESC']
  ]
}

const getProjectOr404 = async (id) => {
  // 详情/编辑都要用 category 与 creator 的展示字段，统一在这里带出来
  const project = await Project.findByPk(id, {
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ]
  })
  if (!project) throw ApiError.notFound('项目不存在')
  return project
}

exports.listProjects = async ({
  page = 1,
  pageSize = 12,
  categoryId,
  tag,
  search,
  filter,
  sort,
  creatorId,
  favoritedBy,
  currentUserId
}) => {
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize, 10) || 12))
  const offset = (page - 1) * limit

  const where = {}
  if (categoryId) where.category_id = categoryId
  if (creatorId) where.creator_id = creatorId
  if (filter === 'recommend') where.is_recommend = 1
  if (filter === 'hot') where.is_hot = 1
  // 标签筛选：tags 列存 JSON 数组，用 JSON_CONTAINS 精确匹配，
  // 而不是 LIKE —— 否则「开源」会误命中「开源硬件」这类互含子串的标签
  if (tag) {
    where[Op.and] = [
      sequelize.where(
        sequelize.fn('JSON_CONTAINS', sequelize.col('Project.tags'), JSON.stringify(tag)),
        1
      )
    ]
  }
  if (search) {
    where[Op.or] = [
      { title: { [Op.like]: `%${search}%` } },
      { description: { [Op.like]: `%${search}%` } },
      // 关键词也命中标签：搜「开源」能找到打了该标签的项目
      { tags: { [Op.like]: `%${search}%` } }
    ]
  }

  // 「只看收藏」：先取出该用户收藏的项目 id，再据此收窄查询集合
  if (favoritedBy) {
    const favorites = await ProjectFavorite.findAll({
      where: { user_id: favoritedBy },
      attributes: ['project_id']
    })
    const ids = favorites.map((f) => f.project_id)
    if (!ids.length) return { projects: [], total: 0, page, pageSize: limit }
    where.id = { [Op.in]: ids }
  }

  const { count, rows } = await Project.findAndCountAll({
    where,
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ],
    order: SORT_MAP[sort] || SORT_MAP.latest,
    limit,
    offset,
    distinct: true
  })

  // 登录用户：批量标记本页项目的收藏状态（卡片书签徽标用），只查一次
  let favoritedIds = null
  if (currentUserId && rows.length) {
    const favorites = await ProjectFavorite.findAll({
      where: { user_id: currentUserId, project_id: { [Op.in]: rows.map((r) => r.id) } },
      attributes: ['project_id']
    })
    favoritedIds = new Set(favorites.map((f) => f.project_id))
  }

  return {
    projects: rows.map((row) =>
      toClientProject(row, favoritedIds ? { favorited: favoritedIds.has(row.id) } : {})
    ),
    total: count,
    page,
    pageSize: limit
  }
}

// 标签是 projects.tags 里的 JSON 数组（无独立表），这里全量聚合出「热门标签」
// 数据量小、也无索引可用，直接拉非空行在内存里计数；随项目增长可改为定时物化
exports.listPopularTags = async ({ limit = 12 } = {}) => {
  const max = Math.min(30, Math.max(1, parseInt(limit, 10) || 12))

  const rows = await Project.findAll({
    attributes: ['tags'],
    where: { tags: { [Op.ne]: null } }
  })

  const counter = new Map()
  rows.forEach((row) => {
    const list = Array.isArray(row.tags) ? row.tags : []
    list.forEach((raw) => {
      const name = String(raw || '').trim()
      if (!name) return
      counter.set(name, (counter.get(name) || 0) + 1)
    })
  })

  // 项目数倒序；数量相同按名称稳定排序，避免每次刷新顺序抖动
  return [...counter.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'zh'))
    .slice(0, max)
}

exports.getProjectDetail = async (id, currentUserId) => {
  const project = await getProjectOr404(id)

  // 浏览量异步累加，不阻塞响应
  Project.update({ view_count: project.view_count + 1 }, { where: { id } }).catch(() => {})

  const [participantRows, participantTotal, liked, participated, favorited] = await Promise.all([
    ProjectParticipant.findAll({
      where: { project_id: id },
      include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }],
      order: [['joined_at', 'ASC']],
      limit: 200
    }),
    ProjectParticipant.count({ where: { project_id: id } }),
    currentUserId ? ProjectLike.findOne({ where: { project_id: id, user_id: currentUserId } }) : null,
    currentUserId ? ProjectParticipant.findOne({ where: { project_id: id, user_id: currentUserId } }) : null,
    currentUserId ? ProjectFavorite.findOne({ where: { project_id: id, user_id: currentUserId } }) : null
  ])

  // 历史数据可能存在计数漂移：以中间表真实行数为准，并异步回写自愈
  if (project.participant_count !== participantTotal) {
    Project.update({ participant_count: participantTotal }, { where: { id } }).catch(() => {})
  }

  // 详情页只带预览条数，完整名单走 /projects/:id/participants
  const extra = {
    participantCount: participantTotal,
    participants: sortParticipants(participantRows)
      .slice(0, PARTICIPANT_PREVIEW)
      .map(toClientParticipant)
  }
  if (currentUserId) {
    extra.liked = !!liked
    extra.participated = !!participated
    extra.favorited = !!favorited
  }

  return toClientProject(project, extra)
}

exports.listParticipants = async (id, { page = 1, pageSize = 24 } = {}) => {
  await getProjectOr404(id)
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(60, Math.max(1, parseInt(pageSize, 10) || 24))
  const offset = (page - 1) * limit

  const { count, rows } = await ProjectParticipant.findAndCountAll({
    where: { project_id: id },
    include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }],
    order: [['joined_at', 'ASC']],
    limit,
    offset
  })

  return {
    // 分页列表保持数据库顺序（joined_at 升序），分页切片后才重排会跨页错位
    participants: rows.map(toClientParticipant),
    total: count,
    page,
    pageSize: limit
  }
}

exports.createProject = async ({ title, description, coverImage, categoryId, tags, creatorId }) => {
  if (!title || !String(title).trim()) throw ApiError.badRequest('标题为必填项')
  if (String(title).trim().length < 4) throw ApiError.badRequest('标题至少 4 个字符')
  if (!description || String(description).trim().length < 20) {
    throw ApiError.badRequest('项目介绍至少 20 个字符')
  }
  if (categoryId && !(await Category.findByPk(categoryId))) {
    throw ApiError.badRequest('所选分类不存在')
  }

  const project = await Project.create({
    title: String(title).trim(),
    description: stripEmoji(description) || description,
    cover_image: coverImage || null,
    category_id: categoryId || null,
    creator_id: creatorId,
    tags: Array.isArray(tags) ? tags.slice(0, 5) : []
  })

  await ProjectParticipant.create({ project_id: project.id, user_id: creatorId, role: 'creator' })
  return toClientProject(project)
}

exports.updateProject = async (id, userId, { title, description, coverImage, categoryId, tags }) => {
  const project = await getProjectOr404(id)
  if (project.creator_id !== userId) throw ApiError.forbidden('无权修改此项目')

  if (title !== undefined) {
    if (String(title).trim().length < 4) throw ApiError.badRequest('标题至少 4 个字符')
    project.title = String(title).trim()
  }
  if (description !== undefined) {
    if (String(description).trim().length < 20) throw ApiError.badRequest('项目介绍至少 20 个字符')
    project.description = stripEmoji(description) || description
  }
  if (coverImage !== undefined) project.cover_image = coverImage || null
  if (categoryId !== undefined) project.category_id = categoryId || null
  if (tags !== undefined && Array.isArray(tags)) project.tags = tags.slice(0, 5)

  await project.save()
  return toClientProject(project)
}

exports.deleteProject = async (id, userId) => {
  const project = await getProjectOr404(id)
  if (project.creator_id !== userId) throw ApiError.forbidden('无权删除此项目')
  await project.destroy()
}

exports.likeProject = async (id, userId) => {
  const project = await getProjectOr404(id)

  const existing = await ProjectLike.findOne({ where: { project_id: id, user_id: userId } })
  if (existing) throw ApiError.conflict('已点赞过该项目')

  await ProjectLike.create({ project_id: id, user_id: userId })
  project.like_count += 1
  await project.save()
  return { likeCount: project.like_count }
}

exports.unlikeProject = async (id, userId) => {
  const project = await getProjectOr404(id)

  const existing = await ProjectLike.findOne({ where: { project_id: id, user_id: userId } })
  if (!existing) throw ApiError.badRequest('尚未点赞该项目')

  await existing.destroy()
  if (project.like_count > 0) {
    project.like_count -= 1
    await project.save()
  }
  return { likeCount: project.like_count }
}

// 收藏项目（数据库唯一键兜底防重复）
exports.favoriteProject = async (id, userId) => {
  await getProjectOr404(id)

  const existing = await ProjectFavorite.findOne({ where: { project_id: id, user_id: userId } })
  if (existing) throw ApiError.conflict('已收藏过该项目')

  await ProjectFavorite.create({ project_id: id, user_id: userId })
  return { favorited: true }
}

exports.unfavoriteProject = async (id, userId) => {
  await getProjectOr404(id)

  const existing = await ProjectFavorite.findOne({ where: { project_id: id, user_id: userId } })
  if (!existing) throw ApiError.badRequest('尚未收藏该项目')

  await existing.destroy()
  return { favorited: false }
}

exports.participateProject = async (id, userId) => {
  const project = await getProjectOr404(id)

  const existing = await ProjectParticipant.findOne({ where: { project_id: id, user_id: userId } })
  if (existing) throw ApiError.conflict('已参与此项目')

  await ProjectParticipant.create({ project_id: id, user_id: userId, role: 'member' })
  project.participant_count += 1
  await project.save()

  // 通知发起人（同一人对同一项目只提醒一次，避免「退出 → 再加入」刷屏）
  notificationService.notifyOnce({
    userId: project.creator_id,
    type: 'participate',
    actorId: userId,
    projectId: Number(id)
  })

  return { participantCount: project.participant_count }
}

exports.cancelParticipate = async (id, userId) => {
  const project = await getProjectOr404(id)

  const participant = await ProjectParticipant.findOne({ where: { project_id: id, user_id: userId } })
  if (!participant) throw ApiError.badRequest('未参与此项目')
  if (participant.role === 'creator') throw ApiError.badRequest('项目创建者不能退出自己的项目')

  await participant.destroy()
  if (project.participant_count > 0) {
    project.participant_count -= 1
    await project.save()
  }
  return { participantCount: project.participant_count }
}

exports.toClientProject = toClientProject

const { Op } = require('sequelize')
const { Project, Category, User, ProjectParticipant, ProjectLike, ProjectFavorite } = require('../models')
const ApiError = require('../utils/ApiError')
const { stripEmoji } = require('../utils/textSanitize')
const { toClientUser } = require('./user.service')

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
  const project = await Project.findByPk(id)
  if (!project) throw ApiError.notFound('项目不存在')
  return project
}

exports.listProjects = async ({
  page = 1,
  pageSize = 12,
  categoryId,
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
  if (search) {
    where[Op.or] = [
      { title: { [Op.like]: `%${search}%` } },
      { description: { [Op.like]: `%${search}%` } }
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

exports.getProjectDetail = async (id, currentUserId) => {
  const project = await getProjectOr404(id)

  // 浏览量异步累加，不阻塞响应
  Project.update({ view_count: project.view_count + 1 }, { where: { id } }).catch(() => {})

  const extra = {}
  if (currentUserId) {
    const [liked, participated, favorited] = await Promise.all([
      ProjectLike.findOne({ where: { project_id: id, user_id: currentUserId } }),
      ProjectParticipant.findOne({ where: { project_id: id, user_id: currentUserId } }),
      ProjectFavorite.findOne({ where: { project_id: id, user_id: currentUserId } })
    ])
    extra.liked = !!liked
    extra.participated = !!participated
    extra.favorited = !!favorited
  }

  return toClientProject(project, extra)
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

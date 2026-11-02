// 管理台服务：概览、项目管理、用户管理、通知管理。
//
// 设计边界：
//   · 权限判断**不在这一层** —— routes 已挂 auth + requireAdmin，这里只处理业务。
//   · 每个写操作都先落库再写审计；审计失败不影响业务（activityLog.record 自身吞异常）。
//   · 列表查询一律 clampInt 收口分页，user_id 等参数不接受任意透传。
const { Op } = require('sequelize')
const sequelize = require('../config/database')
const {
  User,
  Project,
  Category,
  Comment,
  Notification,
  ActivityLog
} = require('../models')
const ApiError = require('../utils/ApiError')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const { stripEmoji, stripControlChars } = require('../utils/textSanitize')
const activityLogService = require('./activityLog.service')

const USER_ATTRS = ['id', 'username', 'email', 'avatar', 'bio', 'status', 'is_admin', 'created_at']
const PROJECT_ADMIN_ATTRS = [
  'id', 'title', 'description', 'cover_image', 'category_id', 'creator_id',
  'like_count', 'comment_count', 'participant_count', 'view_count',
  'is_recommend', 'is_hidden', 'created_at'
]
const NOTICE_MAX_LENGTH = 255
const WEEK_MS = 7 * 24 * 60 * 60 * 1000

// 只有明确出现「修改意图」才写库：PATCH 没带字段时不能把默认值当成用户意图。
const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key)

const toBoolFlag = (value, label) => {
  if (value === true || value === 1 || value === '1' || value === 'true') return 1
  if (value === false || value === 0 || value === '0' || value === 'false') return 0
  throw ApiError.badRequest(`${label}参数不合法`)
}

const toClientUser = (row) => ({
  id: row.id,
  username: row.username,
  email: row.email,
  avatar: row.avatar || '',
  bio: row.bio || '',
  status: Number(row.status) === 0 ? 0 : 1,
  isAdmin: Number(row.is_admin) === 1,
  createdAt: row.created_at
})

const toClientProject = (row) => {
  const p = row.toJSON ? row.toJSON() : row
  return {
    id: p.id,
    title: p.title,
    description: p.description,
    coverImage: p.cover_image || null,
    categoryId: p.category_id,
    categoryName: p.category ? p.category.name : null,
    creator: p.creator
      ? { id: p.creator.id, username: p.creator.username, avatar: p.creator.avatar || '' }
      : null,
    likeCount: p.like_count || 0,
    commentCount: p.comment_count || 0,
    participantCount: p.participant_count || 0,
    viewCount: p.view_count || 0,
    isRecommend: !!p.is_recommend,
    isHidden: !!p.is_hidden,
    createdAt: p.created_at
  }
}

const toClientNotification = (row) => {
  const n = row.toJSON ? row.toJSON() : row
  return {
    id: n.id,
    type: n.type,
    message: n.message || null,
    isRead: !!n.is_read,
    createdAt: n.created_at,
    recipient: n.recipient
      ? { id: n.recipient.id, username: n.recipient.username, avatar: n.recipient.avatar || '' }
      : null,
    actor: n.actor ? { id: n.actor.id, username: n.actor.username } : null,
    project: n.project ? { id: n.project.id, title: n.project.title } : null
  }
}

const NOTIFICATION_TYPES = ['comment', 'reply', 'like', 'participate', 'mention', 'system']

// ============ 概览 ============

exports.getOverview = async () => {
  const weekAgo = new Date(Date.now() - WEEK_MS)

  const [
    userTotal,
    userActive,
    userDisabled,
    adminCount,
    projectTotal,
    projectHidden,
    projectRecommend,
    projectNew,
    commentTotal,
    commentNew,
    notificationTotal,
    notificationUnread,
    notificationSystem
  ] = await Promise.all([
    User.count(),
    User.count({ where: { status: 1 } }),
    User.count({ where: { status: 0 } }),
    User.count({ where: { is_admin: 1 } }),
    Project.count(),
    Project.count({ where: { is_hidden: 1 } }),
    Project.count({ where: { is_recommend: 1 } }),
    Project.count({ where: { created_at: { [Op.gte]: weekAgo } } }),
    Comment.count(),
    Comment.count({ where: { created_at: { [Op.gte]: weekAgo } } }),
    Notification.count(),
    Notification.count({ where: { is_read: 0 } }),
    Notification.count({ where: { type: 'system' } })
  ])

  const [recentUsers, recentProjects, recentAdminActivity] = await Promise.all([
    User.findAll({
      attributes: USER_ATTRS,
      order: [['created_at', 'DESC']],
      limit: 5
    }),
    Project.findAll({
      attributes: PROJECT_ADMIN_ATTRS,
      include: [
        { model: Category, as: 'category', attributes: ['id', 'name'] },
        { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
      ],
      order: [['created_at', 'DESC']],
      limit: 5
    }),
    ActivityLog.findAll({
      where: {
        action: {
          [Op.in]: [
            'admin.project.update',
            'admin.project.delete',
            'admin.user.update',
            'admin.notice.send',
            'admin.notification.delete'
          ]
        }
      },
      order: [['created_at', 'DESC'], ['id', 'DESC']],
      limit: 5
    })
  ])

  return {
    users: {
      total: userTotal,
      active: userActive,
      disabled: userDisabled,
      admins: adminCount
    },
    projects: {
      total: projectTotal,
      hidden: projectHidden,
      recommend: projectRecommend,
      newThisWeek: projectNew
    },
    comments: { total: commentTotal, newThisWeek: commentNew },
    notifications: {
      total: notificationTotal,
      unread: notificationUnread,
      system: notificationSystem
    },
    recentUsers: recentUsers.map(toClientUser),
    recentProjects: recentProjects.map(toClientProject),
    recentAdminActivity: recentAdminActivity.map((row) => ({
      id: row.id,
      action: row.action,
      summary: row.summary,
      createdAt: row.created_at
    }))
  }
}

// ============ 项目管理 ============

const PROJECT_STATE_FILTERS = {
  hidden: { is_hidden: 1 },
  visible: { is_hidden: 0 },
  recommend: { is_recommend: 1 }
}

exports.listProjects = async ({ page = 1, pageSize = 10, state, search, sort } = {}) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 10 })
  const offset = (page - 1) * limit

  const where = {}
  // 筛选值来自 URL，认不出就退化成「全部」，不拼进 SQL
  if (Object.prototype.hasOwnProperty.call(PROJECT_STATE_FILTERS, state)) {
    Object.assign(where, PROJECT_STATE_FILTERS[state])
  }
  const keyword = typeof search === 'string' ? search.trim() : ''
  if (keyword) where.title = { [Op.like]: `%${keyword}%` }

  const order = sort === 'hot' ? [['like_count', 'DESC'], ['created_at', 'DESC']] : [['created_at', 'DESC'], ['id', 'DESC']]

  const { count, rows } = await Project.findAndCountAll({
    where,
    attributes: PROJECT_ADMIN_ATTRS,
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ],
    order,
    limit,
    offset,
    distinct: true
  })

  const [total, hidden, recommend] = await Promise.all([
    Project.count(),
    Project.count({ where: { is_hidden: 1 } }),
    Project.count({ where: { is_recommend: 1 } })
  ])

  return {
    projects: rows.map(toClientProject),
    total: count,
    page,
    pageSize: limit,
    summary: { total, hidden, recommend },
    filter: Object.prototype.hasOwnProperty.call(PROJECT_STATE_FILTERS, state) ? state : 'all',
    search: keyword
  }
}

exports.updateProject = async (id, payload, actorId, req) => {
  const project = await Project.findByPk(id, { attributes: PROJECT_ADMIN_ATTRS })
  if (!project) throw ApiError.notFound('项目不存在')

  const changedFields = []
  if (has(payload, 'isHidden')) {
    const next = toBoolFlag(payload.isHidden, '下架状态')
    if (next !== Number(project.is_hidden)) {
      project.is_hidden = next
      changedFields.push('is_hidden')
    }
  }
  if (has(payload, 'isRecommend')) {
    const next = toBoolFlag(payload.isRecommend, '推荐标记')
    if (next !== Number(project.is_recommend)) {
      project.is_recommend = next
      changedFields.push('is_recommend')
    }
  }
  if (!changedFields.length) {
    throw ApiError.badRequest('没有需要更新的项目状态')
  }

  await project.save()
  await activityLogService.logAdminProjectUpdated({
    userId: actorId,
    project,
    changedFields,
    req
  })

  const fresh = await Project.findByPk(id, {
    attributes: PROJECT_ADMIN_ATTRS,
    include: [
      { model: Category, as: 'category', attributes: ['id', 'name'] },
      { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
    ]
  })
  return { project: toClientProject(fresh), changedFields }
}

// 管理台删除沿用项目的软删除（paranoid）：数据仍在库里，账号作者可申诉恢复，
// 审计链也保持完整；公开接口会因 deleted_at 自动过滤。
exports.deleteProject = async (id, actorId, req) => {
  const project = await Project.findByPk(id, { attributes: ['id', 'title'] })
  if (!project) throw ApiError.notFound('项目不存在')

  await project.destroy()
  await activityLogService.logAdminProjectDeleted({ userId: actorId, project, req })
  return { deleted: true, id: project.id }
}

// ============ 用户管理 ============

exports.listUsers = async ({ page = 1, pageSize = 10, state, role, search } = {}) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 10 })
  const offset = (page - 1) * limit

  const where = {}
  if (state === 'disabled') where.status = 0
  else if (state === 'active') where.status = 1
  if (role === 'admin') where.is_admin = 1
  else if (role === 'member') where.is_admin = 0

  const keyword = typeof search === 'string' ? search.trim() : ''
  if (keyword) {
    where[Op.or] = [
      { username: { [Op.like]: `%${keyword}%` } },
      { email: { [Op.like]: `%${keyword}%` } }
    ]
  }

  const { count, rows } = await User.findAndCountAll({
    where,
    attributes: USER_ATTRS,
    order: [['created_at', 'DESC'], ['id', 'DESC']],
    limit,
    offset
  })

  // 每人一行「发布 / 评论」真实计数：管理台判断「这是不是一个空账号」靠它，
  // 列表页一条 N+1 查询太浪费，这里两次聚合查询解决整页。
  const ids = rows.map((u) => u.id)
  const [projectCounts, commentCounts, totals] = await Promise.all([
    ids.length
      ? Project.findAll({
          attributes: ['creator_id', [sequelize.fn('COUNT', sequelize.col('id')), 'total']],
          where: { creator_id: { [Op.in]: ids }, is_hidden: 0 },
          group: ['creator_id'],
          raw: true
        })
      : [],
    ids.length
      ? Comment.findAll({
          attributes: ['user_id', [sequelize.fn('COUNT', sequelize.col('id')), 'total']],
          where: { user_id: { [Op.in]: ids } },
          group: ['user_id'],
          raw: true
        })
      : [],
    Promise.all([
      User.count(),
      User.count({ where: { status: 0 } }),
      User.count({ where: { is_admin: 1 } })
    ])
  ])

  const projectMap = new Map(projectCounts.map((r) => [Number(r.creator_id), Number(r.total)]))
  const commentMap = new Map(commentCounts.map((r) => [Number(r.user_id), Number(r.total)]))

  return {
    users: rows.map((u) => ({
      ...toClientUser(u),
      projectCount: projectMap.get(Number(u.id)) || 0,
      commentCount: commentMap.get(Number(u.id)) || 0
    })),
    total: count,
    page,
    pageSize: limit,
    summary: { total: totals[0], disabled: totals[1], admins: totals[2] },
    filter: { state: state || 'all', role: role || 'all' },
    search: keyword
  }
}

exports.updateUser = async (id, payload, actorId, req) => {
  const target = await User.findByPk(id, { attributes: USER_ATTRS })
  if (!target) throw ApiError.notFound('用户不存在')

  // 管理员唯一且固定：角色不开放给管理台调整，否则「有且只有一个管理员」的约束
  // 只要点一下「授予管理员」就被破坏。换管理员只能走数据库变更。
  if (has(payload, 'isAdmin')) {
    throw ApiError.badRequest('管理员账号已固定，不支持在管理台调整')
  }

  // 自锁保护：停用自己等于当场把管理台锁死，之后只能改数据库才能恢复。
  // 这是明确不允许的操作，不是「谨慎操作」。
  if (Number(target.id) === Number(actorId) && has(payload, 'status')) {
    throw ApiError.badRequest('不能停用自己')
  }

  const changedFields = []
  if (has(payload, 'status')) {
    const next = toBoolFlag(payload.status, '账号状态')
    // 语义转换：1=正常，0=停用
    const normalized = next === 1 ? 1 : 0
    if (normalized !== Number(target.status)) {
      target.status = normalized
      changedFields.push('status')
    }
  }
  if (!changedFields.length) throw ApiError.badRequest('没有需要更新的账号状态')

  await target.save()
  await activityLogService.logAdminUserUpdated({
    userId: actorId,
    targetUser: target,
    changedFields,
    status: target.status,
    isAdmin: target.is_admin,
    req
  })
  return { user: toClientUser(target), changedFields }
}

// ============ 通知管理 ============

exports.listNotifications = async ({ page = 1, pageSize = 12, type, search } = {}) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 12 })
  const offset = (page - 1) * limit

  const where = {}
  const typeFilter = NOTIFICATION_TYPES.includes(type) ? type : null
  if (typeFilter) where.type = typeFilter
  const keyword = typeof search === 'string' ? search.trim() : ''
  if (keyword) {
    where[Op.or] = [
      { message: { [Op.like]: `%${keyword}%` } },
      { '$recipient.username$': { [Op.like]: `%${keyword}%` } }
    ]
  }

  const { count, rows } = await Notification.findAndCountAll({
    where,
    include: [
      { model: User, as: 'recipient', attributes: ['id', 'username', 'avatar'] },
      { model: User, as: 'actor', attributes: ['id', 'username'] },
      { model: Project, as: 'project', attributes: ['id', 'title'], required: false }
    ],
    order: [['created_at', 'DESC'], ['id', 'DESC']],
    limit,
    offset,
    // 搜索关联列时必须关掉子查询模式，否则 `$recipient.username$` 会被当成字面量
    subQuery: false,
    distinct: true
  })

  const [total, system, unread] = await Promise.all([
    Notification.count(),
    Notification.count({ where: { type: 'system' } }),
    Notification.count({ where: { is_read: 0 } })
  ])

  return {
    notifications: rows.map(toClientNotification),
    total: count,
    page,
    pageSize: limit,
    summary: { total, system, unread },
    filter: typeFilter || 'all',
    search: keyword
  }
}

// 发公告：不传 userId 即全站广播（只发给正常账号，接收人永远不会是发送者自己）。
// 逐条 insert 而不是一条 SQL 拼接，是为了让每行都拿到独立 id，管理台能逐条删除。
exports.sendNotice = async ({ message, userId }, actorId, req) => {
  const raw = typeof message === 'string' ? message : ''
  const cleaned = stripControlChars(stripEmoji(raw.replace(/\r\n?/g, '\n')), { keepNewlines: true }).trim()
  if (!cleaned) throw ApiError.badRequest('公告内容不能为空')
  if (cleaned.length > NOTICE_MAX_LENGTH) {
    throw ApiError.badRequest(`公告内容最多 ${NOTICE_MAX_LENGTH} 个字符`)
  }

  let recipients
  let audience
  if (userId !== undefined && userId !== null && userId !== '') {
    const targetId = Number(userId)
    if (!Number.isInteger(targetId) || targetId <= 0) throw ApiError.badRequest('接收用户不合法')
    if (targetId === Number(actorId)) throw ApiError.badRequest('不能给自己发送通知')
    const target = await User.findByPk(targetId, { attributes: ['id', 'username', 'status'] })
    if (!target) throw ApiError.notFound('接收用户不存在')
    if (Number(target.status) === 0) throw ApiError.badRequest('该账号已停用，无法接收通知')
    recipients = [target]
    audience = 'single'
  } else {
    recipients = await User.findAll({
      attributes: ['id', 'username'],
      where: { status: 1, id: { [Op.ne]: Number(actorId) } }
    })
    audience = 'all'
  }

  if (!recipients.length) throw ApiError.badRequest('当前没有可接收通知的用户')

  await Notification.bulkCreate(
    recipients.map((user) => ({
      user_id: user.id,
      actor_id: Number(actorId),
      type: 'system',
      project_id: null,
      comment_id: null,
      message: cleaned,
      is_read: 0
    }))
  )

  await activityLogService.logAdminNoticeSent({
    userId: actorId,
    message: cleaned,
    audience,
    recipients: recipients.length,
    req
  })

  return { created: recipients.length, audience, message: cleaned }
}

exports.deleteNotification = async (id, actorId, req) => {
  const notification = await Notification.findByPk(id, {
    include: [{ model: User, as: 'recipient', attributes: ['id', 'username'] }]
  })
  if (!notification) throw ApiError.notFound('通知不存在')

  const snapshot = { id: notification.id, type: notification.type, message: notification.message }
  const recipientName = notification.recipient ? notification.recipient.username : ''

  await notification.destroy()
  await activityLogService.logAdminNotificationDeleted({
    userId: actorId,
    notification: snapshot,
    recipientName,
    req
  })
  return { deleted: true, id: snapshot.id }
}

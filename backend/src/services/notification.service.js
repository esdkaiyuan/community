const { Notification, User, Project, Comment } = require('../models')

// 通知文案所需的最小关联
const ACTOR_ATTRS = ['id', 'username', 'avatar']
const PROJECT_ATTRS = ['id', 'title']

// 创建通知（fire-and-forget：失败不影响主流程；自己触发的不通知自己）
exports.notify = ({ userId, type, actorId, projectId, commentId = null }) => {
  if (!userId || userId === actorId) return Promise.resolve(null)
  return Notification.create({ user_id: userId, type, actor_id: actorId, project_id: projectId, comment_id: commentId }).catch(
    () => null
  )
}

// 同一 actor 对同一项目只通知一次：用于「参与共创」这类可重复触发的动作，
// 避免「退出 → 再加入」反复刷屏；同样 fire-and-forget，不抛错
exports.notifyOnce = ({ userId, type, actorId, projectId, commentId = null }) => {
  if (!userId || userId === actorId) return Promise.resolve(null)
  return Notification.findOne({ where: { user_id: userId, type, actor_id: actorId, project_id: projectId } })
    .then((existing) =>
      existing
        ? null
        : Notification.create({
            user_id: userId,
            type,
            actor_id: actorId,
            project_id: projectId,
            comment_id: commentId
          })
    )
    .catch(() => null)
}

exports.list = async ({ userId, page = 1, pageSize = 15, unreadOnly = false }) => {
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize, 10) || 15))
  const offset = (page - 1) * limit

  const where = { user_id: userId }
  if (unreadOnly) where.is_read = 0

  const { count, rows } = await Notification.findAndCountAll({
    where,
    include: [
      { model: User, as: 'actor', attributes: ACTOR_ATTRS },
      { model: Project, as: 'project', attributes: PROJECT_ATTRS },
      // ⚠️ Comment 带 defaultScope(status = 1)，Sequelize 会因此把该关联当成 INNER JOIN，
      // 于是 comment_id 为 NULL 的通知（如「参与共创」）被整行过滤掉 —— 必须显式 required: false
      { model: Comment, as: 'comment', attributes: ['id', 'content'], required: false }
    ],
    order: [['created_at', 'DESC']],
    limit,
    offset,
    distinct: true
  })

  const unread = await Notification.count({ where: { user_id: userId, is_read: 0 } })

  return {
    notifications: rows.map((n) => {
      const row = n.toJSON()
      return {
        id: row.id,
        type: row.type,
        isRead: !!row.is_read,
        createdAt: row.created_at,
        actor: row.actor,
        project: row.project,
        commentPreview: row.comment?.content?.slice(0, 60) || null
      }
    }),
    total: count,
    unread,
    page,
    pageSize: limit,
    filter: unreadOnly ? 'unread' : 'all'
  }
}

exports.unreadCount = (userId) => Notification.count({ where: { user_id: userId, is_read: 0 } })

// 标记已读：ids 数组或 all
exports.markRead = async ({ userId, ids, all }) => {
  const where = { user_id: userId }
  if (!all) {
    const idList = (Array.isArray(ids) ? ids : []).map(Number).filter(Boolean)
    if (!idList.length) return { updated: 0 }
    where.id = idList
  }
  const [updated] = await Notification.update({ is_read: 1 }, { where })
  return { updated }
}

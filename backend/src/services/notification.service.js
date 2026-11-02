const { Notification, User, Project, Comment } = require('../models')
const { clampInt, MAX_PAGE } = require('../utils/pagination')

// 通知文案所需的最小关联
const ACTOR_ATTRS = ['id', 'username', 'avatar']
const PROJECT_ATTRS = ['id', 'title']

// 通知类型白名单，与 Notification.type 的 ENUM 取值一致（schema.sql 同源）。
// ⚠️ 白名单外的入参「静默忽略」（当作不筛选）而不是 400：与既有 filter 参数保持同一
// 语义（filter 传 'unread' 之外的值也是当 all）。理由有两条——这是只读筛选，非法值
// 不构成安全事件；且将来 ENUM 扩展时前端传新值只会被忽略，不会突然开始报错。
const NOTIFICATION_TYPES = ['comment', 'reply', 'like', 'participate', 'mention', 'system']

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

exports.list = async ({ userId, page = 1, pageSize = 15, unreadOnly = false, type }) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 15 })
  const offset = (page - 1) * limit

  const where = { user_id: userId }
  if (unreadOnly) where.is_read = 0
  // 类型筛选：白名单校验在此收口，service 层是唯一入口，路由/控制器不必重复判
  const typeFilter = NOTIFICATION_TYPES.includes(type) ? type : null
  if (typeFilter) where.type = typeFilter

  const { count, rows } = await Notification.findAndCountAll({
    where,
    include: [
      { model: User, as: 'actor', attributes: ACTOR_ATTRS },
      // 系统公告的 project_id 为空（不指向任何项目），必须显式 required: false，
      // 否则 LEFT JOIN 会被降级成 INNER JOIN，公告整批查不出来
      { model: Project, as: 'project', attributes: PROJECT_ATTRS, required: false },
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
        // 评论 / 回复 / 点赞类通知带上评论 id，前端才能深链直达那一条，而不是停在评论区顶部
        commentId: row.comment_id || null,
        commentPreview: row.comment?.content?.slice(0, 60) || null,
        // 只有系统公告有正文；互动通知的正文来自评论快照或项目本身
        message: row.message || null
      }
    }),
    total: count,
    unread,
    page,
    pageSize: limit,
    filter: unreadOnly ? 'unread' : 'all',
    // 回显实际生效的筛选态：非法 type 被忽略后前端能据此判断「筛选没生效」而不是
    // 误以为「这个类型没有通知」
    type: typeFilter || 'all'
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

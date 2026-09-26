const notificationService = require('../services/notification.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok } = require('../utils/response')

exports.getNotifications = asyncHandler(async (req, res) => {
  const data = await notificationService.list({
    userId: req.user.userId,
    page: req.query.page,
    pageSize: req.query.pageSize,
    unreadOnly: req.query.filter === 'unread'
  })
  ok(res, data, '获取通知列表成功')
})

exports.getUnreadCount = asyncHandler(async (req, res) => {
  const unread = await notificationService.unreadCount(req.user.userId)
  ok(res, { unread }, '获取未读数成功')
})

exports.markRead = asyncHandler(async (req, res) => {
  const data = await notificationService.markRead({
    userId: req.user.userId,
    ids: req.body.ids,
    all: req.body.all
  })
  ok(res, data, '已标记为已读')
})

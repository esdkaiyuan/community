const activityLogService = require('../services/activityLog.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok } = require('../utils/response')

// 我的操作记录（只读）。只查当前登录用户的日志，不接受任何 userId 参数。
exports.getMyLogs = asyncHandler(async (req, res) => {
  const data = await activityLogService.listMine({
    userId: req.user.userId,
    page: req.query.page,
    pageSize: req.query.pageSize,
    action: req.query.action,
    projectId: req.query.projectId
  })
  ok(res, data, '获取操作日志成功')
})

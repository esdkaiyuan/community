const activityLogService = require('../services/activityLog.service')
const securityEventService = require('../services/securityEvent.service')
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

// 针对**我**账号的被拒尝试（登录失败、有人拿我的邮箱/用户名注册等）。
//
// 与上面的 /logs/me 互补：那边是我做成了什么，这边是别人对我做了什么没做成。
// 同样只查当前登录用户，不接受任何 userId 参数 —— 「谁能读」由「你是谁」决定。
// 全站流水（按 IP / 按事件类型横查）需要角色体系，本项目没有，刻意不开；将来做管理端
// 时应另开一条带角色校验的路由，而不是把这里的条件放开。
exports.getMySecurityEvents = asyncHandler(async (req, res) => {
  const data = await securityEventService.listMine({
    userId: req.user.userId,
    page: req.query.page,
    pageSize: req.query.pageSize,
    event: req.query.event
  })
  ok(res, data, '获取安全事件成功')
})

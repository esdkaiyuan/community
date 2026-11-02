const adminService = require('../services/admin.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok, created } = require('../utils/response')

exports.getOverview = asyncHandler(async (_req, res) => {
  ok(res, await adminService.getOverview(), '获取管理台概览成功')
})

exports.getProjects = asyncHandler(async (req, res) => {
  ok(res, await adminService.listProjects(req.query), '获取项目列表成功')
})

exports.updateProject = asyncHandler(async (req, res) => {
  const data = await adminService.updateProject(req.params.id, req.body, req.user.userId, req)
  ok(res, data, '项目状态已更新')
})

exports.deleteProject = asyncHandler(async (req, res) => {
  ok(res, await adminService.deleteProject(req.params.id, req.user.userId, req), '项目已删除')
})

exports.getUsers = asyncHandler(async (req, res) => {
  ok(res, await adminService.listUsers(req.query), '获取用户列表成功')
})

exports.updateUser = asyncHandler(async (req, res) => {
  const data = await adminService.updateUser(req.params.id, req.body, req.user.userId, req)
  ok(res, data, '账号状态已更新')
})

exports.getNotifications = asyncHandler(async (req, res) => {
  ok(res, await adminService.listNotifications(req.query), '获取通知列表成功')
})

exports.sendNotice = asyncHandler(async (req, res) => {
  const data = await adminService.sendNotice(req.body, req.user.userId, req)
  created(res, data, `公告已发送给 ${data.created} 位用户`)
})

exports.deleteNotification = asyncHandler(async (req, res) => {
  ok(res, await adminService.deleteNotification(req.params.id, req.user.userId, req), '通知已删除')
})

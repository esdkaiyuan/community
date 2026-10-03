const userService = require('../services/user.service')
const favoriteService = require('../services/favorite.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok, created } = require('../utils/response')

exports.register = asyncHandler(async (req, res) => {
  const data = await userService.register(req.body, req)
  created(res, data, data.adjusted ? '注册成功（用户名里的表情符号等非法字符已自动移除）' : '注册成功')
})

exports.login = asyncHandler(async (req, res) => {
  // 与 register 一样透传 req：登录失败要留安全事件（ip / ua 都从 req 取）
  const data = await userService.login(req.body, req)
  ok(res, data, '登录成功')
})

exports.getProfile = asyncHandler(async (req, res) => {
  const user = await userService.getProfile(req.user.userId)
  ok(res, user, '获取用户信息成功')
})

exports.updateProfile = asyncHandler(async (req, res) => {
  const data = await userService.updateProfile(req.user.userId, req.body, req)
  // adjusted 只在「净化确实改动了内容」时为真，不做静默修改 —— 让用户知道自己打的东西变了
  ok(res, data, data.adjusted ? '资料已更新（已自动移除表情符号等非法字符）' : '资料已更新')
})

exports.updatePassword = asyncHandler(async (req, res) => {
  const data = await userService.changePassword(req.user.userId, req.body, req)
  // 文案必须讲清「其他设备会掉线」：用户改密往往就是为了把别人踢出去，
  // 不说明的话他会以为「改完就没事了」，而实际上下一次请求才会发现旧令牌已废
  ok(res, data, '密码已更新，其他设备需要重新登录')
})

exports.getPublicProfile = asyncHandler(async (req, res) => {
  const data = await userService.getPublicProfile(req.params.id)
  ok(res, data, '获取用户主页成功')
})

exports.getMyComments = asyncHandler(async (req, res) => {
  const data = await userService.getMyComments(req.user.userId, req.query)
  ok(res, data)
})

exports.getMyStats = asyncHandler(async (req, res) => {
  const data = await userService.getMyStats(req.user.userId)
  ok(res, data)
})

exports.getMyFavorites = asyncHandler(async (req, res) => {
  const data = await favoriteService.listFavorites({ userId: req.user.userId, ...req.query })
  ok(res, data)
})

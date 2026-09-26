const userService = require('../services/user.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok, created } = require('../utils/response')

exports.register = asyncHandler(async (req, res) => {
  const data = await userService.register(req.body)
  created(res, data, '注册成功')
})

exports.login = asyncHandler(async (req, res) => {
  const data = await userService.login(req.body)
  ok(res, data, '登录成功')
})

exports.getProfile = asyncHandler(async (req, res) => {
  const user = await userService.getProfile(req.user.userId)
  ok(res, user, '获取用户信息成功')
})

exports.updateProfile = asyncHandler(async (req, res) => {
  const user = await userService.updateProfile(req.user.userId, req.body)
  ok(res, { user }, '更新成功')
})

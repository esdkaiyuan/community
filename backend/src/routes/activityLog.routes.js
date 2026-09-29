const express = require('express')
const router = express.Router()
const activityLogController = require('../controllers/activityLog.controller')
const { auth } = require('../middleware/auth')

// 操作日志只对本人开放。
// 本项目目前没有角色体系，所以刻意不提供「查看他人日志」的接口 —— 加了就得先有
// 可信的角色校验，否则等于把全站用户行为记录公开。将来做管理端时，应另开一条
// 带角色校验的路由，而不是把这里的 userId 参数放开。
router.use(auth)

router.get('/me', activityLogController.getMyLogs)

module.exports = router

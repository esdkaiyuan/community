const express = require('express')
const router = express.Router()
const userController = require('../controllers/user.controller')
const { auth } = require('../middleware/auth')
const { authLimiter } = require('../middleware/rateLimiter')

// 公开路由（注册/登录有更严格的限流）
router.post('/register', authLimiter, userController.register)
router.post('/login', authLimiter, userController.login)

// 需要认证的路由
router.get('/me', auth, userController.getProfile)
router.get('/me/comments', auth, userController.getMyComments)
router.get('/me/stats', auth, userController.getMyStats)
router.get('/profile', auth, userController.getProfile)
router.put('/profile', auth, userController.updateProfile)

module.exports = router

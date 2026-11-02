const express = require('express')
const router = express.Router()
const userController = require('../controllers/user.controller')
const { auth } = require('../middleware/auth')
const { authLimiter, passwordLimiter, emailCodeLimiter } = require('../middleware/rateLimiter')

// 公开路由（注册/登录有更严格的限流）
router.post('/register', authLimiter, userController.register)
router.post('/login', authLimiter, userController.login)

// 统一身份认证服务：邮箱验证码发送 / 验证码注册 / 验证码登录 / 忘记密码
// 这四个入口都不需要登录态；验证码发送单独限流，避免被脚本刷外部邮件额度。
router.post('/email/send-code', emailCodeLimiter, userController.sendEmailCode)
router.post('/register/email', authLimiter, userController.registerWithEmailCode)
router.post('/login/email', authLimiter, userController.loginWithEmailCode)
router.post('/password/reset', passwordLimiter, userController.resetPasswordWithEmailCode)

// 需要认证的路由
router.get('/me', auth, userController.getProfile)
router.get('/me/comments', auth, userController.getMyComments)
router.get('/me/stats', auth, userController.getMyStats)
router.get('/me/favorites', auth, userController.getMyFavorites)
router.get('/profile', auth, userController.getProfile)
router.put('/profile', auth, userController.updateProfile)
// 改密：改的是自己的密码，所以只认登录态（不接受任何 userId 参数）。
// 独立限流：防「拿到令牌后反复猜当前密码」，且不与登录共用配额（见 rateLimiter.js）
router.put('/password', auth, passwordLimiter, userController.updatePassword)

// 公开主页：任何人可看（响应不含 email）。
// ⚠️ 必须排在 /me、/profile 等具名 GET 之后，否则 GET /users/me 会被当成 id='me'
router.get('/:id', userController.getPublicProfile)

module.exports = router

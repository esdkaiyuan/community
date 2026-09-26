const express = require('express')
const router = express.Router()
const userController = require('../controllers/user.controller')
const auth = require('../middleware/auth')

// 公开路由
router.post('/register', userController.register)
router.post('/login', userController.login)

// 需要认证的路由
router.get('/me', auth, userController.getProfile)
router.get('/profile', auth, userController.getProfile)
router.put('/profile', auth, userController.updateProfile)

module.exports = router

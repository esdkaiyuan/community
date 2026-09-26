const express = require('express')
const router = express.Router()
const notificationController = require('../controllers/notification.controller')
const { auth } = require('../middleware/auth')

// 全部需要登录
router.use(auth)

router.get('/', notificationController.getNotifications)
router.get('/unread-count', notificationController.getUnreadCount)
router.post('/read', notificationController.markRead)

module.exports = router

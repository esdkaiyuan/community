const express = require('express')
const router = express.Router()
const adminController = require('../controllers/admin.controller')
const { auth, requireAdmin } = require('../middleware/auth')

// 整个管理台统一守卫：撤权/停用需要「立即生效」，所以这里不读 JWT 里的角色，
// 而是由 auth 每次请求回查 users.is_admin（见 middleware/auth.js）。
router.use(auth, requireAdmin)

router.get('/overview', adminController.getOverview)

router.get('/projects', adminController.getProjects)
router.patch('/projects/:id', adminController.updateProject)
router.delete('/projects/:id', adminController.deleteProject)

router.get('/users', adminController.getUsers)
router.patch('/users/:id', adminController.updateUser)

router.get('/notifications', adminController.getNotifications)
router.post('/notifications', adminController.sendNotice)
router.delete('/notifications/:id', adminController.deleteNotification)

module.exports = router

const express = require('express')
const router = express.Router()
const projectController = require('../controllers/project.controller')
const { auth, optionalAuth } = require('../middleware/auth')

// 公开路由（详情页用可选认证，登录用户可拿到 liked/participated 状态）
router.get('/', projectController.getProjects)
router.get('/:id', optionalAuth, projectController.getProjectById)

// 需要认证的路由
router.post('/', auth, projectController.createProject)
router.put('/:id', auth, projectController.updateProject)
router.delete('/:id', auth, projectController.deleteProject)
router.post('/:id/like', auth, projectController.likeProject)
router.delete('/:id/like', auth, projectController.unlikeProject)
router.post('/:id/participate', auth, projectController.participateProject)
router.delete('/:id/participate', auth, projectController.cancelParticipate)

module.exports = router

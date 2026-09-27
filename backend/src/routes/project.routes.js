const express = require('express')
const router = express.Router()
const projectController = require('../controllers/project.controller')
const commentController = require('../controllers/comment.controller')
const { auth, optionalAuth } = require('../middleware/auth')

// 公开路由（详情页用可选认证，登录用户可拿到 liked/participated 状态）
router.get('/', projectController.getProjects)
router.get('/:id', optionalAuth, projectController.getProjectById)

// 项目评论（嵌套路由，参数与详情页一致使用 :id）
router.get('/:id/comments', optionalAuth, commentController.getComments)
router.post('/:id/comments', auth, commentController.createComment)
router.delete('/:id/comments/:commentId', auth, commentController.deleteComment)
router.post('/:id/comments/:commentId/like', auth, commentController.likeComment)
router.delete('/:id/comments/:commentId/like', auth, commentController.unlikeComment)

// 需要认证的路由
router.post('/', auth, projectController.createProject)
router.put('/:id', auth, projectController.updateProject)
router.delete('/:id', auth, projectController.deleteProject)
router.post('/:id/like', auth, projectController.likeProject)
router.delete('/:id/like', auth, projectController.unlikeProject)
router.post('/:id/participate', auth, projectController.participateProject)
router.delete('/:id/participate', auth, projectController.cancelParticipate)
router.post('/:id/favorite', auth, projectController.favoriteProject)
router.delete('/:id/favorite', auth, projectController.unfavoriteProject)

module.exports = router

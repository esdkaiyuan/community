const express = require('express')
const router = express.Router()
const projectController = require('../controllers/project.controller')
const commentController = require('../controllers/comment.controller')
const { auth, optionalAuth } = require('../middleware/auth')

// 公开路由（列表/详情用可选认证，登录用户可拿到 favorited 状态与「只看收藏」筛选）
router.get('/', optionalAuth, projectController.getProjects)
// 注意：必须排在 /:id 之前，否则会被当成 id = 'tags' 的项目详情
router.get('/tags', projectController.getProjectTags)
router.get('/:id', optionalAuth, projectController.getProjectById)
router.get('/:id/participants', projectController.getProjectParticipants)
// 相关推荐（详情页底部的「继续浏览」入口）：公开接口
router.get('/:id/related', projectController.getProjectRelated)

// 项目评论（嵌套路由，参数与详情页一致使用 :id）
router.get('/:id/comments', optionalAuth, commentController.getComments)
// 深链定位：具名子路径必须排在 /:id/comments/:commentId 之前
router.get('/:id/comments/locate', optionalAuth, commentController.locateComment)
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

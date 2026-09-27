const commentService = require('../services/comment.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok, created } = require('../utils/response')

exports.getComments = asyncHandler(async (req, res) => {
  const data = await commentService.listComments({
    projectId: req.params.id,
    page: req.query.page,
    pageSize: req.query.pageSize,
    currentUserId: req.user?.userId
  })
  ok(res, data, '获取评论列表成功')
})

// 深链定位：给出某条评论在评论列表里的页码（前端据此加载到那一页再滚动高亮）
exports.locateComment = asyncHandler(async (req, res) => {
  const data = await commentService.locateComment({
    projectId: req.params.id,
    commentId: req.query.commentId,
    pageSize: req.query.pageSize
  })
  ok(res, data, '定位成功')
})

exports.createComment = asyncHandler(async (req, res) => {
  const data = await commentService.createComment({
    projectId: req.params.id,
    content: req.body.content,
    parentId: req.body.parentId,
    userId: req.user.userId
  })
  created(res, data, data.hadEmoji ? '评论发布成功（表情符号已自动移除）' : '评论发布成功')
})

exports.deleteComment = asyncHandler(async (req, res) => {
  const data = await commentService.deleteComment({
    projectId: req.params.id,
    commentId: req.params.commentId,
    userId: req.user.userId
  })
  ok(res, data, '评论已删除')
})

exports.likeComment = asyncHandler(async (req, res) => {
  const data = await commentService.likeComment({
    projectId: req.params.id,
    commentId: req.params.commentId,
    userId: req.user.userId
  })
  ok(res, data, '点赞成功')
})

exports.unlikeComment = asyncHandler(async (req, res) => {
  const data = await commentService.unlikeComment({
    projectId: req.params.id,
    commentId: req.params.commentId,
    userId: req.user.userId
  })
  ok(res, data, '已取消点赞')
})

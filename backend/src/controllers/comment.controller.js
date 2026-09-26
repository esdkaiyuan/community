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

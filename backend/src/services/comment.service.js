const { Op } = require('sequelize')
const { Comment, Project, User } = require('../models')
const ApiError = require('../utils/ApiError')
const { stripEmoji, hasEmoji } = require('../utils/textSanitize')

const MAX_CONTENT_LEN = 500

// 数据库行 -> 前端数据形状
const toClientComment = (comment, extra = {}) => {
  const row = comment.toJSON ? comment.toJSON() : comment
  return {
    id: row.id,
    content: row.content,
    createdAt: row.created_at,
    user: row.user
      ? { id: row.user.id, username: row.user.username, avatar: row.user.avatar || '' }
      : null,
    ...extra
  }
}

exports.listComments = async ({ projectId, page = 1, pageSize = 20, currentUserId }) => {
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize, 10) || 20))
  const offset = (page - 1) * limit

  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const { count, rows } = await Comment.findAndCountAll({
    where: { project_id: projectId },
    include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }],
    order: [['created_at', 'DESC']],
    limit,
    offset,
    distinct: true
  })

  // 项目创建者也可以删除任意评论
  const isProjectOwner = currentUserId != null && project.creator_id === currentUserId

  return {
    comments: rows.map((row) =>
      toClientComment(row, {
        canDelete: isProjectOwner || (currentUserId != null && row.user_id === currentUserId)
      })
    ),
    total: count,
    page,
    pageSize: limit
  }
}

exports.createComment = async ({ projectId, content, userId }) => {
  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const cleaned = stripEmoji(content)
  if (!cleaned) throw ApiError.badRequest('评论内容不能为空')
  if (cleaned.length > MAX_CONTENT_LEN) {
    throw ApiError.badRequest(`评论最多 ${MAX_CONTENT_LEN} 个字符`)
  }

  const comment = await Comment.create({
    project_id: Number(projectId),
    user_id: userId,
    content: cleaned
  })

  project.comment_count += 1
  await project.save()

  const full = await Comment.findByPk(comment.id, {
    include: [{ model: User, as: 'user', attributes: ['id', 'username', 'avatar'] }]
  })

  return {
    comment: toClientComment(full, { canDelete: true }),
    hadEmoji: hasEmoji(content),
    commentCount: project.comment_count
  }
}

exports.deleteComment = async ({ projectId, commentId, userId }) => {
  const project = await Project.findByPk(projectId)
  if (!project) throw ApiError.notFound('项目不存在')

  const comment = await Comment.findOne({
    where: { id: commentId, project_id: projectId }
  })
  if (!comment) throw ApiError.notFound('评论不存在或已被删除')

  // 仅评论作者或项目创建者可删除
  if (comment.user_id !== userId && project.creator_id !== userId) {
    throw ApiError.forbidden('无权删除此评论')
  }

  await comment.destroy()
  if (project.comment_count > 0) {
    project.comment_count -= 1
    await project.save()
  }

  return { commentCount: project.comment_count }
}

// 评论计数与真实条数对账（供管理/修复用）
exports.recountComments = async (projectId) => {
  const count = await Comment.count({ where: { project_id: { [Op.eq]: projectId } } })
  await Project.update({ comment_count: count }, { where: { id: projectId } })
  return count
}

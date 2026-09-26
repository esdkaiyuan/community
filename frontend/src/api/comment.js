import request from './request'

// 评论列表（分页，可选认证：登录后返回 canDelete 权限标记）
export const getComments = (projectId, params) =>
  request.get(`/projects/${projectId}/comments`, { params })

// 发布评论（parentId 可选：回复根评论）
export const createComment = (projectId, data) =>
  request.post(`/projects/${projectId}/comments`, data)

// 删除评论（作者本人或项目创建者）
export const deleteComment = (projectId, commentId) =>
  request.delete(`/projects/${projectId}/comments/${commentId}`)

// 评论点赞 / 取消点赞
export const likeComment = (projectId, commentId) =>
  request.post(`/projects/${projectId}/comments/${commentId}/like`)

export const unlikeComment = (projectId, commentId) =>
  request.delete(`/projects/${projectId}/comments/${commentId}/like`)

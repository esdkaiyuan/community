import request from './request'

// 获取项目列表
export function getProjects(params) {
  return request.get('/projects', { params })
}

// 根据ID获取项目详情
export function getProjectById(id) {
  return request.get(`/projects/${id}`)
}

// 创建项目
export function createProject(data) {
  return request.post('/projects', data)
}

// 更新项目
export function updateProject(id, data) {
  return request.put(`/projects/${id}`, data)
}

// 删除项目
export function deleteProject(id) {
  return request.delete(`/projects/${id}`)
}

// 点赞项目
export function likeProject(id) {
  return request.post(`/projects/${id}/like`)
}

// 取消点赞
export function unlikeProject(id) {
  return request.delete(`/projects/${id}/like`)
}

// 参与项目
export function participateProject(id) {
  return request.post(`/projects/${id}/participate`)
}

// 取消参与
export function cancelParticipate(id) {
  return request.delete(`/projects/${id}/participate`)
}

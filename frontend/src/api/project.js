import request from './request'

// 项目列表（page、pageSize、categoryId、search、filter: recommend|hot、sort: latest|hot|participants）
export const getProjects = (params) => request.get('/projects', { params })

// 项目详情
export const getProject = (id) => request.get(`/projects/${id}`)

// 创建项目
export const createProject = (data) => request.post('/projects', data)

// 更新项目
export const updateProject = (id, data) => request.put(`/projects/${id}`, data)

// 删除项目
export const deleteProject = (id) => request.delete(`/projects/${id}`)

// 点赞 / 取消点赞
export const likeProject = (id) => request.post(`/projects/${id}/like`)
export const unlikeProject = (id) => request.delete(`/projects/${id}/like`)

// 参与 / 取消参与
export const participateProject = (id) => request.post(`/projects/${id}/participate`)
export const cancelParticipate = (id) => request.delete(`/projects/${id}/participate`)

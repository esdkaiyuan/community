import request from './request'

// 项目列表（page、pageSize、categoryId、tag、search、filter: recommend|hot、sort: latest|hot|participants）
export const getProjects = (params) => request.get('/projects', { params })

// 热门标签（广场入口）
export const getProjectTags = (params) => request.get('/projects/tags', { params })

// 项目详情
export const getProject = (id) => request.get(`/projects/${id}`)

// 共创伙伴名单（分页）
export const getProjectParticipants = (id, params) => request.get(`/projects/${id}/participants`, { params })

// 相关项目推荐（详情页底部的「继续浏览」，按共同标签 / 同分类排序）
export const getRelatedProjects = (id, params) => request.get(`/projects/${id}/related`, { params })

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

// 收藏 / 取消收藏
export const favoriteProject = (id) => request.post(`/projects/${id}/favorite`)
export const unfavoriteProject = (id) => request.delete(`/projects/${id}/favorite`)

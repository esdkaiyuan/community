import request from './request'

// 管理台：概览、项目、用户、通知四组接口。
// 权限由后端 admin.routes 的 auth + requireAdmin 统一守卫，前端不再重复判断。

export const getAdminOverview = () => request.get('/admin/overview')

export const getAdminProjects = (params) => request.get('/admin/projects', { params })
export const updateAdminProject = (id, data) => request.patch(`/admin/projects/${id}`, data)
export const deleteAdminProject = (id) => request.delete(`/admin/projects/${id}`)

export const getAdminUsers = (params) => request.get('/admin/users', { params })
export const updateAdminUser = (id, data) => request.patch(`/admin/users/${id}`, data)

export const getAdminNotifications = (params) => request.get('/admin/notifications', { params })
// 发送失败要就地显示在公告表单旁（「该账号已停用」「内容不能为空」），
// 所以 silent：不再叠一张全局提示
export const sendAdminNotice = (data) => request.post('/admin/notifications', data, { silent: true })
export const deleteAdminNotification = (id) => request.delete(`/admin/notifications/${id}`)

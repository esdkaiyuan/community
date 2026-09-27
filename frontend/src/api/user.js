import request from './request'

// 注册
export const register = (data) => request.post('/users/register', data)

// 登录
export const login = (data) => request.post('/users/login', data)

// 获取当前用户信息
export const getMe = () => request.get('/users/me')

// 更新个人资料
export const updateProfile = (data) => request.put('/users/profile', data)

// 我发表的评论（个人中心「我参与的讨论」）
export const getMyComments = (params) => request.get('/users/me/comments', { params })

// 个人数据概览（发布/评论/收藏/获赞）
export const getMyStats = () => request.get('/users/me/stats')

// 我的收藏（分页）
export const getMyFavorites = (params) => request.get('/users/me/favorites', { params })

import request from './request'

// 注册
export const register = (data) => request.post('/users/register', data)

// 登录
export const login = (data) => request.post('/users/login', data)

// 获取当前用户信息
export const getMe = () => request.get('/users/me')

// 更新个人资料
export const updateProfile = (data) => request.put('/users/profile', data)

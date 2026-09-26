import request from './request'

// 通知列表（分页，含未读数）
export const getNotifications = (params) => request.get('/notifications', { params })

// 未读数
export const getUnreadCount = () => request.get('/notifications/unread-count')

// 标记已读：{ ids: [...] } 或 { all: true }
export const markRead = (data) => request.post('/notifications/read', data)

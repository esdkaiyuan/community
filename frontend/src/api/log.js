import request from './request'

// 我的操作记录（我做成了什么）。
// 后端只按「当前登录用户」过滤，不接受任何 userId 参数 —— 能读到什么由「你是谁」决定。
export const getMyLogs = (params) => request.get('/logs/me', { params })

// 针对**我**账号的被拒尝试（别人对我没做成的：撞库、账号枚举、伪造令牌）。
// 与上面互补，走的是另一张表（security_events，含聚合列 occurrences）。
export const getMySecurityEvents = (params) => request.get('/logs/me/security', { params })

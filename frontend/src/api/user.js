import request from './request'

// 注册
export const register = (data) => request.post('/users/register', data)

// 登录
export const login = (data) => request.post('/users/login', data)

// 统一身份认证服务：邮箱验证码发送 / 注册 / 登录 / 找回密码。
// silent：这几类错误都要就地显示在输入框旁（验证码错误、发送太频繁），
// 不应该再叠一张全局提示。
export const sendEmailCode = (data) => request.post('/users/email/send-code', data, { silent: true })
export const registerWithEmailCode = (data) => request.post('/users/register/email', data)
export const loginWithEmailCode = (data) => request.post('/users/login/email', data, { silent: true })
export const resetPasswordWithEmailCode = (data) =>
  request.post('/users/password/reset', data, { silent: true })

// 获取当前用户信息
export const getMe = () => request.get('/users/me')

// 更新个人资料
export const updateProfile = (data) => request.put('/users/profile', data)

// 修改登录密码。成功后服务端会**作废此前签发的所有令牌**（其他设备需要重新登录），
// 并在响应里换发一张新令牌 —— 调用方必须立刻把它落回本地，否则当前页面下一次请求就 401。
// silent：错误由改密表单就地红字显示（「当前密码不正确」贴着输入框才看得懂），
// 不再叠一张全局提示 —— 见 request.js 对 silent 的说明
export const updatePassword = (data) => request.put('/users/password', data, { silent: true })

// 我发表的评论（个人中心「我参与的讨论」）
export const getMyComments = (params) => request.get('/users/me/comments', { params })

// 公开主页（任何人可看，响应不含 email）
export const getPublicProfile = (id) => request.get(`/users/${id}`)

// 个人数据概览（发布/评论/收藏/获赞）
export const getMyStats = () => request.get('/users/me/stats')

// 我的收藏（分页）
export const getMyFavorites = (params) => request.get('/users/me/favorites', { params })

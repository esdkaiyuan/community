// 邮箱格式的唯一前端口径：登录 / 注册 / 找回密码 / 发送验证码都从这里取，
// 避免四个页面各写一份正则慢慢漂移（后端 user.service.js 的 EMAIL_RE 保持同形）。
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const isValidEmail = (value) => EMAIL_RE.test(String(value ?? '').trim())
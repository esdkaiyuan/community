const rateLimit = require('express-rate-limit')

// 全局基础限流：单 IP 15 分钟内最多 600 次请求
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 600,
  standardHeaders: true,
  legacyHeaders: false,
  message: { code: 429, message: '请求过于频繁，请稍后再试' }
})

// 登录/注册等敏感接口的更严格限流
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
  message: { code: 429, message: '尝试次数过多，请 15 分钟后再试' }
})

// 图片上传：比全局严格、比登录宽松。上传是重 IO 操作，
// 单 IP 15 分钟 40 张足够正常使用，又能挡住脚本刷磁盘
const uploadLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 40,
  standardHeaders: true,
  legacyHeaders: false,
  message: { code: 429, message: '上传过于频繁，请稍后再试' }
})

// 改密：需要有效登录态，真正的滥用场景是「拿到令牌后反复猜当前密码」。
// 比登录（30 次 / 15 分钟）严格，又不与它共用配额 —— 否则改一次密码会吃掉登录额度
const passwordLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 15,
  standardHeaders: true,
  legacyHeaders: false,
  message: { code: 429, message: '尝试次数过多，请 15 分钟后再试' }
})

// 邮箱验证码发送：外部服务本身有「同一邮箱 60 秒一次」的限制，
// 这里再加一层按 IP 的闸门，避免脚本换邮箱地址刷爆邮件额度。
const emailCodeLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: { code: 429, message: '验证码发送过于频繁，请稍后再试' }
})

module.exports = { apiLimiter, authLimiter, uploadLimiter, passwordLimiter, emailCodeLimiter }

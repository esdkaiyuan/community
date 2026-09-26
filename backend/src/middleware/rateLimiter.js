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

module.exports = { apiLimiter, authLimiter }

const jwt = require('jsonwebtoken')
const env = require('../config/env')

// tv = 会话版本（users.token_version）。令牌里带上签发时的版本，auth 中间件据此判断
// 「这张令牌是否已经被一次改密作废」。旧令牌没有 tv（历史签发）时按 0 处理，
// 于是「从没改过密码的用户」在部署这版之后不会被强制登出。
const generateToken = (userId, tokenVersion = 0) =>
  jwt.sign({ userId, tv: Number(tokenVersion) || 0 }, env.jwt.secret, { expiresIn: env.jwt.expiresIn })

const verifyToken = (token) => jwt.verify(token, env.jwt.secret)

module.exports = { generateToken, verifyToken }

const { verifyToken } = require('../utils/jwt')
const ApiError = require('../utils/ApiError')

const extractToken = (req) => {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) return null
  return header.slice(7)
}

// 强制认证
const auth = (req, _res, next) => {
  try {
    const token = extractToken(req)
    if (!token) throw ApiError.unauthorized('未提供认证令牌')

    const decoded = verifyToken(token)
    req.user = { userId: decoded.userId }
    next()
  } catch (error) {
    next(error.statusCode === 401 ? error : ApiError.unauthorized('认证令牌无效或已过期'))
  }
}

// 可选认证：有 token 就解析，没有也放行（用于详情页返回当前用户点赞/参与状态）
const optionalAuth = (req, _res, next) => {
  const token = extractToken(req)
  if (token) {
    try {
      const decoded = verifyToken(token)
      req.user = { userId: decoded.userId }
    } catch {
      // 无效 token 视为未登录，不阻断请求
    }
  }
  next()
}

module.exports = { auth, optionalAuth }

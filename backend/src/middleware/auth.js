const { verifyToken } = require('../utils/jwt')
const ApiError = require('../utils/ApiError')
const securityEventService = require('../services/securityEvent.service')

const extractToken = (req) => {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) return null
  return header.slice(7)
}

// 强制认证
//
// ⚠️ 本函数是 async，而本项目用的是 Express 4（异步中间件的 reject **不会**被自动转给
// errorHandler，请求会直接挂住）。所以这里每一处 await 都必须自己兜住异常 —— 下面
// 留痕那段单独套了 try/catch，就是为此。改动这里时不要图省事把 try 去掉。
const auth = async (req, _res, next) => {
  const token = extractToken(req)
  // 「没带 token」不记安全事件：这是未登录用户的正常访问（前端路由守卫之外还有
  // 直接访问 URL、脚本调用等），记了只会让日志被噪音淹没。
  if (!token) return next(ApiError.unauthorized('未提供认证令牌'))

  let failure = null
  let decoded = null
  try {
    decoded = verifyToken(token)
  } catch (error) {
    failure = error
  }

  if (!failure) {
    req.user = { userId: decoded.userId }
    return next()
  }

  const apiError =
    failure.statusCode === 401 ? failure : ApiError.unauthorized('认证令牌无效或已过期')

  // 只记「带了 token 却验不过」里**真正可疑**的那一类：
  //   - TokenExpiredError：签名是对的，只是过期了 —— 正常使用里最常见的一种，
  //     用户隔几天回来点收藏就会遇到，记进安全事件属于纯噪音；
  //   - 其余（签名错 / 格式错 / 载荷被改）：说明有人在伪造或篡改令牌，值得留痕。
  // 这个区分靠 jsonwebtoken 的错误类型，不要去 match message 文本。
  if (failure.name !== 'TokenExpiredError') {
    try {
      await securityEventService.logTokenRejected({
        reason: '认证令牌无效（签名或格式异常）',
        req
      })
    } catch {
      // 留痕失败绝不能把本该是 401 的响应变成 500 / 挂住请求
    }
  }

  return next(apiError)
}

// 可选认证：有 token 就解析，没有也放行（用于详情页返回当前用户点赞/参与状态）
//
// 这里**刻意不留痕**：它天生就是「验证失败就当未登录」的静默退化路径，
// 而浏览器里一个过期的 token 会让每次浏览都触发一次 —— 记了就是洪水。
// 需要留痕的异常（伪造 token）在 auth 那条路上已经记了。
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

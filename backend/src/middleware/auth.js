const { verifyToken } = require('../utils/jwt')
const { User } = require('../models')
const ApiError = require('../utils/ApiError')
const createLogger = require('../utils/logger')
const securityEventService = require('../services/securityEvent.service')

const log = createLogger('auth')

const extractToken = (req) => {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) return null
  return header.slice(7)
}

// 会话是否仍然有效：JWT 里的 tv 必须等于 users.token_version。
//
// 🔥 为什么必须有这一层（它是「改密码」功能的另一半）：JWT 是无状态的 —— 令牌一经签发，
// 服务端在到期前没有任何办法否定它。所以如果改密只做了「把 password 列换个哈希」，
// 一张已经泄漏的令牌在改密之后**照样能用满 JWT_EXPIRES_IN（默认 7 天）**。
// 而改密最典型的触发场景恰恰是「令牌/密码可能已泄漏」，等于最关键的时候没生效。
//
// 代价是一次主键查询。受保护接口本来就要查库，多一次 PK lookup 可忽略；
// optionalAuth 只在「请求里真的带了 token」时才查 —— 未登录刷广场不产生任何额外查询。
const isSessionActive = async (userId, tokenVersion) => {
  const user = await User.findByPk(userId, { attributes: ['id', 'token_version'] })
  if (!user) return false
  return Number(user.token_version || 0) === Number(tokenVersion || 0)
}

// 强制认证
//
// ⚠️ 本函数是 async，而本项目用的是 Express 4（异步中间件的 reject **不会**被自动转给
// errorHandler，请求会直接挂住）。所以这里每一处 await 都必须自己兜住异常 —— 下面留痕
// 与会话校验两段各自套了 try/catch，就是为此。改动这里时不要图省事把 try 去掉。
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

  if (failure) {
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

  // 签名过了，再问一句「这张令牌有没有被一次改密作废」。
  // ⚠️ 这一层**刻意不记安全事件**：它不是攻击信号 —— 最常见的来源恰恰是用户自己
  // 在别的标签页 / 别的设备上留着的旧令牌（改密后第一次请求就会撞上），记了是自刷噪音。
  let active
  try {
    active = await isSessionActive(decoded.userId, decoded.tv)
  } catch (error) {
    // 查库失败**不能**当成「会话失效」：那会把一次数据库抖动变成全员登出
    // （前端收到 401 就清本地会话）。转成 500，前端对 5xx 只提示「服务暂时不可用」，
    // 不会清登录态、也不会跳登录页。
    log.error('会话版本校验失败:', error.message)
    return next(new Error('会话状态校验失败'))
  }
  if (!active) return next(ApiError.unauthorized('登录状态已失效，请重新登录'))

  req.user = { userId: decoded.userId }
  return next()
}

// 可选认证：有 token 就解析，没有也放行（用于详情页返回当前用户点赞/参与状态）
//
// 这里**刻意不留痕**：它天生就是「验证失败就当未登录」的静默退化路径，
// 而浏览器里一个过期的 token 会让每次浏览都触发一次 —— 记了就是洪水。
// 被改密作废的旧令牌同样走这条静默退化：广场是公开页面，最坏结果只是「看起来没登录」。
// 需要留痕的异常（伪造 token）在 auth 那条路上已经记了。
//
// ⚠️ 本函数现在是 async（多了一次会话版本查询）：Express 4 不会为 async 中间件兜 reject，
// 整段必须自己 try/catch，且 next() 一定要在 try 之外无条件调用 —— 否则请求会挂死。
const optionalAuth = async (req, _res, next) => {
  const token = extractToken(req)
  if (!token) return next()
  try {
    const decoded = verifyToken(token)
    if (await isSessionActive(decoded.userId, decoded.tv)) {
      req.user = { userId: decoded.userId }
    }
  } catch {
    // 无效 / 过期 / 已被改密作废的 token 一律视为未登录，不阻断请求
  }
  next()
}

module.exports = { auth, optionalAuth }

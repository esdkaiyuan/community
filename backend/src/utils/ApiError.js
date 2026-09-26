// 业务错误：服务层抛出，由全局错误处理中间件统一转为 HTTP 响应
class ApiError extends Error {
  constructor(statusCode, message, details) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.details = details
    Error.captureStackTrace(this, this.constructor)
  }

  static badRequest(message, details) {
    return new ApiError(400, message, details)
  }

  static unauthorized(message = '未登录或登录已过期') {
    return new ApiError(401, message)
  }

  static forbidden(message = '没有权限执行此操作') {
    return new ApiError(403, message)
  }

  static notFound(message = '资源不存在') {
    return new ApiError(404, message)
  }

  static conflict(message) {
    return new ApiError(409, message)
  }
}

module.exports = ApiError

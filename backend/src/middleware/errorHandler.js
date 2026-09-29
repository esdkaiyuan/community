const ApiError = require('../utils/ApiError')
const createLogger = require('../utils/logger')

const log = createLogger('http')

// 404：未匹配到任何路由
const notFound = (req, _res, next) => {
  next(ApiError.notFound(`接口不存在: ${req.method} ${req.originalUrl}`))
}

// 全局错误处理：ApiError 按状态码返回；Sequelize 校验错误转 400；其余一律 500
// eslint-disable-next-line no-unused-vars
const errorHandler = (err, req, res, _next) => {
  let statusCode = err.statusCode || 500
  let message = err.message || '服务器错误'
  let details

  if (err.name === 'SequelizeUniqueConstraintError') {
    statusCode = 409
    message = '数据已存在，请勿重复提交'
    details = err.errors?.map((e) => e.message)
  } else if (err.name === 'SequelizeValidationError') {
    statusCode = 400
    message = '参数校验失败'
    details = err.errors?.map((e) => e.message)
  } else if (err.name === 'SequelizeDatabaseError') {
    statusCode = 500
    message = '数据存储异常'
    log.error('数据库错误:', err.original?.message || err.message)
  }

  // body-parser 的报错（JSON 语法错、请求体超限）状态码本身是对的（400/413），
  // 但 message 是英文技术原文，而前端对 4xx 是**原样显示**给用户的 ——
  // 不翻译的话用户会看到 "Unexpected token , in JSON at position 19"。
  // 按 err.type 判断（比 match message 文本可靠）。
  if (err.type === 'entity.parse.failed') {
    statusCode = 400
    message = '请求内容不是合法的 JSON'
  } else if (err.type === 'entity.too.large') {
    statusCode = 413
    message = '提交的内容太大了，请精简后再试'
  }

  if (statusCode >= 500) {
    log.error(`${req.method} ${req.originalUrl} ->`, err.stack || err.message)
  } else {
    log.debug(`${req.method} ${req.originalUrl} -> ${statusCode} ${message}`)
  }

  res.status(statusCode).json({
    code: statusCode,
    message,
    ...(details ? { details } : {})
  })
}

module.exports = { notFound, errorHandler }

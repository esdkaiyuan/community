require('dotenv').config()

const path = require('node:path')
const env = require('./src/config/env')
const createLogger = require('./src/utils/logger')
const express = require('express')
const cors = require('cors')
const helmet = require('helmet')

const routes = require('./src/routes')
const { sequelize } = require('./src/models')
const { notFound, errorHandler } = require('./src/middleware/errorHandler')
const { apiLimiter } = require('./src/middleware/rateLimiter')

const log = createLogger('server')
const app = express()

// 安全与解析
app.set('trust proxy', 1)
app.use(helmet())
app.use(
  cors({
    origin: env.isProd ? (process.env.CORS_ORIGIN || true) : true,
    credentials: true
  })
)
app.use(express.json({ limit: '1mb' }))
app.use(express.urlencoded({ extended: true }))

// 用户上传的封面：静态直出。
// 生产环境一般由 Nginx / CDN 承担这一层，但本机开发必须由 Express 提供，
// 否则 /uploads/* 会落进 notFound 变成 404（历史上就是这么丢的）。
app.use(
  '/uploads',
  express.static(path.join(__dirname, 'uploads'), {
    maxAge: '7d',
    immutable: true,
    index: false,
    dotfiles: 'deny'
  })
)

// 业务路由（全局限流）
app.use('/api', apiLimiter, routes)

// 404 与全局错误处理（必须最后注册）
app.use(notFound)
app.use(errorHandler)

const server = app.listen(env.port, () => {
  log.info(`Server is running on port ${env.port} (${env.nodeEnv})`)
})

// 优雅停机：等待在途请求结束后关闭连接池
const shutdown = async (signal) => {
  log.info(`${signal} received, shutting down...`)
  server.close(async () => {
    try {
      await sequelize.close()
      log.info('Database connection closed')
    } catch (error) {
      log.error('Error closing database:', error.message)
    }
    process.exit(0)
  })
  // 兜底：10 秒后强制退出
  setTimeout(() => process.exit(1), 10_000).unref()
}

process.on('SIGINT', () => shutdown('SIGINT'))
process.on('SIGTERM', () => shutdown('SIGTERM'))

// 未捕获异常兜底：记录后退出，交给 PM2 重启
process.on('unhandledRejection', (reason) => {
  log.error('Unhandled rejection:', reason)
})

module.exports = app

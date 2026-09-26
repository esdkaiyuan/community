// 集中读取并校验环境变量，启动时快速失败
require('dotenv').config()

const required = (name, fallback) => {
  const value = process.env[name] ?? fallback
  if (value === undefined || value === '') {
    throw new Error(`缺少必需的环境变量: ${name}`)
  }
  return value
}

const env = {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '5000', 10),
  isProd: process.env.NODE_ENV === 'production',

  db: {
    name: required('DB_NAME', 'community_platform'),
    user: required('DB_USER', 'root'),
    password: required('DB_PASSWORD', ''),
    host: required('DB_HOST', '127.0.0.1'),
    port: parseInt(process.env.DB_PORT || '3306', 10)
  },

  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '7d'
  }
}

// 生产环境必须显式配置 JWT 密钥，开发环境给出兜底并警告
if (!env.jwt.secret) {
  if (env.isProd) {
    throw new Error('生产环境必须配置 JWT_SECRET')
  }
  console.warn('[env] 警告: 未配置 JWT_SECRET，开发环境使用临时密钥（重启后已登录用户需重新登录）')
  env.jwt.secret = `dev-secret-${Date.now()}`
}

module.exports = env

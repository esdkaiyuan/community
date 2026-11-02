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
  },

  // 统一身份认证服务（邮箱验证码 / 密码登录 / 密码重置）。
  // 外部 API Key 只放环境变量，绝不写进代码或仓库；缺省时相关接口返回 503，
  // 不影响本项目原有的账号密码登录。
  emailVerify: {
    baseUrl: process.env.EMAIL_VERIFY_BASE_URL || 'https://email.esdkaiyuan.online/api/v1',
    apiKey: process.env.EMAIL_VERIFY_API_KEY || '',
    timeoutMs: parseInt(process.env.EMAIL_VERIFY_TIMEOUT_MS || '10000', 10)
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

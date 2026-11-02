// 统一身份认证服务（邮箱验证码 / 密码登录 / 密码重置）的接入层。
//
// 外部服务是用户身份的唯一真源：注册、密码登录、验证码登录、找回密码都走它。
// 本项目的 users 表只作为「项目 / 评论等业务外键」所需的本地镜像（按邮箱关联），
// 不再新增第二套身份体系。
//
// 凭据纪律：API Key 只从环境变量读取，任何日志、异常、响应里都不出现。
const http = require('node:http')
const https = require('node:https')
const { URL } = require('node:url')
const env = require('../config/env')
const ApiError = require('../utils/ApiError')
const createLogger = require('../utils/logger')

const log = createLogger('email-auth')

const MAX_RESPONSE_BYTES = 1024 * 1024
const timeoutMs = Number.isFinite(env.emailVerify.timeoutMs) && env.emailVerify.timeoutMs > 0
  ? env.emailVerify.timeoutMs
  : 10000

class EmailServiceError extends Error {
  constructor(httpStatus, message, payload) {
    super(message || '邮箱验证服务请求失败')
    this.name = 'EmailServiceError'
    this.httpStatus = httpStatus
    this.payload = payload || null
  }
}

const isConfigured = () => Boolean(env.emailVerify.apiKey)

const requestJson = (targetUrl, { method = 'GET', headers = {}, body, timeoutMs }) =>
  new Promise((resolve, reject) => {
    let target
    try {
      target = new URL(targetUrl)
    } catch {
      reject(new EmailServiceError(0, '邮箱验证服务地址配置错误'))
      return
    }

    const transport = target.protocol === 'http:' ? http : https
    const payload = body === undefined ? null : Buffer.from(JSON.stringify(body))
    const req = transport.request(
      {
        protocol: target.protocol,
        hostname: target.hostname,
        port: target.port || (target.protocol === 'http:' ? 80 : 443),
        path: `${target.pathname}${target.search}`,
        method,
        headers: {
          Accept: 'application/json',
          ...(payload ? { 'Content-Type': 'application/json', 'Content-Length': payload.length } : {}),
          ...headers
        }
      },
      (res) => {
        let raw = ''
        res.setEncoding('utf8')
        res.on('data', (chunk) => {
          raw += chunk
          if (raw.length > MAX_RESPONSE_BYTES) {
            req.destroy(new Error('response too large'))
          }
        })
        res.on('end', () => {
          let parsed = null
          try {
            parsed = raw ? JSON.parse(raw) : null
          } catch {
            // 非 JSON 响应（网关错误页等）按纯文本 message 处理
          }
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(
              new EmailServiceError(
                res.statusCode,
                parsed?.message || `邮箱验证服务返回 HTTP ${res.statusCode}`,
                parsed
              )
            )
            return
          }
          resolve(parsed)
        })
      }
    )

    req.setTimeout(timeoutMs, () => req.destroy(new Error('timeout')))
    req.on('error', (error) => {
      reject(new EmailServiceError(0, error.message || '邮箱验证服务连接失败'))
    })
    if (payload) req.write(payload)
    req.end()
  })

const call = async (path, { method = 'POST', body, useApiKey = true, bearerToken } = {}) => {
  if (!isConfigured()) {
    throw new ApiError(503, '邮箱验证服务未配置，请联系管理员')
  }
  const headers = {}
  if (useApiKey) headers['X-API-Key'] = env.emailVerify.apiKey
  if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`

  return requestJson(`${env.emailVerify.baseUrl.replace(/\/+$/, '')}${path}`, {
    method,
    headers,
    body,
    timeoutMs
  })
}

const retryMessage = (payload) => {
  const retryAfter = Number(payload?.data?.retry_after)
  return Number.isFinite(retryAfter) && retryAfter > 0
    ? `操作过于频繁，请 ${retryAfter} 秒后重试`
    : '操作过于频繁，请稍后重试'
}

// 把外部服务的失败翻译成本项目统一的 ApiError。
// 4xx 的用户文案保留（服务端已写成中文），5xx / 网络错误一律 503。
const toApiError = (error, fallbackMessage) => {
  if (error instanceof ApiError) return error
  if (!(error instanceof EmailServiceError)) {
    log.error('邮箱验证服务未知错误:', error.message)
    return new ApiError(503, fallbackMessage)
  }

  if (error.httpStatus === 0) {
    log.warn('邮箱验证服务不可达:', error.message)
    return new ApiError(503, '邮箱验证服务暂时不可用，请稍后重试')
  }
  if (error.httpStatus === 429) {
    return new ApiError(429, retryMessage(error.payload))
  }
  if (error.httpStatus === 401 || error.httpStatus === 403) {
    // 这是我们的 API Key 出问题，不是用户输入错；不要把服务端细节暴露给用户。
    log.error(`邮箱验证服务鉴权失败 (HTTP ${error.httpStatus}):`, error.message)
    return new ApiError(503, '邮箱验证服务配置异常，请联系管理员')
  }
  if (error.httpStatus >= 500) {
    log.warn(`邮箱验证服务暂时不可用 (HTTP ${error.httpStatus}):`, error.message)
    return new ApiError(503, '邮箱验证服务暂时不可用，请稍后重试')
  }
  return new ApiError(error.httpStatus === 404 ? 400 : error.httpStatus, error.message || fallbackMessage)
}

const extractUser = (data) => ({
  externalId: data?.user?.id ?? data?.user_id ?? data?.id ?? null,
  email: data?.user?.email ?? data?.verified_email ?? data?.email ?? null,
  nickname: data?.user?.nickname ?? data?.nickname ?? null
})

exports.isConfigured = isConfigured

exports.sendCode = async (email) => {
  try {
    const data = await call('/send-code', { body: { email } })
    return data
  } catch (error) {
    throw toApiError(error, '验证码发送失败，请稍后重试')
  }
}

exports.register = async ({ email, code, password, nickname }) => {
  try {
    const data = await call('/auth/register', {
      body: {
        email,
        code,
        password,
        confirmPassword: password,
        ...(nickname ? { nickname } : {})
      }
    })
    return { user: extractUser(data), raw: data }
  } catch (error) {
    throw toApiError(error, '注册失败，请稍后重试')
  }
}

// 密码登录：返回 ok/reason 而不是抛异常，调用方需要据此决定是否回退到本地密码。
//   invalid     —— 邮箱或密码错（可以回退本地校验）
//   unavailable —— 服务不可用（可回退本地，但两者都失败时要明确告知服务异常）
exports.passwordLogin = async ({ email, password }) => {
  try {
    const data = await call('/auth/login', {
      body: { email, password },
      useApiKey: false
    })
    return {
      ok: true,
      accessToken: data?.access_token || data?.token || null,
      user: extractUser(data)
    }
  } catch (error) {
    if (error instanceof EmailServiceError && [400, 401, 404].includes(error.httpStatus)) {
      return { ok: false, reason: 'invalid', message: error.message }
    }
    log.warn('邮箱验证服务密码登录失败:', error.message)
    return { ok: false, reason: 'unavailable' }
  }
}

exports.verifyCode = async ({ email, code }) => {
  try {
    const data = await call('/verify-code', { body: { email, code } })
    return {
      sessionToken: data?.token || null,
      user: extractUser(data)
    }
  } catch (error) {
    throw toApiError(error, '验证码无效或已过期，请重新获取')
  }
}

exports.getProfile = async (sessionToken) => {
  if (!sessionToken) return null
  try {
    const data = await call('/auth/me', { method: 'GET', useApiKey: false, bearerToken: sessionToken })
    return extractUser(data)
  } catch (error) {
    // 资料读取失败不影响「验证码已验证」这个事实，调用方会退回邮箱前缀生成用户名
    log.warn('读取外部用户资料失败:', error.message)
    return null
  }
}

exports.resetPassword = async ({ email, code, password }) => {
  try {
    return await call('/auth/password/reset', {
      body: {
        email,
        code,
        password,
        confirmPassword: password
      }
    })
  } catch (error) {
    throw toApiError(error, '密码重置失败，请稍后重试')
  }
}

// 已登录用户改密：先用旧密码换一张外部会话令牌，再调用外部改密接口。
// 这是「本地密码」与「外部身份中心」保持同步的关键一步；失败只记日志，
// 本地改密仍然生效（见 user.service.changePassword 的注释）。
exports.changePassword = async ({ email, oldPassword, newPassword }) => {
  const login = await exports.passwordLogin({ email, password: oldPassword })
  if (!login.ok || !login.accessToken) {
    return { ok: false, reason: login.reason || 'invalid' }
  }
  try {
    await call('/auth/password/change', {
      body: {
        oldPassword,
        newPassword,
        confirmPassword: newPassword
      },
      useApiKey: false,
      bearerToken: login.accessToken
    })
    return { ok: true }
  } catch (error) {
    log.warn('同步外部密码失败:', error.message)
    return { ok: false, reason: 'failed' }
  }
}

exports.EmailServiceError = EmailServiceError
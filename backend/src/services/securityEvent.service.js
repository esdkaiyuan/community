// 安全事件服务：**被拒的尝试**的唯一写入入口。
//
// 与 activityLog.service 的分工（读之前先看这段）：
//   activityLog  记「谁做成了什么」—— 有身份、可逐条读、给用户自己看。
//   本模块        记「有人尝试但没成功」—— 大多没有身份、按来源聚合、给运维与取证看。
//
// 四条约束，全部在这里强制：
//   1. **事件白名单**：只认 EVENTS 里的取值，写错字符串不会静默入库。
//   2. **绝不记密码**：字段是一个一个显式取出来拼的（不是把 req.body 摊开写），
//      所以调用方多传 password 也没用 —— 「按白名单构造」而不是「按传入对象遍历」
//      这条纪律与 activityLog.sanitizeDetail 完全一致。
//   3. **账号脱敏**：只存 maskAccount 之后的结果，明文邮箱 / 用户名不进库。
//   4. **异常不外抛**：留痕失败绝不能把「本该是 401 的响应」变成 500。
const crypto = require('node:crypto')
const { Op } = require('sequelize')
const { SecurityEvent, sequelize } = require('../models')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const ApiError = require('../utils/ApiError')
const createLogger = require('../utils/logger')
const {
  sanitizeLogText,
  sanitizeIp,
  sanitizeUserAgent,
  maskAccount
} = require('../utils/logSanitize')

const log = createLogger('security')

const EVENTS = Object.freeze({
  LOGIN_REJECTED: 'auth.login.rejected',
  REGISTER_REJECTED: 'auth.register.rejected',
  TOKEN_REJECTED: 'auth.token.rejected',
  PASSWORD_REJECTED: 'auth.password.rejected'
})
const EVENT_VALUES = Object.freeze(Object.values(EVENTS))

// 聚合窗口：同一 (事件, 来源IP, 账号, 路径) 在窗口内重复发生**只更新既有行**，
// 不做新增。暴力破解的本质就是「同一来源对同一目标反复失败」，一条一行会瞬间把表
// 撑成噪音洪水（也会把真正有信息量的「第一次尝试」淹掉）。合并成「一条带次数的行」，
// 读起来是「这个 IP 在 10 分钟内对 z***@e***.com 试了 47 次」，信息量反而更高。
const AGGREGATE_WINDOW_MS = 10 * 60 * 1000

const REASON_MAX = 120
const ACCOUNT_MAX = 80
const PATH_MAX = 120
const METHOD_MAX = 10

// 聚合键。用 sha256 而不是直接拼字符串，是为了定长 + 可以直接建索引，
// 也顺手避开「ip 为空时 NULL 不参与等值比较」这类陷阱。
//
// 🔥 **target_user_id 必须进键**。这里踩过一次真实的坑：最初只用
// (event, ip, account, path)，而 account 是**脱敏后**的形态 —— `secA…@example.com` 与
// `secB…@example.com` 都脱敏成 `s***@e***.com`，于是两个**不同的真实账号**被合并进同一行，
// 而且合并时会把 `target_user_id` 覆盖成后一个 —— 那行日志会指向错误的账号，
// 取证价值直接反成负的（指错人比没记更糟）。
// 把 target_user_id 放进键之后：账号存在时按**精确身份**分开聚合；账号不存在时
// （没有 target）才退回脱敏形态 —— 那种情况下本来也没有「指错人」可言。
const buildFingerprint = ({ event, ip, account, targetUserId, path }) =>
  crypto
    .createHash('sha256')
    .update([event, ip || '', account || '', String(targetUserId ?? ''), path || ''].join('\u0000'))
    .digest('hex')

// 路径：**剥掉 query 再存**。留 query 等于把用户/攻击者的请求参数原样抄进日志
// （将来真有人把 token 或邮箱放 query 里就麻烦了），而取证只需要「打了哪个接口」。
const requestPath = (req) => {
  const raw = (req && (req.originalUrl || req.url)) || ''
  return sanitizeLogText(raw.split('?')[0], PATH_MAX) || null
}

// 只接受正整数 ID
const toId = (value) => {
  const n = Number(value)
  return Number.isInteger(n) && n > 0 ? n : null
}

/**
 * 构造「将要落库的一行」。**纯函数**，不碰数据库。
 *
 * 之所以单独抽出来：这是「什么能进日志」的唯一决定点，抽成纯函数后可以在
 * scripts/check-security-log.js 里不经 HTTP、不经数据库直接喂载荷断言输出
 * （比如「传了 password 也绝不会出现在结果里」这种最重要的性质）。
 * 集成测试（scripts/verify_security_events.py）只负责验「它真的落库了、且被聚合」。
 *
 * @returns {object} 白名单字段拼出的行（未含 id / occurrences 等）
 */
const buildEventPayload = ({ event, reason, account, targetUserId, req }) => {
  const ip = sanitizeIp(req && req.ip)
  const accountMasked = maskAccount(account)
  const path = requestPath(req)
  const targetId = toId(targetUserId)
  return {
    event,
    reason: sanitizeLogText(reason, REASON_MAX) || '(无原因)',
    target_user_id: targetId,
    // 只存脱敏形态；maskAccount 的返回值再过一道只是纵深防御（它本身已净化过）
    account: accountMasked ? sanitizeLogText(accountMasked, ACCOUNT_MAX) : null,
    ip,
    user_agent: sanitizeUserAgent(req && req.headers && req.headers['user-agent']),
    path,
    method: sanitizeLogText(req && req.method, METHOD_MAX) || null,
    fingerprint: buildFingerprint({ event, ip, account: accountMasked, targetUserId: targetId, path })
  }
}

/**
 * 落一条安全事件。**永不抛异常**。
 *
 * @returns {Promise<{id:number, merged:boolean}|null>} 失败返回 null；merged 表示被并进了既有行
 */
const recordEvent = async ({ event, reason, account, targetUserId, req }) => {
  try {
    if (!EVENT_VALUES.includes(event)) {
      log.warn(`拒绝写入未知类型的安全事件: ${sanitizeLogText(event, 40) || '(空)'}`)
      return null
    }

    const payload = buildEventPayload({ event, reason, account, targetUserId, req })
    const now = new Date()

    // 窗口内已有同键的行 → 只 +1 并刷新时间，不新增
    const existing = await SecurityEvent.findOne({
      where: {
        fingerprint: payload.fingerprint,
        last_seen_at: { [Op.gte]: new Date(now.getTime() - AGGREGATE_WINDOW_MS) }
      },
      order: [
        ['last_seen_at', 'DESC'],
        ['id', 'DESC']
      ],
      attributes: ['id']
    })

    if (existing) {
      await SecurityEvent.update(
        {
          // ⚠️ 必须是 SQL 层原子自增：读出来 +1 再写回会在并发失败尝试下丢计数
          //（与浏览量那次是同一个坑，见技能里「累加类字段必须原子自增」）
          occurrences: sequelize.literal('occurrences + 1'),
          last_seen_at: now,
          reason: payload.reason,
          user_agent: payload.user_agent,
          // 目标账号后来才识别出来（如先失败于不存在、后失败于已存在）也要补上
          target_user_id: payload.target_user_id
        },
        { where: { id: existing.id } }
      )
      return { id: existing.id, merged: true }
    }

    const row = await SecurityEvent.create({
      ...payload,
      occurrences: 1,
      last_seen_at: now
    })
    return { id: row.id, merged: false }
  } catch (error) {
    log.error('写入安全事件失败:', error.message)
    return null
  }
}

// ---- 对外只暴露「意图命名」的方法，调用方不必知道事件字符串 ----

// 登录失败。
// 刻意不区分「账号不存在」与「密码错误」—— 对外文案本来就一样（防账号枚举），
// 日志里也保持一致，避免这份日志自己变成一份「哪些邮箱真实存在」的名单。
// ⚠️ 绝不要把 password 传进来：本模块只取白名单字段，但源头就不该碰。
exports.logLoginRejected = ({ account, targetUserId, reason, req }) =>
  recordEvent({ event: EVENTS.LOGIN_REJECTED, account, targetUserId, reason, req })

// 注册被拒（校验不过 / 重名）。account 是**尝试注册的用户名**。
exports.logRegisterRejected = ({ account, targetUserId, reason, req }) =>
  recordEvent({ event: EVENTS.REGISTER_REJECTED, account, targetUserId, reason, req })

// 令牌被拒：**只有「带了 token 却验不过」才值得记**。
// 没带 token 是「未登录」（正常），过期 token 是「会话到期」（正常），
// 真正异常的是签名/格式对不上 —— 那是有人在伪造或篡改令牌。
exports.logTokenRejected = ({ reason, targetUserId, req }) =>
  recordEvent({ event: EVENTS.TOKEN_REJECTED, reason, targetUserId, req })

// 改密时「当前密码不正确」。与登录失败同源（都是「不知道密码」），区别在于它发生在一个
// **已经通过认证**的会话里 —— 更像「令牌被盗后试图改密把主人锁在门外」，而不是撞库。
// 身份是确定的（target_user_id 就是当前登录的账号），所以它能归属到人、也就能出现在
// 用户自己的安全提醒里 —— 这正是他必须知道的事。
// ⚠️ 同样绝不接受 password 参数：本模块按白名单取值，但源头就不该碰。
exports.logPasswordChangeRejected = ({ account, targetUserId, reason, req }) =>
  recordEvent({ event: EVENTS.PASSWORD_REJECTED, account, targetUserId, reason, req })

// ---- 读取：只允许查「针对自己账号」的尝试 ----
// 与 activity_logs 的 /logs/me 同一思路：能读到什么由「你是谁」决定，不接受任何
// userId 参数。全站流水（按 IP / 按事件类型横查）需要角色体系，本项目没有，刻意不开。

const toClientEvent = (row) => ({
  id: row.id,
  event: row.event,
  reason: row.reason,
  account: row.account,
  ip: row.ip,
  occurrences: row.occurrences,
  firstSeenAt: row.created_at,
  lastSeenAt: row.last_seen_at
})

exports.listMine = async ({ userId, page = 1, pageSize = 20, event }) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 20 })

  const where = { target_user_id: userId }
  if (event !== undefined && event !== null && event !== '') {
    // 无效筛选值明确报错（与 /logs/me 的 action 同一口径），不做静默忽略
    if (!EVENT_VALUES.includes(event)) throw ApiError.badRequest('不支持的安全事件类型')
    where.event = event
  }

  const { count, rows } = await SecurityEvent.findAndCountAll({
    where,
    order: [
      ['last_seen_at', 'DESC'],
      ['id', 'DESC']
    ],
    limit,
    offset: (page - 1) * limit
  })

  return { events: rows.map(toClientEvent), total: count, page, pageSize: limit }
}

exports.EVENTS = EVENTS
exports.EVENT_VALUES = EVENT_VALUES
exports.AGGREGATE_WINDOW_MS = AGGREGATE_WINDOW_MS
exports.recordEvent = recordEvent
exports.buildEventPayload = buildEventPayload

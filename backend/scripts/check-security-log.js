/**
 * 安全事件（被拒的尝试）的纯函数自检。
 *
 * 为什么单独跑一层：安全事件里最要命的两条性质都是「**不该出现的东西没出现**」——
 *   ① 密码（任何形态）绝不能被写进库；
 *   ② 账号标识必须脱敏，明文邮箱不能留存。
 * 这两条如果只靠端到端测试，就得真的发一次「密码错」的登录请求，再去库里翻 —— 又慢又绕，
 * 而且「断言通过」只说明那一次没漏。这里直接调构造器（buildEventPayload）喂载荷，
 * 一次覆盖几十种输入，失败信息还能精确到「哪一条漏了」。
 *
 * 端到端那一层（scripts/verify_security_events.py）负责验「它真的落库了、且被聚合了」。
 *
 * 用法（在 backend/ 下）：node scripts/check-security-log.js   —— 退出码 0 表示全绿
 */
const {
  EVENTS,
  EVENT_VALUES,
  buildEventPayload,
  AGGREGATE_WINDOW_MS
} = require('../src/services/securityEvent.service')
const { maskAccount, sanitizeLogText, sanitizeIp } = require('../src/utils/logSanitize')

const failures = []
const check = (label, cond) => {
  console.log((cond ? '  OK  ' : ' FAIL ') + label)
  if (!cond) failures.push(label)
}

// eslint-disable-next-line no-control-regex -- 要断言「没有控制字符」就必须先匹配它们
const hasControlChar = (text) => /[\u0000-\u001F\u007F-\u009F]/.test(text)
// eslint-disable-next-line no-control-regex -- 同上：ANSI 转义的开头就是 ESC
const hasAnsi = (text) => /\u001B\[/.test(text)

const fakeReq = (overrides = {}) => ({
  ip: '203.0.113.9',
  method: 'POST',
  originalUrl: '/api/users/login',
  headers: { 'user-agent': 'Mozilla/5.0 (probe)' },
  ...overrides
})

console.log('== A. 账号脱敏：只留极少量特征，不留明文 ==')
{
  const email = maskAccount('zhangsan@example.com')
  check('邮箱脱敏成形如 z***@e***.com', email === 'z***@e***.com')
  check('邮箱脱敏后不含 local part 原文', !email.includes('zhangsan'))
  check('邮箱脱敏后不含域名原文', !email.includes('example'))

  check('非邮箱（用户名）只留首字符', maskAccount('zhangsan') === 'z***')
  check('单字符原样返回（一个字符不构成 PII）', maskAccount('z') === 'z')

  check('空串 -> null', maskAccount('') === null)
  check('null -> null', maskAccount(null) === null)
  check('undefined -> null', maskAccount(undefined) === null)

  // 注入面：CRLF / ANSI / 零宽经脱敏也不能残留
  const crlf = maskAccount('a\r\nb@x.com')
  check('账号里的 CRLF 被压平（脱敏前先净化）', !crlf.includes('\n') && !crlf.includes('\r'))
  check('压平后的账号仍能脱敏成形', crlf === 'a***@x***.com')
  const ansi = maskAccount('\u001b[31mbad\u001b[0m@x.com')
  check('账号里的 ANSI 被摘除', !hasAnsi(ansi))
  const nul = maskAccount('a\u0000b@x.com')
  check('账号里的 NUL 被摘除', !hasControlChar(nul))

  // 超长：不能靠账号字段把一行撑爆
  const long = maskAccount('x'.repeat(500) + '@example.com')
  check('超长账号被截断', long.length <= 80)

  const noDomain = maskAccount('abc@')
  check('畸形邮箱（@ 结尾）退化成首字符形态', noDomain === 'a***')
}

console.log('== B. 落库行：白名单构造，密码与明文都进不来 ==')
{
  // 🔥 最重要的一条：调用方把 password 一起传进来，也绝不能出现在结果里
  const payload = buildEventPayload({
    event: EVENTS.LOGIN_REJECTED,
    reason: '邮箱或密码错误',
    account: 'zhangsan@example.com',
    targetUserId: 7,
    req: fakeReq(),
    // 下面这些是「调用方手滑多传」的模拟：本函数按字段显式取值，多传天然无效
    password: 'TOPSECRET123',
    password_hash: '$2b$10$SECRETHASH',
    body: { email: 'zhangsan@example.com', password: 'TOPSECRET123' }
  })
  const serialized = JSON.stringify(payload)
  check('多传的 password 不进结果', !serialized.includes('TOPSECRET123'))
  check('多传的 password_hash 不进结果', !serialized.includes('SECRETHASH'))
  check('结果里没有 password 这个键', !Object.prototype.hasOwnProperty.call(payload, 'password'))
  check('结果里没有 body 这个键', !Object.prototype.hasOwnProperty.call(payload, 'body'))

  // 明文账号不进结果
  check('account 列是脱敏值', payload.account === 'z***@e***.com')
  check('account 列不含明文邮箱', !serialized.includes('zhangsan@example.com'))
  check('结果里没有 email 这个键（不另存一份明文）',
        !Object.prototype.hasOwnProperty.call(payload, 'email'))

  // 路径必须剥掉 query：将来有人把 token / 邮箱放 query 里也不会被抄进日志
  const withQuery = buildEventPayload({
    event: EVENTS.TOKEN_REJECTED,
    reason: '认证令牌无效（签名或格式异常）',
    req: fakeReq({ originalUrl: '/api/logs/me?token=LEAKME&page=1' })
  })
  check('path 不含 query', withQuery.path === '/api/logs/me')
  check('query 里的敏感值没被抄进日志', !JSON.stringify(withQuery).includes('LEAKME'))

  // reason 是系统自己的文案，但仍然过净化（防「将来有人把用户输入拼进 reason」）
  const dirtyReason = buildEventPayload({
    event: EVENTS.REGISTER_REJECTED,
    reason: '被拒\r\n[FATAL] 伪造行\u001b[31m\u200b',
    req: fakeReq()
  })
  check('reason 里的 CRLF 被压平', !dirtyReason.reason.includes('\n') && !dirtyReason.reason.includes('\r'))
  check('reason 里的 ANSI 被摘除', !hasAnsi(dirtyReason.reason))
  check('reason 里的零宽被摘除', !dirtyReason.reason.includes('\u200b'))
  check('reason 为空时给兜底文案（列 NOT NULL）',
        buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: '', req: fakeReq() }).reason === '(无原因)')

  // ip / ua / method / targetUserId
  check('合法 IPv4 保留', buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', req: fakeReq() }).ip === '203.0.113.9')
  const ipv6 = buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', req: fakeReq({ ip: '::1' }) })
  check('合法 IPv6 保留', ipv6.ip === '::1')
  const badIp = buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', req: fakeReq({ ip: '203.0.113.9:5000' }) })
  check('「IP:端口」这种伪 IP 被丢弃（net.isIP 判定）', badIp.ip === null)
  check('无 req 时 ip 为 null（脚本/定时任务场景）',
        buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x' }).ip === null)

  const dirtyUa = buildEventPayload({
    event: EVENTS.TOKEN_REJECTED,
    reason: 'x',
    req: fakeReq({ headers: { 'user-agent': 'UA\r\n伪造\u001b[31m' } })
  })
  check('UA 里的 CRLF 被压平', !dirtyUa.user_agent.includes('\r') && !dirtyUa.user_agent.includes('\n'))
  check('UA 里的 ANSI 被摘除', !hasAnsi(dirtyUa.user_agent))

  check('targetUserId 支持数字', buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', targetUserId: 12 }).target_user_id === 12)
  check('targetUserId 支持数字串', buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', targetUserId: '12' }).target_user_id === 12)
  check('targetUserId 非法（字符串）归 null', buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', targetUserId: 'abc' }).target_user_id === null)
  check('targetUserId 非法（负数）归 null', buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x', targetUserId: -3 }).target_user_id === null)

  // 没有 ip 时 method/path 仍应记录
  const noReq = buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x' })
  check('无 req 时 path / method 为 null 而不是空串', noReq.path === null && noReq.method === null)
}

console.log('== C. 聚合键 fingerprint ==')
{
  const base = { event: EVENTS.LOGIN_REJECTED, reason: '邮箱或密码错误', account: 'a@b.com', req: fakeReq() }
  const p1 = buildEventPayload(base)
  const p2 = buildEventPayload(base)
  check('fingerprint 是 64 位十六进制（sha256）', /^[0-9a-f]{64}$/.test(p1.fingerprint))
  check('同输入 -> 同指纹（窗口内才能合并）', p1.fingerprint === p2.fingerprint)

  const otherAccount = buildEventPayload({ ...base, account: 'b@b.com' })
  check('账号不同 -> 指纹不同', otherAccount.fingerprint !== p1.fingerprint)

  const otherPath = buildEventPayload({ ...base, req: fakeReq({ originalUrl: '/api/users/register' }) })
  check('路径不同 -> 指纹不同', otherPath.fingerprint !== p1.fingerprint)

  const otherIp = buildEventPayload({ ...base, req: fakeReq({ ip: '198.51.100.7' }) })
  check('来源IP 不同 -> 指纹不同', otherIp.fingerprint !== p1.fingerprint)

  const otherEvent = buildEventPayload({ ...base, event: EVENTS.REGISTER_REJECTED })
  check('事件类型不同 -> 指纹不同', otherEvent.fingerprint !== p1.fingerprint)

  // reason 刻意不进指纹：同一账号同一来源反复被拒，合并成「一条带次数的行」比拆成
  // 一堆「原因各异但本质相同」的行更有信息量
  const otherReason = buildEventPayload({ ...base, reason: '邮箱格式不正确' })
  check('原因不同 -> 指纹相同（刻意只按来源+账号+路径聚合）', otherReason.fingerprint === p1.fingerprint)

  // 🔥 回归：脱敏**一定**会碰撞 —— `secA123@example.com` 与 `secB456@example.com` 都变成
  // `s***@e***.com`。所以「目标账号ID」必须进聚合键，否则两个不同账号被并成一行，而且
  // 合并时 target_user_id 会被覆盖成后一个 —— 日志会**指错人**（比没记更糟）。
  // 这是实现后实测抓到的真 bug，别再退化回去。
  const collideA = buildEventPayload({
    event: EVENTS.LOGIN_REJECTED,
    reason: '邮箱或密码错误',
    account: 'secA123@example.com',
    targetUserId: 1,
    req: fakeReq()
  })
  const collideB = buildEventPayload({
    event: EVENTS.LOGIN_REJECTED,
    reason: '邮箱或密码错误',
    account: 'secB456@example.com',
    targetUserId: 2,
    req: fakeReq()
  })
  check('脱敏碰撞：两个账号的 account 列确实相同（构造成立）', collideA.account === collideB.account)
  check('但聚合键按目标账号ID 分开（不会并成一行、不会指错人）', collideA.fingerprint !== collideB.fingerprint)
  check('同一个目标账号仍然聚合到同一条', buildEventPayload({
    event: EVENTS.LOGIN_REJECTED,
    reason: '换个原因也不影响',
    account: 'secA999@example.com',
    targetUserId: 1,
    req: fakeReq()
  }).fingerprint === collideA.fingerprint)
  check('无目标账号时退回脱敏形态聚合（本就没有身份可指错）',
        buildEventPayload({ event: EVENTS.LOGIN_REJECTED, reason: 'x', account: 'secA123@example.com', req: fakeReq() })
          .fingerprint !== collideA.fingerprint)

  // 无 ip / 无账号时指纹仍要稳定（不能因为 NULL 就永远不相等）
  const nullA = buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'x' })
  const nullB = buildEventPayload({ event: EVENTS.TOKEN_REJECTED, reason: 'y' })
  check('无 ip/账号时指纹依然稳定（脚本场景也能聚合）', nullA.fingerprint === nullB.fingerprint)
}

console.log('== D. 事件白名单与窗口 ==')
{
  check('恰好三个事件类型', EVENT_VALUES.length === 3)
  check('含 auth.login.rejected', EVENT_VALUES.includes('auth.login.rejected'))
  check('含 auth.register.rejected', EVENT_VALUES.includes('auth.register.rejected'))
  check('含 auth.token.rejected', EVENT_VALUES.includes('auth.token.rejected'))
  check('命名统一为 auth.<动作>.rejected', EVENT_VALUES.every((v) => /^auth\.[a-z]+\.rejected$/.test(v)))
  check('聚合窗口是正数且不超过 1 小时', AGGREGATE_WINDOW_MS > 0 && AGGREGATE_WINDOW_MS <= 3600 * 1000)

  // 交叉验证：maskAccount 与 sanitizeIp 是共用工具，这里顺带钉住它们的契约
  check('maskAccount 不会返回带控制字符的结果', !hasControlChar(maskAccount('a\r\nb@c.com')))
  check('sanitizeIp 与 net.isIP 口径一致（不自己写正则）', sanitizeIp('127.0.0.1') === '127.0.0.1' && sanitizeIp('127.0.0.1:80') === null)
  check('sanitizeLogText 仍是单行输出', sanitizeLogText('a\nb') === 'a b')
}

console.log()
if (failures.length) {
  console.log(`共 ${failures.length} 条失败：`)
  for (const f of failures) console.log(' -', f)
  process.exit(1)
}
console.log('全部通过（安全事件纯函数自检）')

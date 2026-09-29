/* eslint-disable no-control-regex -- 本文件的职责就是「匹配并移除控制字符 / 转义序列」，
   不匹配它们就无从移除。这条规则在这里方向是反的，所以整文件豁免。 */
// 操作日志的文本净化规则。
//
// 日志与别的用户输入不同：它会被写进数据库、被运维读到、将来还会导出到文件 /
// SIEM / 终端。也就是说「用户在标题或评论里写了什么」会直接影响日志本身的完整性。
// 这里把四类注入面集中处理，业务代码只调这一处，不要各写各的：
//
//   1. 日志伪造（CRLF 注入）—— 正文里塞 `\r\n[ERROR][auth] admin 登录成功`，
//      下游按行解析的日志系统就会凭空多出一条记录。所有换行一律压成空格。
//   2. 控制字符与终端转义 —— `\x1b[31m` 会改写终端配色甚至擦屏，`\x00` 会截断
//      下游解析器的字符串，`\x7f` 是 DEL。
//   3. Unicode 方向控制 —— `\u202E`（RLO）能让整段文本反向显示，用来伪造视觉内容；
//      零宽字符（`\u200B`）能在肉眼看不见的地方把两个词粘成一个。
//   4. 存储放大 —— 一条日志塞几万字能把表撑爆，所以统一截断，并在结尾显式加 `…`
//      标出「这里被截过」，不做静默丢弃。
//
// 刻意**不做**的事：不剥离 `<` `>`，也不做 HTML 实体转义。这是共创社区，用户真的
// 会在评论里讨论标签写法；把原文改成 `&lt;` 既让审计失真（看不到用户到底写了什么），
// 又会在前端被二次转义成 `&amp;lt;`。这一层的约定是：**日志只做纯文本渲染，禁止 v-html**，
// 转义交给渲染层。
const { stripEmoji } = require('./textSanitize')
const { isIP } = require('node:net')

// ANSI CSI 序列：ESC [ 参数 终止符
const ANSI_RE = /\u001B\[[0-9;?]*[ -/]*[@-~]/g
// 换行家族：CRLF / CR / LF / U+2028 / U+2029
const LINE_BREAK_RE = /[\n\r\u2028\u2029]+/g
// C0 控制字符（保留 \t = \u0009，稍后统一折叠成空格）与 C1 控制字符
const CONTROL_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g
// 双向文本控制与零宽字符、BOM
const INVISIBLE_RE = /[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/g
// 空白家族（含不换行空格、全角空格）折叠成单个半角空格
const WHITESPACE_RE = /[ \t\u00A0\u3000]+/g

const DEFAULT_MAX = 160

// 截断：超长时留出 1 个字符位放省略号，让「被截过」这件事在数据里可见
const truncate = (text, maxLen) => {
  const limit = Math.max(0, Math.floor(maxLen))
  if (text.length <= limit) return text
  if (limit === 0) return ''
  return text.slice(0, limit - 1) + '…'
}

/**
 * 把任意值净化成「可以安全写进日志的一行文本」。
 *
 * @param {*} input 原始值（非字符串会被 String() 化）
 * @param {number} maxLen 长度上限，默认 160
 * @returns {string} 单行、无控制字符、无方向控制、已截断的文本（可能为空串）
 */
const sanitizeLogText = (input, maxLen = DEFAULT_MAX) => {
  if (input === null || input === undefined) return ''
  const raw = typeof input === 'string' ? input : String(input)
  const ordered = raw
    // ANSI 必须先整体摘掉：否则 ESC 会被下面按单字符清掉，留下 `[31m` 这种垃圾
    .replace(ANSI_RE, '')
    .replace(LINE_BREAK_RE, ' ')
    .replace(CONTROL_RE, '')
    .replace(INVISIBLE_RE, '')
  // 复用全站约定：日志内容同样不允许 emoji（与评论 / 标题一致）
  const withoutEmoji = stripEmoji(ordered).replace(WHITESPACE_RE, ' ').trim()
  return truncate(withoutEmoji, maxLen)
}

/**
 * 按**键白名单**抽取结构化附加信息。
 *
 * 关键点：循环的是 `allowedKeys` 而不是传入的对象。所以传入对象里多出来的键
 * （包括 `__proto__` / `constructor` 这类原型污染载荷）天然进不来 —— 不需要
 * 逐个去黑名单匹配。值只接受「有限数字 / 布尔 / 净化后的短字符串 / 短字符串数组」，
 * 嵌套对象一律丢弃（日志里的结构越浅，下游越好解析）。
 *
 * @param {object} detail 原始附加信息
 * @param {string[]} allowedKeys 该动作允许的键
 * @returns {object|null} 全部键都不合法时返回 null（不写空对象）
 */
const sanitizeDetail = (detail, allowedKeys) => {
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return null
  if (!Array.isArray(allowedKeys) || allowedKeys.length === 0) return null

  const out = {}
  for (const key of allowedKeys) {
    if (typeof key !== 'string' || !Object.prototype.hasOwnProperty.call(detail, key)) continue
    const value = detail[key]
    if (value === null || value === undefined) continue

    if (typeof value === 'number') {
      if (Number.isFinite(value)) out[key] = value
    } else if (typeof value === 'boolean') {
      out[key] = value
    } else if (Array.isArray(value)) {
      const list = value
        .filter((item) => typeof item === 'string')
        .slice(0, 8)
        .map((item) => sanitizeLogText(item, 40))
        .filter(Boolean)
      if (list.length) out[key] = list
    } else if (typeof value === 'string') {
      const text = sanitizeLogText(value, 120)
      if (text) out[key] = text
    }
    // 其余类型（嵌套对象 / 函数 / symbol 等）一律丢弃。
    // 不能图省事写成 String(value)：`{a:1}` 会变成字符串 `[object Object]`，
    // 日志里出现一串这个既没信息量、又说明写日志的人漏了字段 —— 宁可缺字段。
  }
  return Object.keys(out).length ? out : null
}

// IP：交给 net.isIP 判定，不要自己写正则 —— IPv6 允许冒号，
// 手写字符集会连 `127.0.0.1:5000` 这种「带端口的串」一起放进来。
const sanitizeIp = (ip) => (typeof ip === 'string' && ip.length <= 45 && isIP(ip) ? ip : null)

// UA 是不可信请求头，只做净化与截断，不做格式校验（合法 UA 本来就五花八门）
const sanitizeUserAgent = (ua) => sanitizeLogText(ua, 255)

module.exports = {
  sanitizeLogText,
  sanitizeDetail,
  sanitizeIp,
  sanitizeUserAgent
}

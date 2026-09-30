// logSanitize.js 单元测试 —— 日志净化的五条约定，每条都对应一类真实注入面：
//   sanitizeLogText：CRLF 伪造 / ANSI 转义 / 控制字符 / 零宽与双向控制 / emoji / 存储放大截断
//   sanitizeDetail：键白名单（原型污染载荷天然进不来）+ 值类型收敛
//   sanitizeIp：交给 net.isIP（手写字符集会放行 127.0.0.1:5000）
//   maskAccount：脱敏但保特征（碰撞是有意取舍，见源码注释）
const { test } = require('node:test')
const assert = require('node:assert')
const {
  sanitizeLogText,
  sanitizeDetail,
  sanitizeIp,
  sanitizeUserAgent,
  maskAccount
} = require('../../src/utils/logSanitize')

// ---- sanitizeLogText ----

test('空值返回空串（不写「undefined」进日志）', () => {
  assert.strictEqual(sanitizeLogText(null), '')
  assert.strictEqual(sanitizeLogText(undefined), '')
})

test('CRLF 家族压成单个空格（按行解析的下游无法凭空多出记录）', () => {
  assert.strictEqual(sanitizeLogText('a\r\nFAKE'), 'a FAKE')
  assert.strictEqual(sanitizeLogText('a\n\n\nb'), 'a b')
  assert.strictEqual(sanitizeLogText('a\u2028b\u2029c'), 'a b c')
})

test('ANSI 序列整体摘除（不是留下 [31m 垃圾）', () => {
  assert.strictEqual(sanitizeLogText('\u001B[31mred\u001B[0m'), 'red')
})

test('C0 控制字符与 DEL 删除', () => {
  assert.strictEqual(sanitizeLogText('a\u0000b\u0007c\u007Fd'), 'abcd')
})

test('零宽与双向控制字符删除（U+202E 不能让文本反向显示）', () => {
  assert.strictEqual(sanitizeLogText('vis\u200Bible'), 'visible')
  assert.strictEqual(sanitizeLogText('a\u202Eb'), 'ab')
  assert.strictEqual(sanitizeLogText('a\uFEFFb'), 'ab')
})

test('emoji 剥除（与全站「仅矢量图标」约定一致）', () => {
  assert.strictEqual(sanitizeLogText('发布🎯成功'), '发布成功')
})

test('空白家族折叠成单个半角空格（含 NBSP 与全角空格）', () => {
  assert.strictEqual(sanitizeLogText('a\t b\u00A0\u3000c'), 'a b c')
})

test('存储放大：超长截断并显式加省略号', () => {
  const out = sanitizeLogText('x'.repeat(200))
  assert.strictEqual(out.length, 160)
  assert.ok(out.endsWith('…'))
  // 恰好等于上限不截断
  assert.strictEqual(sanitizeLogText('y'.repeat(160)), 'y'.repeat(160))
  // 上限 0 → 空串
  assert.strictEqual(sanitizeLogText('abc', 0), '')
})

test('非字符串 String() 化（数字可用，不抛异常）', () => {
  assert.strictEqual(sanitizeLogText(42), '42')
})

// ---- sanitizeDetail ----

test('键白名单：白名单外的键（含原型污染载荷）一律进不来', () => {
  const detail = { ok: 'yes', __proto__: { x: 1 }, constructor: 'evil', extra: 'no' }
  assert.deepStrictEqual(sanitizeDetail(detail, ['ok']), { ok: 'yes' })
})

test('嵌套对象丢弃而非 String() 成 [object Object]', () => {
  assert.strictEqual(sanitizeDetail({ a: { deep: true } }, ['a']), null)
})

test('值类型收敛：有限数字 / 布尔保留，NaN 与 Infinity 丢弃', () => {
  assert.deepStrictEqual(sanitizeDetail({ n: 3, ok: true }, ['n', 'ok']), { n: 3, ok: true })
  assert.strictEqual(sanitizeDetail({ n: NaN }, ['n']), null)
  assert.strictEqual(sanitizeDetail({ n: Infinity }, ['n']), null)
})

test('字符串数组：净化、截 8 个、非字符串过滤', () => {
  const out = sanitizeDetail({ tags: ['a', 42, 'b'] }, ['tags'])
  assert.deepStrictEqual(out, { tags: ['a', 'b'] })
  const many = sanitizeDetail({ tags: ['1', '2', '3', '4', '5', '6', '7', '8', '9'] }, ['tags'])
  assert.strictEqual(many.tags.length, 8)
})

test('字符串值净化并截到 120', () => {
  const out = sanitizeDetail({ s: 'x'.repeat(200) }, ['s'])
  assert.strictEqual(out.s.length, 120)
  assert.ok(out.s.endsWith('…'))
})

test('非法输入：非对象 / 数组 / 空白名单 → null；全部键不合法 → null', () => {
  assert.strictEqual(sanitizeDetail(null, ['a']), null)
  assert.strictEqual(sanitizeDetail([1, 2], ['a']), null)
  assert.strictEqual(sanitizeDetail({ a: 'x' }, []), null)
  assert.strictEqual(sanitizeDetail({ a: { deep: 1 } }, ['a']), null)
})

// ---- sanitizeIp ----

test('合法 IP 原样返回', () => {
  assert.strictEqual(sanitizeIp('127.0.0.1'), '127.0.0.1')
  assert.strictEqual(sanitizeIp('::1'), '::1')
})

test('带端口的串不放行（手写字符集的真实漏网，net.isIP 实证）', () => {
  assert.strictEqual(sanitizeIp('127.0.0.1:5000'), null)
})

test('非 IP / 非字符串 / 超长 → null', () => {
  assert.strictEqual(sanitizeIp('not-an-ip'), null)
  assert.strictEqual(sanitizeIp(123), null)
  assert.strictEqual(sanitizeIp('a'.repeat(46)), null)
})

// ---- sanitizeUserAgent ----

test('UA 净化 + 255 截断', () => {
  const out = sanitizeUserAgent('Mozilla/5.0 \r\nFAKE ' + 'x'.repeat(300))
  assert.strictEqual(out.length, 255)
  assert.ok(!out.includes('\r'))
  assert.ok(!out.includes('\n'))
})

// ---- maskAccount ----

test('邮箱脱敏：保首字符 + 域名首字符 + 顶级域', () => {
  assert.strictEqual(maskAccount('zhang@x.com'), 'z***@x***.com')
  assert.strictEqual(maskAccount('secA@example.com'), 's***@e***.com')
})

test('非邮箱形态：只留首字符', () => {
  assert.strictEqual(maskAccount('abc'), 'a***')
  assert.strictEqual(maskAccount('a'), 'a')
})

test('净化先行：注入串不能借脱敏路径绕进日志', () => {
  // CRLF 先被压成空格，再按非邮箱脱敏
  assert.strictEqual(maskAccount('a\r\nFAKE'), 'a***')
  // 全 emoji 净化后为空 → null
  assert.strictEqual(maskAccount('🎯'), null)
  assert.strictEqual(maskAccount('   '), null)
})

test('畸形邮箱：@ 在开头或结尾按非邮箱处理', () => {
  assert.strictEqual(maskAccount('@x.com'), '@***')
  assert.strictEqual(maskAccount('a@'), 'a***')
})

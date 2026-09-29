/**
 * 日志净化规则的纯函数自检。
 *
 * 为什么单独跑一层：净化是「一堆正则 + 截断」的纯逻辑，用 HTTP 端到端去测它既慢又
 * 绕（想测 ANSI 转义就得往评论里塞 ESC）。这里直接喂载荷、直接断言输出，
 * 失败信息也能精确到「哪条规则漏了」。
 *
 * 端到端那一层（scripts/verify_activity_logs.py）负责验证「净化后的文本确实落库了」。
 *
 * 用法（在 backend/ 下）：node scripts/check-log-sanitize.js   —— 退出码 0 表示全绿
 */
const {
  sanitizeLogText,
  sanitizeDetail,
  sanitizeIp,
  sanitizeUserAgent
} = require('../src/utils/logSanitize')

const failures = []
const check = (label, cond) => {
  console.log((cond ? '  OK  ' : ' FAIL ') + label)
  if (!cond) failures.push(label)
}

// 断言结果里不含任何 C0 控制字符 / DEL / C1
// eslint-disable-next-line no-control-regex -- 要断言「没有控制字符」就必须先匹配它们
const hasControlChar = (text) => /[\u0000-\u001F\u007F-\u009F]/.test(text)
// 断言结果里不含任何方向控制或零宽字符
const hasInvisible = (text) => /[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/.test(text)

console.log('== A. 日志伪造（CRLF 注入）==')
{
  const payload = '正常标题\r\n[ERROR][auth] admin 登录成功'
  const out = sanitizeLogText(payload)
  check('CRLF 被压平：输出不含 \\n', !out.includes('\n'))
  check('CRLF 被压平：输出不含 \\r', !out.includes('\r'))
  check('CRLF 注入后仍是一行', out.split('\n').length === 1)
  check('CRLF 处变成空格而不是黏连', out.includes('正常标题 [ERROR]'))

  const lf = sanitizeLogText('a\nb')
  check('单个 LF 被替换成空格', lf === 'a b')

  const cr = sanitizeLogText('a\rb')
  check('单个 CR 被替换成空格', cr === 'a b')

  const lsep = sanitizeLogText('a\u2028b\u2029c')
  check('U+2028 / U+2029 同样被压平', lsep === 'a b c')
}

console.log('== B. 控制字符与终端转义 ==')
{
  check('ANSI 彩色序列被整体摘除', sanitizeLogText('\u001B[31m红\u001B[0m字') === '红字')
  check('ANSI 清屏序列被摘除', sanitizeLogText('前\u001B[2J后') === '前后')
  check('NUL 被移除', sanitizeLogText('a\u0000b') === 'ab')
  check('DEL(0x7F) 被移除', sanitizeLogText('a\u007Fb') === 'ab')
  check('C1 控制字符(0x9B) 被移除', sanitizeLogText('a\u009Bb') === 'ab')
  check('BEL(0x07) 被移除', sanitizeLogText('a\u0007b') === 'ab')
  check('输出整体不含任何控制字符', !hasControlChar(sanitizeLogText('a\u0000\u001B[1m\u007F\u009Bb')))
}

console.log('== C. Unicode 方向控制与零宽字符 ==')
{
  check('RLO(U+202E) 被移除', sanitizeLogText('abc\u202Edef') === 'abcdef')
  check('零宽空格(U+200B) 被移除', sanitizeLogText('a\u200Bb') === 'ab')
  check('零宽连接符(U+200D) 被移除', sanitizeLogText('a\u200Db') === 'ab')
  check('BOM(U+FEFF) 被移除', sanitizeLogText('\uFEFFa') === 'a')
  check('输出整体不含任何方向控制字符', !hasInvisible(sanitizeLogText('a\u202E\u200B\u2066b')))
}

console.log('== D. 空白归一 ==')
{
  check('制表符折叠成单个空格', sanitizeLogText('a\t\tb') === 'a b')
  check('连续空格折叠', sanitizeLogText('a     b') === 'a b')
  check('首尾空白被 trim', sanitizeLogText('   a  ') === 'a')
  check('不换行空格(U+00A0) 也折叠', sanitizeLogText('a\u00A0b') === 'a b')
}

console.log('== E. 存储放大（截断）==')
{
  const long = 'x'.repeat(300)
  const out = sanitizeLogText(long, 100)
  check('超长被截断到上限', out.length === 100)
  check('截断处有可见省略号（不静默丢内容）', out.endsWith('…'))
  check('刚好等于上限时不截断', sanitizeLogText('x'.repeat(100), 100) === 'x'.repeat(100))
  check('默认上限 160', sanitizeLogText('x'.repeat(5000)).length === 160)
  check('上限为 0 时返回空串而不是崩', sanitizeLogText('abc', 0) === '')
}

console.log('== F. 类型兜底 ==')
{
  check('null -> 空串', sanitizeLogText(null) === '')
  check('undefined -> 空串', sanitizeLogText(undefined) === '')
  check('数字被字符串化', sanitizeLogText(42) === '42')
  check('对象不会变成 [object Object] 之外的怪东西', sanitizeLogText({ a: 1 }) === '[object Object]')
  check('emoji 按全站约定被剥离', sanitizeLogText('你好🌱世界') === '你好世界')
}

console.log('== G. detail 键白名单 ==')
{
  const parsed = JSON.parse('{"title":"T","__proto__":"polluted","evil":"x"}')
  const out = sanitizeDetail(parsed, ['title'])
  check('白名单外的键被丢弃', out && out.evil === undefined)
  check('原型污染键进不来', out && !Object.prototype.hasOwnProperty.call(out, '__proto__'))
  check('白名单内的键保留', out && out.title === 'T')
  check('JSON 序列化后不含 __proto__', !JSON.stringify(out).includes('__proto__'))
  check('全局原型没有被污染', ({}).polluted === undefined)

  check('全部键非法时返回 null 而不是空对象', sanitizeDetail({ evil: 1 }, ['title']) === null)
  check('非对象返回 null', sanitizeDetail('字符串', ['title']) === null)
  check('数组返回 null', sanitizeDetail([1, 2], ['title']) === null)
  check('空白名单返回 null', sanitizeDetail({ title: 'T' }, []) === null)

  const mixed = sanitizeDetail(
    { n: 3, b: true, s: '文字', bad: Number.NaN, obj: { a: 1 }, nul: null },
    ['n', 'b', 's', 'bad', 'obj', 'nul']
  )
  check('有限数字保留', mixed.n === 3)
  check('布尔值保留', mixed.b === true)
  check('字符串保留', mixed.s === '文字')
  check('NaN 被丢弃', !('bad' in mixed))
  check('嵌套对象被丢弃', !('obj' in mixed))
  check('且没有退化成 [object Object]', !JSON.stringify(mixed).includes('[object Object]'))
  check('null 值被丢弃', !('nul' in mixed))

  const arr = sanitizeDetail({ tags: ['a', 'b', { x: 1 }, null, 'c'] }, ['tags'])
  check('字符串数组保留（非字符串项被过滤）', JSON.stringify(arr) === '{"tags":["a","b","c"]}')
  const capped = sanitizeDetail({ tags: Array.from({ length: 20 }, (_, i) => 'T' + i) }, ['tags'])
  check('数组长度被截到 8', capped.tags.length === 8)

  const dirty = sanitizeDetail({ title: 'a\r\nb' }, ['title'])
  check('detail 里的值同样被净化', dirty.title === 'a b')
}

console.log('== H. IP / UA ==')
{
  check('IPv4 保留', sanitizeIp('127.0.0.1') === '127.0.0.1')
  check('IPv6 回环保留', sanitizeIp('::1') === '::1')
  check('带端口的串被拒', sanitizeIp('127.0.0.1:5000') === null)
  check('SQL 注入串被拒', sanitizeIp("127.0.0.1' OR 1=1 --") === null)
  check('非字符串被拒', sanitizeIp(12345) === null)

  const ua = sanitizeUserAgent('Mozilla/5.0\r\nX-Injected: 1')
  check('UA 里的 CRLF 被压平', !ua.includes('\r') && !ua.includes('\n'))
  check('UA 超长被截断到 255', sanitizeUserAgent('u'.repeat(600)).length === 255)
}

console.log()
console.log(`assert failed: ${failures.length}`)
failures.forEach((f) => console.log(' - ' + f))
process.exit(failures.length ? 1 : 0)

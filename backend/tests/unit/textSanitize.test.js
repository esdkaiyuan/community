// textSanitize.js 单元测试 —— 用户文本净化的三层约定：
//   stripEmoji（全站禁 emoji）/ hasEmoji（提示「已自动移除」用）/ stripControlChars（CRLF 伪造与隐形字符）
// 边界矩阵照「修过的真实 bug」铺：emoji 空白收敛、多行字段保留 \n、单行字段连 \t 一起清。
const { test } = require('node:test')
const assert = require('node:assert')
const { stripEmoji, hasEmoji, stripControlChars } = require('../../src/utils/textSanitize')

// ---- stripEmoji ----

test('emoji 被移除、中文原样保留', () => {
  assert.strictEqual(stripEmoji('开源共创🎯平台'), '开源共创平台')
  assert.strictEqual(stripEmoji('👍👍好'), '好')
})

test('ZJW 字符（零宽连接符）一并移除', () => {
  assert.strictEqual(stripEmoji('a\u200Db'), 'ab')
  assert.strictEqual(stripEmoji('1\u20E3'), '1')
})

test('空白收敛：行尾空白、3+ 连续换行压成最多 2 个、首尾空白剪掉', () => {
  assert.strictEqual(stripEmoji('  a  \n\n\n\nb  '), 'a\n\nb')
  assert.strictEqual(stripEmoji('a\t\nb'), 'a\nb')
})

test('非字符串输入原样返回（不抛异常）', () => {
  assert.strictEqual(stripEmoji(null), null)
  assert.strictEqual(stripEmoji(undefined), undefined)
  assert.strictEqual(stripEmoji(123), 123)
})

test('ASCII 与常见标点不受影响', () => {
  assert.strictEqual(stripEmoji('C++/Rust & Go! 你好，世界。'), 'C++/Rust & Go! 你好，世界。')
})

// ---- hasEmoji ----

test('hasEmoji 与 stripEmoji 的判定一致', () => {
  assert.strictEqual(hasEmoji('🎯'), true)
  assert.strictEqual(hasEmoji('纯中文'), false)
  assert.strictEqual(hasEmoji('a\u200Db'), true) // 零宽连接符也算
  assert.strictEqual(hasEmoji(42), false) // 非字符串恒 false
})

// ---- stripControlChars ----

test('CRLF / DEL / ESC 在单行模式下全部删除（日志伪造的根）', () => {
  assert.strictEqual(stripControlChars('a\r\nFAKE'), 'aFAKE')
  assert.strictEqual(stripControlChars('a\x1b[31mred'), 'a[31mred'.replace('[', '[')) // ESC 摘掉，其余可见字符保留
  assert.strictEqual(stripControlChars('bad\x00\x7f'), 'bad')
})

test('零宽与双向控制字符（U+200B / U+202E）被移除', () => {
  assert.strictEqual(stripControlChars('vis\u200Bible'), 'visible')
  assert.strictEqual(stripControlChars('a\u202Eb'), 'ab')
})

test('keepNewlines: 多行字段保留 \\n，但 \\r \\t 仍清', () => {
  const src = '第一段\r\n第二段\t第三段\n\n第四段'
  assert.strictEqual(stripControlChars(src, { keepNewlines: true }), '第一段\n第二段第三段\n\n第四段')
})

test('单行模式连 \\n \\t 一起清（用户名等单行字段的契约）', () => {
  assert.strictEqual(stripControlChars('nick\tname\nx'), 'nicknamex')
})

test('非字符串输入原样返回', () => {
  assert.strictEqual(stripControlChars(undefined), undefined)
  assert.strictEqual(stripControlChars(7), 7)
})

// pagination.js 单元测试 —— clampInt 是「用户可控数字进 SQL LIMIT/OFFSET」的唯一收口。
//
// 修过的真实 bug 就是这里的边界：`?page=99999999999999999999` 让
// (page-1)*limit 越过 MAX_SAFE_INTEGER，序列化成科学计数法拼进 SQL → 500。
// 这里把边界矩阵钉死，防止将来任何一处「顺手重写」回退。
const { test } = require('node:test')
const assert = require('node:assert')
const { clampInt, MAX_PAGE } = require('../../src/utils/pagination')

test('合法值原样通过（字符串数字也接受）', () => {
  assert.strictEqual(clampInt('3', { fallback: 1 }), 3)
  assert.strictEqual(clampInt(3, { fallback: 1 }), 3)
  assert.strictEqual(clampInt('05', { fallback: 1 }), 5)
})

test('非数字 / 0 / 空 / NaN 退回 fallback', () => {
  assert.strictEqual(clampInt('abc', { fallback: 1 }), 1)
  assert.strictEqual(clampInt('', { fallback: 1 }), 1)
  assert.strictEqual(clampInt(undefined, { fallback: 1 }), 1)
  assert.strictEqual(clampInt(null, { fallback: 1 }), 1)
  // parseInt('0') === 0 是 falsy → fallback（与旧写法 `|| fallback` 语义一致）
  assert.strictEqual(clampInt('0', { fallback: 1 }), 1)
  assert.strictEqual(clampInt(0, { fallback: 1 }), 1)
})

test('负数夹到 min', () => {
  assert.strictEqual(clampInt('-5', { fallback: 1 }), 1)
  assert.strictEqual(clampInt(-5, { fallback: 1 }), 1)
  // 自定义 min 下限
  assert.strictEqual(clampInt('-3', { min: 2, max: 10, fallback: 2 }), 2)
})

test('超界夹到 max（含科学计数法与超大整数串——真实 bug 的指纹）', () => {
  assert.strictEqual(clampInt('99999999999999999999', { fallback: 1 }), 50)
  assert.strictEqual(clampInt('1e20', { fallback: 1, max: 100 }), 1) // parseInt('1e20')===1
  // 数字型的科学计数法会被 parseInt 吃成首位数字（1e21 → '1e+21' → 1）：
  // 钉住这个真实语义，防止有人「顺手修好」它却改变了调用方的既有行为
  assert.strictEqual(clampInt(1e21, { fallback: 1 }), 1)
  // 自定义 max
  assert.strictEqual(clampInt('999', { min: 1, max: 100, fallback: 1 }), 100)
})

test('恰好等于边界时不被改动', () => {
  assert.strictEqual(clampInt('1', { fallback: 1 }), 1)
  assert.strictEqual(clampInt('50', { fallback: 1 }), 50)
  assert.strictEqual(clampInt('100000', { max: MAX_PAGE, fallback: 1 }), 100000)
  assert.strictEqual(clampInt('100001', { max: MAX_PAGE, fallback: 1 }), MAX_PAGE)
})

test('fallback 缺省时返回 undefined（调用方自行兜底的契约）', () => {
  assert.strictEqual(clampInt('abc'), undefined)
})

test('MAX_PAGE 常量语义：翻到尾页仍在安全整数内', () => {
  assert.ok(Number.isSafeInteger((MAX_PAGE - 1) * 50))
})

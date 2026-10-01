const test = require('node:test')
const assert = require('node:assert')

const { bumpCounter } = require('../../src/utils/counter')

// 假模型：只记录 update 收到的载荷，并让 findByPk 返回固定值
const fakeModel = (value) => {
  const state = { value, updates: [] }
  return {
    __state: state,
    update: async (payload, opts) => {
      state.updates.push({ payload, opts })
    },
    findByPk: async (_id, _opts) => ({ get: () => state.value })
  }
}

// Sequelize 的 literal 把 SQL 片段存在 .val 上
const sqlOf = (literal) => (literal && literal.val !== undefined ? literal.val : literal)

test('bumpCounter: 正增量生成 col + n', async () => {
  const m = fakeModel(3)
  await bumpCounter(m, 1, 'like_count', 1)
  assert.strictEqual(m.__state.updates.length, 1)
  assert.strictEqual(sqlOf(m.__state.updates[0].payload.like_count), 'like_count + 1')
})

test('bumpCounter: 负增量用 GREATEST 兜住下限', async () => {
  const m = fakeModel(5)
  await bumpCounter(m, 1, 'like_count', -1)
  assert.strictEqual(sqlOf(m.__state.updates[0].payload.like_count), 'GREATEST(like_count - 1, 0)')
})

test('bumpCounter: 多档自减用绝对值', async () => {
  const m = fakeModel(9)
  await bumpCounter(m, 1, 'comment_count', -5)
  assert.strictEqual(sqlOf(m.__state.updates[0].payload.comment_count), 'GREATEST(comment_count - 5, 0)')
})

test('bumpCounter: delta 为 0 时不写库', async () => {
  const m = fakeModel(7)
  const got = await bumpCounter(m, 1, 'like_count', 0)
  assert.strictEqual(m.__state.updates.length, 0)
  assert.strictEqual(got, 7)
})

test('bumpCounter: 返回值来自库里的读数而不是内存推算', async () => {
  const m = fakeModel(42)
  const got = await bumpCounter(m, 12, 'participant_count', 1)
  assert.strictEqual(got, 42)
  assert.deepStrictEqual(m.__state.updates[0].opts, { where: { id: 12 } })
})

test('bumpCounter: 非法 delta 不产生 NaN 表达式', async () => {
  const m = fakeModel(1)
  await bumpCounter(m, 1, 'like_count', NaN)
  // NaN 会被当成 0 处理：不写库，只读回当前值
  assert.strictEqual(m.__state.updates.length, 0)
})

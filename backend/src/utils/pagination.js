// 用户可控的整数参数（页码 / 每页条数 / 取数上限）统一从这里过。
//
// 为什么必须收口到一处：这些数字会直接进 SQL 的 LIMIT / OFFSET。
// `?page=99999999999999999999` 会让 `(page - 1) * limit` 超出
// Number.MAX_SAFE_INTEGER，被序列化成 "1.2e+22" 这种科学计数法拼进 SQL，
// 数据库报语法错 → 用户收到 500（修复前实测正是这个表现）。
// 上界在**这里**收口，调用方只管给默认值 —— 否则每个列表接口各写一遍，
// 迟早有人漏掉 page 的上界（本轮 6 个 service 里就漏了 8 处）。
//
// 语义与旧写法 `Math.min(max, Math.max(1, parseInt(v, 10) || fallback))`
// 完全一致（保持既有行为，不引入新的边界变化）：
//   非数字 / 0 / 空 → 退回 fallback
//   负数 / 超界      → 夹到 [min, max]
const MAX_PAGE = 100000 // (MAX_PAGE - 1) * 50 仍在安全整数内，足够翻到任何真实数据的尾页

const clampInt = (value, { min = 1, max = 50, fallback } = {}) => {
  const n = parseInt(value, 10)
  return n ? Math.min(max, Math.max(min, n)) : fallback
}

module.exports = { clampInt, MAX_PAGE }

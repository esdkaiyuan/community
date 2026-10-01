const sequelize = require('../config/database')

/**
 * 计数列的原子自增 / 自减。
 *
 * 为什么必须有它：全站所有「点赞数 / 评论数 / 参与数」过去都写成
 * `model.count += 1; await model.save()`。那是**读改写** —— 两个并发请求读到
 * 同一个旧值、各自写回同一个结果，实际只加了 1。实测 8 个并发点赞只让
 * like_count +1（丢 7 次），而且整个过程不报错、不报警，页面上的数字长期被低估。
 *
 * 正确做法是把运算交给数据库：UPDATE ... SET col = col + 1 由行锁保证串行，
 * 不丢更新。自减用 GREATEST(col - n, 0) 兜住下限，避免并发下减成负数。
 *
 * @param {Model} Model Sequelize 模型
 * @param {number|string} id 主键
 * @param {string} column 计数列名（内部常量，不接受用户输入）
 * @param {number} delta 增量，正数加、负数减
 * @returns {Promise<number>} 更新后的值（从库里读回，不用内存里的推算值）
 */
const bumpCounter = async (Model, id, column, delta = 1) => {
  const n = Number(delta) || 0

  if (n === 0) {
    const row = await Model.findByPk(id, { attributes: [column] })
    return row ? Number(row.get(column)) || 0 : 0
  }

  // 加：col + n；减：GREATEST(col - n, 0) —— 下限兜底，减到 0 就停住
  const expr = n > 0 ? `${column} + ${n}` : `GREATEST(${column} - ${Math.abs(n)}, 0)`
  await Model.update({ [column]: sequelize.literal(expr) }, { where: { id } })

  const row = await Model.findByPk(id, { attributes: [column] })
  return row ? Number(row.get(column)) || 0 : 0
}

module.exports = { bumpCounter }

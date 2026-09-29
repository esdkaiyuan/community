/**
 * 按留存期清理操作日志。
 *
 * 为什么需要它：activity_logs 只写不删，是唯一会无限增长的业务表。
 * 一条日志几十字节到几百字节，日常量级很小，但「永不清理」等于给运维埋一颗
 * 定时炸弹 —— 半年后没人敢动这张表，也没人知道它为什么这么大。
 *
 * 留存期默认 365 天（审计通常要求覆盖一个完整年度的对账周期），可通过
 * --days=N 覆盖。**默认只报告不删除**，要真删必须显式加 --apply。
 *
 * 用法（在 backend/ 下）：
 *   node scripts/prune-activity-logs.js                 # 干跑，只报告将要删除的条数
 *   node scripts/prune-activity-logs.js --apply         # 真删
 *   node scripts/prune-activity-logs.js --days=180      # 留存 180 天
 */
const path = require('node:path')

// 显式指定 .env 位置：否则从仓库根目录跑时会读到错误的配置（dotenv 默认按 cwd 找）
require('dotenv').config({ path: path.resolve(__dirname, '../.env') })

const { Op } = require('sequelize')
const { ActivityLog, sequelize } = require('../src/models')

const DEFAULT_DAYS = 365

const args = process.argv.slice(2)
const apply = args.includes('--apply')
const daysArg = args.find((a) => a.startsWith('--days='))
const days = daysArg ? Number(daysArg.split('=')[1]) : DEFAULT_DAYS

if (args.includes('--help') || args.includes('-h')) {
  console.log('用法: node scripts/prune-activity-logs.js [--apply] [--days=365]')
  process.exit(0)
}
if (!Number.isFinite(days) || days < 1) {
  console.error('--days 必须是大于等于 1 的数字（单位：天）')
  process.exit(2)
}

const fmt = (d) => d.toISOString().slice(0, 19).replace('T', ' ')

async function main() {
  const cutoff = new Date(Date.now() - days * 24 * 3600 * 1000)

  const total = await ActivityLog.count()
  const expired = await ActivityLog.count({ where: { created_at: { [Op.lt]: cutoff } } })

  console.log(`操作日志留存期: ${days} 天，截止时间: ${fmt(cutoff)} UTC`)
  console.log(`总计 ${total} 条 | 超出留存期 ${expired} 条`)

  if (!expired) {
    console.log('\n没有超出留存期的日志。')
    return
  }

  // 按动作分布报一下，避免操作者对着一个数字不知道删的是什么
  const rows = await ActivityLog.findAll({
    attributes: ['action', [sequelize.fn('COUNT', sequelize.col('id')), 'n']],
    where: { created_at: { [Op.lt]: cutoff } },
    group: ['action'],
    raw: true
  })
  console.log('\n将要删除的日志按动作分布：')
  for (const row of rows) {
    console.log(`  - ${row.action}: ${row.n}`)
  }

  if (!apply) {
    console.log('\n当前是干跑模式，未删除任何记录。加 --apply 才会真的删除。')
    return
  }

  const removed = await ActivityLog.destroy({ where: { created_at: { [Op.lt]: cutoff } } })
  console.log(`\n已删除 ${removed} 条日志。`)
}

main()
  .then(() => sequelize.close())
  .catch(async (err) => {
    console.error('清理失败:', err)
    await sequelize.close().catch(() => {})
    process.exit(1)
  })

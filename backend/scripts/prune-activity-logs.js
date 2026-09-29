/**
 * 按留存期清理「日志类」表。
 *
 * 为什么需要它：activity_logs 与 security_events 都是只写不删的表。一条记录几十字节到
 * 几百字节，日常量级很小，但「永不清理」等于给运维埋一颗定时炸弹 —— 半年后没人敢动
 * 这两张表，也没人知道它们为什么这么大。
 *
 * 两张表放在同一个入口，是因为它们的留存策略本来就是同一个（审计通常要求覆盖一个
 * 完整年度的对账周期）。分成两个脚本的话，将来改留存期一定会漏掉其中一个。
 *
 * 留存期默认 365 天，可通过 --days=N 覆盖。**默认只报告不删除**，要真删必须显式加 --apply。
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
const { ActivityLog, SecurityEvent, sequelize } = require('../src/models')

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

// 报告 + 返回超期条数。干跑与真删共用这一段，避免两条路径各算一遍算岔。
async function reportActivityLogs(cutoff) {
  const total = await ActivityLog.count()
  const expired = await ActivityLog.count({ where: { created_at: { [Op.lt]: cutoff } } })
  console.log(`操作日志留存期: ${days} 天，截止时间: ${fmt(cutoff)} UTC`)
  console.log(`总计 ${total} 条 | 超出留存期 ${expired} 条`)

  if (expired) {
    // 按动作分布报一下，避免操作者对着一个数字不知道删的是什么
    const rows = await ActivityLog.findAll({
      attributes: ['action', [sequelize.fn('COUNT', sequelize.col('id')), 'n']],
      where: { created_at: { [Op.lt]: cutoff } },
      group: ['action'],
      raw: true
    })
    console.log('将要删除的操作日志按动作分布：')
    for (const row of rows) {
      console.log(`  - ${row.action}: ${row.n}`)
    }
  }
  return expired
}

async function reportSecurityEvents(cutoff) {
  const total = await SecurityEvent.count()
  const expired = await SecurityEvent.count({ where: { created_at: { [Op.lt]: cutoff } } })
  console.log(`\n安全事件留存期: ${days} 天`)
  console.log(`总计 ${total} 条 | 超出留存期 ${expired} 条`)

  if (expired) {
    const rows = await SecurityEvent.findAll({
      attributes: [
        'event',
        [sequelize.fn('COUNT', sequelize.col('id')), 'n'],
        [sequelize.fn('SUM', sequelize.col('occurrences')), 'occ']
      ],
      where: { created_at: { [Op.lt]: cutoff } },
      group: ['event'],
      raw: true
    })
    console.log('将要删除的安全事件按类型分布（occ = 其中聚合了多少次尝试）：')
    for (const row of rows) {
      console.log(`  - ${row.event}: ${row.n} 条 / ${row.occ} 次`)
    }
  }
  return expired
}

async function main() {
  const cutoff = new Date(Date.now() - days * 24 * 3600 * 1000)

  const expiredLogs = await reportActivityLogs(cutoff)
  const expiredEvents = await reportSecurityEvents(cutoff)

  if (!expiredLogs && !expiredEvents) {
    console.log('\n两张表都没有超出留存期的记录。')
    return
  }

  if (!apply) {
    console.log('\n当前是干跑模式，未删除任何记录。加 --apply 才会真的删除。')
    return
  }

  const removedLogs = await ActivityLog.destroy({ where: { created_at: { [Op.lt]: cutoff } } })
  const removedEvents = await SecurityEvent.destroy({ where: { created_at: { [Op.lt]: cutoff } } })
  console.log(`\n已删除操作日志 ${removedLogs} 条、安全事件 ${removedEvents} 条。`)
}

main()
  .then(() => sequelize.close())
  .catch(async (err) => {
    console.error('清理失败:', err)
    await sequelize.close().catch(() => {})
    process.exit(1)
  })

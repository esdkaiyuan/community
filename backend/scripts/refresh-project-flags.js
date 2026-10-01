/**
 * 刷新项目的「编辑推荐」标记（projects.is_recommend）。
 *
 * 为什么需要它：前端首页的「编辑推荐」筛选把这个标记位翻译成
 * `WHERE is_recommend = 1`，但**全仓没有任何代码写过它** —— 线上实测
 * is_recommend=1 与 is_hot=1 都是 0 条（共 18 个项目）。于是这个入口
 * 长得能用，点下去永远得到空列表。标记位要么有写入路径，要么就别用，
 * 不能悬在半空。
 *
 * 打标口径（可解释、可复现，不需要人工介入）：
 *   互动分 = 点赞 ×1 + 评论 ×2 + 参与 ×3
 * 权重与列表页 sort=trending 的趋势分保持同一套（评论比点赞重、参与最重），
 * 全站一个口径，避免「精选」和「本周热门」给出互相矛盾的答案。
 *
 * 取互动分最高的前 N 个（默认 12）打标，集合外的清零 —— 标记位只反映
 * 「当前」的判断，不会因为历史打过标就永久占位。
 *
 * 冷启动兜底：项目总数不足 N 时全部打标。只要库里有项目，精选就永不为空，
 * 从根上杜绝「入口在、结果永远空」的假功能。
 *
 * 默认只报告不写库。要真写必须显式加 --apply（与 prune-uploads.js 同一契约）。
 *
 * 用法（在 backend/ 下）：
 *   node scripts/refresh-project-flags.js                 # 干跑，只列预览
 *   node scripts/refresh-project-flags.js --apply         # 真写库
 *   node scripts/refresh-project-flags.js --top=20        # 调整精选数量
 *
 * 建议挂 PM2 定时（每天一次，见 deploy 文档）：
 *   cron_restart: "0 4 * * *"，脚本参数 "--apply"
 */
const path = require('node:path')

// 显式指定 .env 位置：否则从仓库根目录跑时会读到错误的配置（dotenv 默认按 cwd 找）
require('dotenv').config({ path: path.resolve(__dirname, '../.env') })

const { sequelize } = require('../src/models')

const DEFAULT_TOP = 12
const MAX_TOP = 100

// 互动分：与 project.service.js 的 TREND_SCORE_SQL 同一套权重
const SCORE_SQL = '(like_count * 1 + comment_count * 2 + participant_count * 3)'

function parseArgs(argv) {
  const apply = argv.includes('--apply')
  let top = DEFAULT_TOP
  for (const arg of argv) {
    const m = /^--top=(\d+)$/.exec(arg)
    if (m) top = Math.min(MAX_TOP, Math.max(1, parseInt(m[1], 10)))
  }
  // 只认已知开关，拼错的参数直接报错，避免「以为加了 --apply 其实没写库」
  for (const arg of argv) {
    if (arg === '--apply') continue
    if (/^--top=\d+$/.test(arg)) continue
    console.log(`用法: node scripts/refresh-project-flags.js [--apply] [--top=${DEFAULT_TOP}]`)
    console.log(`未知参数: ${arg}`)
    process.exit(2)
  }
  return { apply, top }
}

async function main() {
  const { apply, top } = parseArgs(process.argv.slice(2))

  const [rows] = await sequelize.query(
    `SELECT id, title, ${SCORE_SQL} AS score
       FROM projects
      WHERE deleted_at IS NULL
      ORDER BY score DESC, created_at DESC
      LIMIT ${top}`
  )

  const picked = rows.map((r) => Number(r.id))
  console.log(`候选项目（互动分前 ${top}）：`)
  for (const r of rows) {
    console.log(`  #${r.id}  分数 ${r.score}  ${r.title}`)
  }
  if (!picked.length) {
    console.log('\n库里没有未删除的项目，本次不打标。')
    return
  }

  const idList = picked.join(',')
  const [current] = await sequelize.query(
    'SELECT id FROM projects WHERE is_recommend = 1 AND deleted_at IS NULL'
  )
  const currentIds = new Set(current.map((r) => Number(r.id)))
  const toClear = [...currentIds].filter((id) => !picked.includes(id))

  console.log(`\n将标记 ${picked.length} 个，取消 ${toClear.length} 个。`)

  if (!apply) {
    console.log('\n当前是干跑模式，未写入任何数据。加 --apply 才会真的打标。')
    return
  }

  await sequelize.query(`UPDATE projects SET is_recommend = 1 WHERE id IN (${idList})`)
  if (toClear.length) {
    await sequelize.query(
      `UPDATE projects SET is_recommend = 0 WHERE id IN (${toClear.join(',')})`
    )
  }

  console.log(`已标记 ${picked.length} 个，取消 ${toClear.length} 个。`)
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('刷新精选标记失败：', err && err.message ? err.message : err)
    process.exit(1)
  })

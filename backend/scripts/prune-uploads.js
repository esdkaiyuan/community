/**
 * 清扫上传目录里的孤儿封面文件。
 *
 * 为什么需要它：编辑换封面、清空封面这两种情况已经由服务层实时回收（见
 * src/services/cover.service.js）。但还有一种漏不掉的路径 —— **用户选了图、
 * 图已经落盘了，然后没提交就关掉页面**。服务端那一刻还不知道这张图属于谁，
 * 无从回收。这类文件只能靠事后对账扫出来。
 *
 * 判定「孤儿」的口径很保守，三条同时满足才删：
 *   1. 文件在 backend/uploads/projects/ 下，且文件名符合服务端生成规则；
 *   2. 全表（含软删除行）没有任何项目的 cover_image 指向它；
 *   3. 文件修改时间已经超过宽限期（默认 24 小时）。
 * 第 3 条是为了避开竞态：正在填表单的人，他的图还没被任何项目引用，
 * 但它不是垃圾。
 *
 * 默认只报告不删除。要真删必须显式加 --apply。
 *
 * 用法（在 backend/ 下）：
 *   node scripts/prune-uploads.js                       # 干跑，只列候选
 *   node scripts/prune-uploads.js --apply               # 真删
 *   node scripts/prune-uploads.js --min-age-hours=1     # 把宽限期调成 1 小时
 */
const fs = require('node:fs')
const path = require('node:path')

// 显式指定 .env 位置：否则从仓库根目录跑时会读到错误的配置（dotenv 默认按 cwd 找）
require('dotenv').config({ path: path.resolve(__dirname, '../.env') })

const { Project, sequelize } = require('../src/models')
const { COVER_DIR, COVER_URL_PREFIX, isManagedCover } = require('../src/utils/coverFile')

const args = process.argv.slice(2)
const apply = args.includes('--apply')
const ageArg = args.find((a) => a.startsWith('--min-age-hours='))
const minAgeHours = ageArg ? Number(ageArg.split('=')[1]) : 24

if (args.includes('--help') || args.includes('-h')) {
  console.log('用法: node scripts/prune-uploads.js [--apply] [--min-age-hours=24]')
  process.exit(0)
}
if (!Number.isFinite(minAgeHours) || minAgeHours < 0) {
  console.error('--min-age-hours 必须是不小于 0 的数字')
  process.exit(2)
}

const mb = (n) => (n / 1024).toFixed(1) + ' KB'

async function main() {
  // 引用集合用 paranoid:false：软删除的项目仍算「引用着」，它的封面交给人工决策
  const rows = await Project.findAll({
    attributes: ['cover_image'],
    paranoid: false,
    raw: true
  })
  const referenced = new Set(rows.map((r) => r.cover_image).filter(Boolean))

  let names
  try {
    names = fs.readdirSync(COVER_DIR).filter((n) => fs.statSync(path.join(COVER_DIR, n)).isFile())
  } catch (err) {
    if (err.code === 'ENOENT') {
      console.log(`上传目录还不存在（${COVER_DIR}），没有东西要清扫。`)
      return
    }
    console.error('读取上传目录失败:', COVER_DIR, err.code || err.message)
    process.exit(1)
  }

  const cutoff = Date.now() - minAgeHours * 3600 * 1000
  const orphans = []
  const strange = []
  let keptReferenced = 0
  let keptTooNew = 0

  for (const name of names) {
    const url = COVER_URL_PREFIX + name
    if (!isManagedCover(url)) {
      // 命名不符合服务端规则的文件不会由本服务产生，多半是人工放进去的，只报告不动
      strange.push(name)
      continue
    }
    if (referenced.has(url)) {
      keptReferenced += 1
      continue
    }
    const stat = fs.statSync(path.join(COVER_DIR, name))
    if (stat.mtimeMs > cutoff) {
      keptTooNew += 1
      continue
    }
    orphans.push({ name, size: stat.size, mtime: stat.mtime })
  }

  console.log(`上传目录: ${COVER_DIR}`)
  console.log(
    `磁盘文件 ${names.length} 个 | 被引用 ${keptReferenced} | 未引用但未过宽限期(${minAgeHours}h) ${keptTooNew} | 孤儿候选 ${orphans.length}`
  )

  if (strange.length) {
    console.log(`\n命名异常、已跳过（需人工确认）${strange.length} 个：`)
    strange.forEach((n) => console.log('  ? ' + n))
  }

  if (!orphans.length) {
    console.log('\n没有可清扫的孤儿文件。')
    return
  }

  console.log(`\n孤儿候选：`)
  for (const o of orphans) {
    console.log(`  - ${o.name}  ${mb(o.size)}  ${o.mtime.toISOString()}`)
  }

  if (!apply) {
    console.log(`\n当前是干跑模式，未删除任何文件。加 --apply 才会真的删除。`)
    return
  }

  let removed = 0
  let freed = 0
  for (const o of orphans) {
    try {
      fs.unlinkSync(path.join(COVER_DIR, o.name))
      removed += 1
      freed += o.size
    } catch (err) {
      console.error(`  删除失败 ${o.name}: ${err.code || err.message}`)
    }
  }
  console.log(`\n已删除 ${removed}/${orphans.length} 个孤儿文件，释放 ${(freed / 1024 / 1024).toFixed(2)} MB`)
}

main()
  .then(() => sequelize.close())
  .catch(async (err) => {
    console.error('清扫失败:', err)
    await sequelize.close().catch(() => {})
    process.exit(1)
  })

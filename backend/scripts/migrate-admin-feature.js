/**
 * 管理台功能的结构迁移（幂等，可重复执行）。
 *
 * 改了什么：
 *   1. projects.is_hidden —— 管理员下架标记。
 *      ⚠️ 刻意不复用 legacy `projects.status`：线上 64/66 行 status=0，语义不可靠，
 *      拿它当「下架」会让几乎所有项目瞬间从广场消失。
 *   2. users.status / users.is_admin —— 线上已有这两列，这里只补 NOT NULL 约束，
 *      让模型声明与真实表结构一致（停用账号的逻辑依赖 status=0 的精确判定）。
 *   3. notifications：
 *      · type 枚举新增 'system'（管理台公告）
 *      · project_id 改为可空（公告不指向任何项目）
 *      · 新增 message 列（公告正文）
 *
 * 用法（在 backend/ 下）：
 *   node scripts/migrate-admin-feature.js            # 只检查并打印将要做什么
 *   node scripts/migrate-admin-feature.js --apply    # 真正执行
 *
 * 与 refresh-project-flags.js 同一契约：默认干跑，写库必须显式 --apply。
 */
const path = require('node:path')

require('dotenv').config({ path: path.resolve(__dirname, '../.env') })

const { sequelize } = require('../src/models')

const APPLY = process.argv.includes('--apply')
const UNKNOWN_ARGS = process.argv.slice(2).filter((a) => a !== '--apply')

const steps = []

const describe = async (table) => sequelize.getQueryInterface().describeTable(table)

const plan = async () => {
  const projects = await describe('projects')
  const notifications = await describe('notifications')
  const users = await describe('users')

  if (!projects.is_hidden) {
    steps.push({
      label: 'projects.is_hidden',
      run: async () => {
        const qi = sequelize.getQueryInterface()
        await qi.addColumn('projects', 'is_hidden', {
          type: sequelize.Sequelize.TINYINT,
          allowNull: false,
          defaultValue: 0,
          comment: '管理员下架: 1-已下架(公开列表不可见), 0-正常'
        })
        await qi.addIndex('projects', ['is_hidden'], { name: 'idx_hidden' })
      }
    })
  } else {
    console.log('· projects.is_hidden 已存在，跳过')
  }

  for (const column of ['status', 'is_admin']) {
    const def = users[column]
    if (!def || def.allowNull === false) {
      console.log(`· users.${column} 已存在且为 NOT NULL，跳过`)
      continue
    }
    steps.push({
      label: `users.${column} 收紧为 NOT NULL`,
      run: async () => {
        // 先补空值再收紧：直接 MODIFY 会在存在 NULL 时失败
        const fallback = column === 'status' ? 1 : 0
        await sequelize.query(`UPDATE users SET \`${column}\` = :fallback WHERE \`${column}\` IS NULL`, {
          replacements: { fallback }
        })
        await sequelize.getQueryInterface().changeColumn('users', column, {
          type: sequelize.Sequelize.TINYINT,
          allowNull: false,
          defaultValue: fallback
        })
      }
    })
  }

  const typeDef = notifications.type
  const typeValues = typeDef && typeDef.type && Array.isArray(typeDef.type.values) ? typeDef.type.values : []
  if (!typeValues.includes('system')) {
    steps.push({
      label: "notifications.type 增加 'system'",
      run: async () => {
        await sequelize.getQueryInterface().changeColumn('notifications', 'type', {
          type: sequelize.Sequelize.ENUM('comment', 'reply', 'like', 'participate', 'mention', 'system'),
          allowNull: false
        })
      }
    })
  } else {
    console.log('· notifications.type 已包含 system，跳过')
  }

  if (notifications.project_id && notifications.project_id.allowNull === false) {
    steps.push({
      label: 'notifications.project_id 改为可空',
      run: async () => {
        await sequelize.getQueryInterface().changeColumn('notifications', 'project_id', {
          type: sequelize.Sequelize.INTEGER.UNSIGNED,
          allowNull: true
        })
      }
    })
  } else {
    console.log('· notifications.project_id 已可空，跳过')
  }

  if (!notifications.message) {
    steps.push({
      label: 'notifications.message',
      run: async () => {
        await sequelize.getQueryInterface().addColumn('notifications', 'message', {
          type: sequelize.Sequelize.STRING(255),
          allowNull: true,
          comment: '系统公告正文（type=system 时使用）'
        })
      }
    })
  } else {
    console.log('· notifications.message 已存在，跳过')
  }
}

const main = async () => {
  if (UNKNOWN_ARGS.length) {
    console.log(`未知参数: ${UNKNOWN_ARGS.join(' ')}`)
    console.log('用法: node scripts/migrate-admin-feature.js [--apply]')
    process.exit(2)
  }

  await plan()

  if (!steps.length) {
    console.log('结构已是最新，无需迁移。')
    return
  }

  console.log(`\n待执行 ${steps.length} 项：`)
  steps.forEach((s, i) => console.log(`  ${i + 1}. ${s.label}`))

  if (!APPLY) {
    console.log('\n这是干跑。确认无误后加 --apply 真正写入数据库。')
    return
  }

  for (const step of steps) {
    console.log(`\n执行: ${step.label} ...`)
    await step.run()
    console.log('完成')
  }
  console.log('\n全部迁移完成。')
}

main()
  .catch((error) => {
    console.error('\n迁移失败:', error.message)
    process.exitCode = 1
  })
  .finally(() => sequelize.close())

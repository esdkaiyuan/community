/**
 * 加密项目功能的结构迁移（幂等，可重复执行）。
 *
 * 新增三列：
 *   · projects.lock_level        none | repo | project
 *   · projects.lock_password_hash  bcrypt 哈希（明文绝不入库）
 *   · projects.lock_slot_user_id   唯一槽位：保证每个账号最多 1 个加密项目
 *
 * 用法（在 backend/ 下）：
 *   node scripts/migrate-encrypted-project.js            # 干跑
 *   node scripts/migrate-encrypted-project.js --apply    # 真正执行
 */
const path = require('node:path')

require('dotenv').config({ path: path.resolve(__dirname, '../.env') })

const { sequelize } = require('../src/models')

const APPLY = process.argv.includes('--apply')
const UNKNOWN_ARGS = process.argv.slice(2).filter((a) => a !== '--apply')

const steps = []
const describe = (table) => sequelize.getQueryInterface().describeTable(table)

const plan = async () => {
  const projects = await describe('projects')

  if (!projects.lock_level) {
    steps.push({
      label: 'projects.lock_level',
      run: async () => {
        await sequelize.getQueryInterface().addColumn('projects', 'lock_level', {
          type: sequelize.Sequelize.STRING(16),
          allowNull: false,
          defaultValue: 'none',
          comment: '访问加密级别: none-公开, repo-加密仓库, project-整项目加密'
        })
      }
    })
  } else {
    console.log('· projects.lock_level 已存在，跳过')
  }

  if (!projects.lock_password_hash) {
    steps.push({
      label: 'projects.lock_password_hash',
      run: async () => {
        await sequelize.getQueryInterface().addColumn('projects', 'lock_password_hash', {
          type: sequelize.Sequelize.STRING(255),
          allowNull: true,
          comment: '加密访问密码的 bcrypt 哈希'
        })
      }
    })
  } else {
    console.log('· projects.lock_password_hash 已存在，跳过')
  }

  if (!projects.lock_slot_user_id) {
    steps.push({
      label: 'projects.lock_slot_user_id + 唯一索引',
      run: async () => {
        const qi = sequelize.getQueryInterface()
        await qi.addColumn('projects', 'lock_slot_user_id', {
          type: sequelize.Sequelize.INTEGER,
          allowNull: true,
          comment: '加密项目槽位：创建者 id，保证每账号最多 1 个加密项目'
        })
        await qi.addIndex('projects', ['lock_slot_user_id'], {
          name: 'uniq_lock_slot_user_id',
          unique: true
        })
      }
    })
  } else {
    console.log('· projects.lock_slot_user_id 已存在，跳过')
  }
}

const main = async () => {
  if (UNKNOWN_ARGS.length) {
    console.log(`未知参数: ${UNKNOWN_ARGS.join(' ')}`)
    console.log('用法: node scripts/migrate-encrypted-project.js [--apply]')
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

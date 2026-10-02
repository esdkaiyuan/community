const mysql = require('mysql2/promise')
require('dotenv').config({ path: __dirname + '/../.env' })

// 种子数据：目前只有 8 条分类。
//
// ⚠️ 这里曾经还往一张 `tags` 表插 18 个标签。那张表**从未在线上创建过**、也没有任何
//    代码读写（标签的唯一真源是 projects.tags JSON 列），已在消除 schema 漂移时删掉建表
//    语句与模型 —— 于是这段插入变成「往不存在的表写数据」，每次跑都报错。已整段移除：
//    标签建议由前端 DEFAULT_TAG_SUGGESTIONS 提供，不需要种子表。
//
// 幂等性：categories 上有 UNIQUE KEY name，`ON DUPLICATE KEY UPDATE` 让本脚本可以
// 反复执行而不产生重复分类（这也是那条唯一键不能删的原因）。
//
// 退出码：失败必须 exit(1)。此前只 console.error 就继续走，脚本永远返回 0，
// 调用方（部署脚本 / CI）根本不知道种子其实没写进去。
async function seed() {
  const connection = await mysql.createConnection({
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
  })

  try {
    console.log('开始插入种子数据...')

    // 插入分类数据
    const categories = [
      { name: '技术开发', icon: 'code', description: '软件、应用、工具开发', sort_order: 1 },
      { name: '设计创意', icon: 'design', description: 'UI/UX、视觉设计', sort_order: 2 },
      { name: '产品/运营', icon: 'product', description: '产品设计、运营策略', sort_order: 3 },
      { name: '内容创作', icon: 'content', description: '文章、视频、音频创作', sort_order: 4 },
      { name: '硬件/物联网', icon: 'hardware', description: '硬件开发、IoT 项目', sort_order: 5 },
      { name: '研究学习', icon: 'research', description: '学术研究、知识分享', sort_order: 6 },
      { name: '开源专区', icon: 'opensource', description: '开源项目协作', sort_order: 7 },
      { name: '公益/社会创新', icon: 'public-welfare', description: '社会公益项目', sort_order: 8 }
    ]

    for (const cat of categories) {
      await connection.execute(
        'INSERT INTO categories (name, icon, description, sort_order) VALUES (?, ?, ?, ?) ON DUPLICATE KEY UPDATE name=name',
        [cat.name, cat.icon, cat.description, cat.sort_order]
      )
    }
    console.log(`✓ 分类数据插入完成（${categories.length} 条）`)

    // 事后核对：不信「执行没报错」，直接问库里有几条
    const [rows] = await connection.execute('SELECT COUNT(*) AS n FROM categories')
    console.log(`✓ 库内分类总数：${rows[0].n}`)

    console.log('种子数据插入完成！')
  } catch (error) {
    console.error('种子数据插入失败:', error.message)
    process.exitCode = 1
  } finally {
    await connection.end()
  }
}

seed()

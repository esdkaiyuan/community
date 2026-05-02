const mysql = require('mysql2/promise')
require('dotenv').config({ path: __dirname + '/../.env' })

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
    console.log('✓ 分类数据插入完成')

    // 插入标签数据
    const tags = ['开发', '开源', '效率工具', '设计', '小程序', '公益', 'AI', '硬件', '物联网', '智能家居', '产品', '教育', '协作', '游戏开发', '像素风', '独立游戏', '字体', '社区']
    
    for (const tagName of tags) {
      await connection.execute(
        'INSERT INTO tags (name) VALUES (?) ON DUPLICATE KEY UPDATE name=name',
        [tagName]
      )
    }
    console.log('✓ 标签数据插入完成')

    console.log('种子数据插入完成！')
  } catch (error) {
    console.error('种子数据插入失败:', error)
  } finally {
    await connection.end()
  }
}

seed()

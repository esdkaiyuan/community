const { Category, sequelize } = require('../models')
const ApiError = require('../utils/ApiError')

exports.listCategories = async () => {
  const categories = await Category.findAll({ order: [['sort_order', 'ASC']] })

  // 实时统计各分类未删除项目数
  const [counts] = await sequelize.query(
    'SELECT category_id, COUNT(*) AS c FROM projects WHERE deleted_at IS NULL GROUP BY category_id'
  )
  const countMap = {}
  counts.forEach((r) => {
    countMap[r.category_id] = Number(r.c)
  })

  return categories.map((cat) => {
    const row = cat.toJSON()
    return { ...row, count: countMap[row.id] || 0 }
  })
}

exports.getCategory = async (id) => {
  const category = await Category.findByPk(id)
  if (!category) throw ApiError.notFound('分类不存在')
  return category
}

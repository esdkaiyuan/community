const Category = require('../models/Category');
const sequelize = require('../config/database');

// 获取所有分类（附带每个分类下的实时项目数 count，供前端展示）
exports.getAllCategories = async (req, res) => {
  try {
    const categories = await Category.findAll({
      order: [['sort_order', 'ASC']]
    });

    // 实时统计各分类未删除项目数
    const [counts] = await sequelize.query(
      'SELECT category_id, COUNT(*) AS c FROM projects WHERE deleted_at IS NULL GROUP BY category_id'
    );
    const countMap = {};
    counts.forEach(r => { countMap[r.category_id] = Number(r.c) });

    res.json({
      code: 200,
      message: '获取分类成功',
      data: categories.map(cat => {
        const row = cat.toJSON();
        return { ...row, count: countMap[row.id] || 0 };
      })
    });
  } catch (error) {
    console.error('获取分类失败:', error);
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    });
  }
};

// 根据ID获取分类
exports.getCategoryById = async (req, res) => {
  try {
    const { id } = req.params;
    const category = await Category.findByPk(id);

    if (!category) {
      return res.status(404).json({
        code: 404,
        message: '分类不存在'
      });
    }

    res.json({
      code: 200,
      message: '获取分类成功',
      data: category
    });
  } catch (error) {
    console.error('获取分类失败:', error);
    res.status(500).json({
      code: 500,
      message: '服务器错误'
    });
  }
};

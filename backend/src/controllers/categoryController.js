const Category = require('../models/Category');

// 获取所有分类
exports.getAllCategories = async (req, res) => {
  try {
    const categories = await Category.findAll({
      order: [['sort_order', 'ASC']]
    });
    
    res.json({
      code: 200,
      message: '获取分类成功',
      data: categories
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

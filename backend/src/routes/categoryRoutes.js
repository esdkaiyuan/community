const express = require('express');
const router = express.Router();
const categoryController = require('../controllers/categoryController');

// 获取所有分类
router.get('/', categoryController.getAllCategories);

// 根据ID获取分类
router.get('/:id', categoryController.getCategoryById);

module.exports = router;

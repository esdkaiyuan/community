const categoryService = require('../services/category.service')
const asyncHandler = require('../utils/asyncHandler')
const { ok } = require('../utils/response')

exports.getAllCategories = asyncHandler(async (req, res) => {
  const data = await categoryService.listCategories()
  ok(res, data, '获取分类成功')
})

exports.getCategoryById = asyncHandler(async (req, res) => {
  const data = await categoryService.getCategory(req.params.id)
  ok(res, data, '获取分类成功')
})

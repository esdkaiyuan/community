import request from './request'

// 获取所有分类
export function getCategories() {
  return request.get('/categories')
}

// 根据ID获取分类
export function getCategoryById(id) {
  return request.get(`/categories/${id}`)
}

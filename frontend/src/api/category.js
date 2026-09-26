import request from './request'

// 全部分类（带各分类项目数 count）
export const getCategories = () => request.get('/categories')

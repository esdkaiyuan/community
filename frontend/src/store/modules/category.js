import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCategories } from '@/api/category'
import { mockCategories } from '@/utils/mockData'

export const useCategoryStore = defineStore('category', () => {
  const categories = ref([])
  const loading = ref(false)

  // 获取所有分类
  async function fetchCategories() {
    loading.value = true
    try {
      const res = await getCategories()
      categories.value = res.data
      return res
    } catch (error) {
      console.warn('获取分类失败，使用模拟数据', error)
      // 使用模拟数据
      categories.value = mockCategories.map(cat => ({
        ...cat,
        icon: cat.icon
      }))
      return { data: categories.value }
    } finally {
      loading.value = false
    }
  }

  return {
    categories,
    loading,
    fetchCategories
  }
})

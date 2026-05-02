<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2>项目分类</h2>
    </div>
    
    <nav class="category-list">
      <div
        v-for="category in categories"
        :key="category.id"
        class="category-item"
        :class="{ active: selectedCategoryId === category.id }"
        @click="selectCategory(category.id)"
      >
        <el-icon v-if="category.icon">
          <component :is="category.icon" />
        </el-icon>
        <span>{{ category.name }}</span>
        <el-tag v-if="category.count" size="small" type="info">
          {{ category.count }}
        </el-tag>
      </div>
    </nav>
  </aside>
</template>

<script setup>
import { onMounted } from 'vue'
import { useCategoryStore } from '@/store/modules/category'
import { storeToRefs } from 'pinia'

const props = defineProps({
  selectedCategoryId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['category-change'])

const categoryStore = useCategoryStore()
const { categories } = storeToRefs(categoryStore)

// 加载分类数据
onMounted(async () => {
  if (categories.value.length === 0) {
    await categoryStore.fetchCategories()
  }
})

// 选择分类
const selectCategory = (categoryId) => {
  emit('category-change', categoryId === props.selectedCategoryId ? null : categoryId)
}
</script>

<style lang="scss" scoped>
.sidebar {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  height: fit-content;
  position: sticky;
  top: 80px;

  .sidebar-header {
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #f0f0f0;

    h2 {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
  }

  .category-list {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .category-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.3s;
      font-size: 14px;
      color: #606266;

      &:hover {
        background-color: #f5f7fa;
        color: #409eff;
      }

      &.active {
        background-color: #ecf5ff;
        color: #409eff;
        font-weight: 500;
      }

      .el-icon {
        font-size: 18px;
      }

      span {
        flex: 1;
      }

      .el-tag {
        font-size: 12px;
      }
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .sidebar {
    position: static;
    margin-bottom: 16px;
  }
}
</style>

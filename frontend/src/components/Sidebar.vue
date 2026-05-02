<template>
  <aside class="sidebar">
    <!-- 第一部分：导航菜单 -->
    <nav class="nav-menu">
      <div
        v-for="item in navItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: activeNav === item.key }"
        @click="handleNavClick(item.key)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </div>
    </nav>

    <!-- 分隔线 -->
    <div class="divider">
      <span>分区</span>
    </div>

    <!-- 第二部分：分类列表 -->
    <nav class="category-list">
      <div
        v-for="category in categories"
        :key="category.id"
        class="category-item"
        :class="{ active: selectedCategoryId === category.id }"
        @click="selectCategory(category.id)"
      >
        <el-icon><component :is="categoryIcons[category.name] || Monitor" /></el-icon>
        <span>{{ category.name }}</span>
      </div>
      <div class="category-item more-categories">
        <el-icon><MoreFilled /></el-icon>
        <span>所有分区</span>
      </div>
    </nav>

    <!-- 第三部分：发布项目卡片 -->
    <div class="publish-card">
      <div class="publish-icon">
        <el-icon><EditPen /></el-icon>
      </div>
      <div class="publish-content">
        <h3>发布你的项目</h3>
        <p>分享想法，找到伙伴</p>
      </div>
      <el-button type="primary" @click="goPublish">
        + 发布项目
      </el-button>
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/store/modules/category'
import { storeToRefs } from 'pinia'
import {
  House,
  Compass,
  TrendCharts,
  Clock,
  Timer,
  Monitor,
  Brush,
  ShoppingBag,
  VideoCamera,
  Cpu,
  Reading,
  Share,
  Handbag,
  MoreFilled,
  EditPen
} from '@element-plus/icons-vue'

const props = defineProps({
  selectedCategoryId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['category-change'])

const router = useRouter()
const categoryStore = useCategoryStore()
const { categories } = storeToRefs(categoryStore)

// 导航菜单
const activeNav = ref('home')
const navItems = [
  { key: 'home', label: '首页', icon: House },
  { key: 'discover', label: '发现项目', icon: Compass },
  { key: 'hot', label: '热门项目', icon: TrendCharts },
  { key: 'latest', label: '最新项目', icon: Clock },
  { key: 'deadline', label: '即将截止', icon: Timer }
]

// 分类图标映射
const categoryIcons = {
  '技术开发': Monitor,
  '设计创意': Brush,
  '产品/运营': ShoppingBag,
  '内容创作': VideoCamera,
  '硬件/物联网': Cpu,
  '研究学习': Reading,
  '开源专区': Share,
  '公益/社会创新': Handbag
}

// 加载分类数据
onMounted(async () => {
  if (categories.value.length === 0) {
    await categoryStore.fetchCategories()
  }
})

// 导航点击
const handleNavClick = (key) => {
  activeNav.value = key
  if (key === 'home') {
    router.push('/')
  }
}

// 选择分类
const selectCategory = (categoryId) => {
  emit('category-change', categoryId === props.selectedCategoryId ? null : categoryId)
}

// 跳转到发布项目页面
const goPublish = () => {
  router.push('/publish')
}
</script>

<style lang="scss" scoped>
.sidebar {
  width: 200px;
  background: transparent;
  height: fit-content;
  position: sticky;
  top: 80px;

  // 导航菜单
  .nav-menu {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 16px;

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;
      font-size: 14px;
      color: #606266;

      &:hover {
        background-color: #f5f7fa;
        color: #409eff;
      }

      &.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      }

      .el-icon {
        font-size: 18px;
      }
    }
  }

  // 分隔线
  .divider {
    position: relative;
    margin: 16px 0;
    text-align: center;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      width: 100%;
      height: 1px;
      background-color: #e4e7ed;
    }

    span {
      position: relative;
      display: inline-block;
      padding: 0 12px;
      background: #f5f7fa;
      font-size: 12px;
      color: #909399;
      z-index: 1;
    }
  }

  // 分类列表
  .category-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 24px;

    .category-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
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

      &.more-categories {
        color: #909399;
        
        &:hover {
          color: #409eff;
        }
      }

      .el-icon {
        font-size: 18px;
      }

      span {
        flex: 1;
      }
    }
  }

  // 发布项目卡片
  .publish-card {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    text-align: center;

    .publish-icon {
      width: 48px;
      height: 48px;
      margin: 0 auto 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 24px;
    }

    .publish-content {
      margin-bottom: 16px;

      h3 {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 8px 0;
      }

      p {
        font-size: 13px;
        color: #909399;
        margin: 0;
      }
    }

    .el-button {
      width: 100%;
      height: 40px;
      font-size: 14px;
      font-weight: 500;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);

      &:hover {
        opacity: 0.9;
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
      }
    }
  }
}

// 响应式适配
@media (max-width: 1024px) {
  .sidebar {
    width: 180px;
    padding: 16px;

    .nav-item,
    .category-item {
      font-size: 13px;
      padding: 10px 12px;
    }

    .publish-card {
      padding: 12px;

      .publish-content {
        h3 {
          font-size: 14px;
        }

        p {
          font-size: 12px;
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .sidebar {
    position: static;
    width: 100%;
    margin-bottom: 16px;
    max-height: none;
    overflow-y: visible;

    .nav-menu {
      display: flex;
      overflow-x: auto;
      gap: 8px;
      padding-bottom: 8px;

      &::-webkit-scrollbar {
        height: 4px;
      }

      .nav-item {
        white-space: nowrap;
        flex-shrink: 0;
      }
    }

    .divider {
      display: none;
    }

    .category-list {
      display: flex;
      overflow-x: auto;
      gap: 8px;
      padding-bottom: 8px;

      &::-webkit-scrollbar {
        height: 4px;
      }

      .category-item {
        white-space: nowrap;
        flex-shrink: 0;
      }
    }

    .publish-card {
      display: none;
    }
  }
}

@media (max-width: 480px) {
  .sidebar {
    .nav-item,
    .category-item {
      font-size: 12px;
      padding: 8px 10px;

      .el-icon {
        font-size: 14px;
      }
    }
  }
}
</style>

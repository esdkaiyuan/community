<template>
  <div class="project-grid">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="projects.length === 0" description="暂无项目" />

    <!-- 项目列表 -->
    <div v-else class="grid-container">
      <ProjectCard
        v-for="project in projects"
        :key="project.id"
        :project="project"
        @like="handleLike"
      />
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[12, 24, 36]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import ProjectCard from './ProjectCard.vue'

const props = defineProps({
  projects: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  total: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['like', 'page-change'])

const currentPage = ref(1)
const pageSize = ref(12)

// 处理点赞
const handleLike = (projectId) => {
  emit('like', projectId)
}

// 页码变化
const handleCurrentChange = (page) => {
  emit('page-change', { page, pageSize: pageSize.value })
}

// 每页数量变化
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  emit('page-change', { page: 1, pageSize: size })
}

// 监听外部传入的页码变化
watch(() => props.projects, () => {
  // 当项目列表变化时，重置到第一页
  if (props.projects.length === 0) {
    currentPage.value = 1
  }
})
</script>

<style lang="scss" scoped>
.project-grid {
  .loading-container {
    padding: 20px;
    background: #fff;
    border-radius: 8px;
  }

  .grid-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
  }

  .pagination-container {
    margin-top: 32px;
    display: flex;
    justify-content: center;
  }
}

// 响应式适配
@media (max-width: 1200px) {
  .project-grid {
    .grid-container {
      grid-template-columns: repeat(3, 1fr);
    }
  }
}

@media (max-width: 900px) {
  .project-grid {
    .grid-container {
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }
  }
}

@media (max-width: 768px) {
  .project-grid {
    .grid-container {
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }
  }
}

@media (max-width: 480px) {
  .project-grid {
    .grid-container {
      grid-template-columns: 1fr;
      gap: 12px;
    }

    .pagination-container {
      :deep(.el-pagination) {
        .el-pagination__sizes,
        .el-pagination__jump {
          display: none;
        }

        .btn-prev,
        .btn-next {
          padding: 8px 12px;
        }

        .el-pager li {
          min-width: 28px;
          height: 28px;
          line-height: 28px;
        }
      }
    }
  }
}
</style>

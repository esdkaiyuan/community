<template>
  <div class="home-view">
    <!-- 顶部导航栏 -->
    <Header />

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <!-- 左侧边栏 -->
        <Sidebar :selected-category-id="selectedCategoryId" @category-change="handleCategoryChange" />

        <!-- 右侧项目列表 -->
        <div class="project-section">
          <ProjectGrid
            :projects="projects"
            :loading="loading"
            :total="total"
            @like="handleLike"
            @page-change="handlePageChange"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '@/store/modules/project'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/modules/user'
import Header from '@/components/Header.vue'
import Sidebar from '@/components/Sidebar.vue'
import ProjectGrid from '@/components/ProjectGrid.vue'

const route = useRoute()
const projectStore = useProjectStore()
const userStore = useUserStore()
const { projects, loading, total } = storeToRefs(projectStore)

const selectedCategoryId = ref(null)
const currentPage = ref(1)
const pageSize = ref(12)
const searchKeyword = ref('')

// 加载项目列表
const loadProjects = async () => {
  const params = {
    page: currentPage.value,
    pageSize: pageSize.value
  }

  if (selectedCategoryId.value) {
    params.categoryId = selectedCategoryId.value
  }

  if (searchKeyword.value) {
    params.search = searchKeyword.value
  }

  await projectStore.fetchProjects(params)
}

// 处理分类变化
const handleCategoryChange = (categoryId) => {
  selectedCategoryId.value = categoryId
  currentPage.value = 1
  loadProjects()
}

// 处理页码变化
const handlePageChange = ({ page, pageSize: size }) => {
  currentPage.value = page
  pageSize.value = size
  loadProjects()
}

// 处理点赞
const handleLike = async (projectId) => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }

  try {
    // 这里需要根据实际情况判断是点赞还是取消点赞
    // 暂时简化为只调用点赞接口
    await projectStore.likeProjectAction(projectId)
    ElMessage.success('点赞成功')
  } catch (error) {
    console.error('点赞失败:', error)
  }
}

// 监听路由查询参数变化
watch(
  () => route.query.search,
  (newSearch) => {
    searchKeyword.value = newSearch || ''
    currentPage.value = 1
    loadProjects()
  }
)

// 初始化
onMounted(() => {
  // 从路由获取搜索关键词
  if (route.query.search) {
    searchKeyword.value = route.query.search
  }
  
  loadProjects()
})
</script>

<style lang="scss" scoped>
.home-view {
  min-height: 100vh;
  background-color: #f5f7fa;

  .main-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;

    .content-container {
      display: grid;
      grid-template-columns: 240px 1fr;
      gap: 24px;
      align-items: start;
    }

    .project-section {
      min-height: 400px;
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .home-view {
    .main-content {
      padding: 16px;

      .content-container {
        grid-template-columns: 1fr;
        gap: 16px;
      }
    }
  }
}
</style>

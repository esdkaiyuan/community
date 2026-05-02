<template>
  <div class="project-detail-view">
    <Header />
    <div class="detail-container">
      <el-skeleton v-if="loading" :rows="10" animated />
      <div v-else-if="currentProject" class="detail-content">
        <h1>{{ currentProject.title }}</h1>
        <p>{{ currentProject.description }}</p>
        <el-divider />
        <p>项目详情页面开发中...</p>
      </div>
      <el-empty v-else description="项目不存在" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '@/store/modules/project'
import { storeToRefs } from 'pinia'
import Header from '@/components/Header.vue'

const route = useRoute()
const projectStore = useProjectStore()
const { currentProject, loading } = storeToRefs(projectStore)

onMounted(async () => {
  await projectStore.fetchProjectById(route.params.id)
})
</script>

<style lang="scss" scoped>
.project-detail-view {
  min-height: 100vh;
  background-color: #f5f7fa;

  .detail-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 24px;

    .detail-content {
      background: #fff;
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      h1 {
        font-size: 28px;
        color: #303133;
        margin-bottom: 16px;
      }

      p {
        font-size: 16px;
        color: #606266;
        line-height: 1.8;
      }
    }
  }
}
</style>

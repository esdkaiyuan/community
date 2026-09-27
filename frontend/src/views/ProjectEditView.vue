<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <div class="mb-8">
      <h1 class="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">编辑项目</h1>
      <p class="mt-2 text-sm text-ink-mid">改完立即生效，新加的标签会同步进广场的「热门标签」。</p>
    </div>

    <!-- 骨架：拉详情期间避免表单闪现又回填 -->
    <div v-if="loading" class="card space-y-5 p-6 sm:p-8" data-test="edit-loading">
      <div class="skeleton h-9 w-full"></div>
      <div class="skeleton h-9 w-2/3"></div>
      <div class="skeleton h-40 w-full"></div>
    </div>

    <EmptyState
      v-else-if="!project"
      icon="search"
      title="找不到这个项目"
      description="它可能已被删除，或者链接不正确。"
    >
      <router-link to="/" class="btn-primary">回到项目广场</router-link>
    </EmptyState>

    <EmptyState
      v-else-if="!isOwner"
      data-test="edit-forbidden"
      icon="users"
      title="只有发起人可以编辑"
      description="这个项目由其他伙伴发起，你可以先去详情页参与共创。"
    >
      <router-link :to="`/project/${project.id}`" class="btn-secondary">返回项目详情</router-link>
    </EmptyState>

    <ProjectForm v-else mode="edit" :project="project" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getProject } from '@/api/project'
import { useUserStore } from '@/store/user'
import ProjectForm from '@/components/ProjectForm.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const userStore = useUserStore()

const project = ref(null)
const loading = ref(true)

const isOwner = computed(
  () =>
    !!project.value &&
    userStore.isLoggedIn &&
    project.value.creator?.id === userStore.userId
)

onMounted(async () => {
  try {
    const res = await getProject(route.params.id)
    project.value = res.data
  } catch {
    project.value = null // 不存在 / 已删除：走 EmptyState
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    <nav class="mb-4 flex min-w-0 items-center gap-1.5 text-footnote text-ink-dim">
      <router-link to="/" class="shrink-0 transition-colors hover:text-pine">项目广场</router-link>
      <span class="shrink-0">/</span>
      <router-link
        v-if="project"
        :to="`/project/${project.id}`"
        class="hidden shrink-0 transition-colors hover:text-pine sm:inline"
      >
        {{ project.title }}
      </router-link>
      <span v-if="project" class="hidden shrink-0 sm:inline">/</span>
      <span class="truncate text-ink-mid">编辑</span>
    </nav>

    <!-- 骨架：拉详情期间避免表单闪现又回填 -->
    <div
      v-if="loading"
      class="overflow-hidden rounded-22 border border-line bg-cream shadow-card"
      data-test="edit-loading"
    >
      <div class="flex items-center gap-3 border-b border-line bg-sand/40 px-6 py-4">
        <div class="flex gap-1.5">
          <span class="h-2.5 w-2.5 rounded-full bg-line-strong"></span>
          <span class="h-2.5 w-2.5 rounded-full bg-line-strong"></span>
          <span class="h-2.5 w-2.5 rounded-full bg-line-strong"></span>
        </div>
        <div class="skeleton h-4 w-32"></div>
      </div>
      <div class="grid gap-8 p-6 sm:p-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div class="space-y-6">
          <div class="skeleton h-11 w-full"></div>
          <div class="skeleton h-24 w-full"></div>
          <div class="skeleton h-44 w-full"></div>
          <div class="skeleton h-28 w-full"></div>
        </div>
        <div class="hidden space-y-3 lg:block">
          <div class="skeleton aspect-[16/9] w-full"></div>
          <div class="skeleton h-4 w-2/3"></div>
          <div class="skeleton h-4 w-full"></div>
        </div>
      </div>
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

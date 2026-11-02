<template>
  <div class="mx-auto max-w-6xl px-4 py-10 pb-24 sm:px-6">
    <!-- 页头：与站内其他页面同一套手绘字标 + 等宽 eyebrow -->
    <header class="flex flex-wrap items-end justify-between gap-4">
      <div class="min-w-0">
        <p class="eyebrow">Admin Console</p>
        <h1 class="mt-3 font-brand text-[clamp(2rem,3vw,2.8rem)] font-bold tracking-normal text-ink">管理台</h1>
        <p class="mt-2 max-w-xl text-footnote leading-relaxed text-ink-mid">
          管理项目、成员与站内通知。所有写操作都会记录到审计日志；停用账号与撤销权限会在下一次请求时立即生效。
        </p>
      </div>
      <span
        v-if="userStore.isAdmin"
        class="inline-flex items-center gap-2 rounded-full border border-line/70 bg-cream px-3 py-1.5 text-caption1 text-ink-mid shadow-card"
      >
        <AppIcon name="shield" class="h-4 w-4 text-pine-deep" />
        管理员
      </span>
    </header>

    <!-- 分区切换：?tab= 同步，便于直接落地某个面板 -->
    <div class="mt-7 overflow-x-auto">
      <AppSegmented v-model="tab" :options="TABS" aria-label="管理台分区" test-id="admin-tab" />
    </div>

    <div class="mt-7">
      <component :is="activePanel" :key="tab" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import AppSegmented from '@/components/AppSegmented.vue'
import AppIcon from '@/components/AppIcon.vue'
import AdminOverviewPanel from '@/components/admin/AdminOverviewPanel.vue'
import AdminProjectsPanel from '@/components/admin/AdminProjectsPanel.vue'
import AdminUsersPanel from '@/components/admin/AdminUsersPanel.vue'
import AdminNotificationsPanel from '@/components/admin/AdminNotificationsPanel.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const TABS = [
  { value: 'overview', label: '概览', icon: 'trendingUp' },
  { value: 'projects', label: '项目', icon: 'lightbulb' },
  { value: 'users', label: '用户', icon: 'users' },
  { value: 'notifications', label: '通知', icon: 'bell' }
]

const PANELS = {
  overview: AdminOverviewPanel,
  projects: AdminProjectsPanel,
  users: AdminUsersPanel,
  notifications: AdminNotificationsPanel
}

const tab = computed({
  get: () => {
    const value = route.query.tab
    return TABS.some((t) => t.value === value) ? value : 'overview'
  },
  set: (value) => {
    router.replace({ query: value === 'overview' ? {} : { tab: value } })
  }
})

const activePanel = computed(() => PANELS[tab.value])
</script>

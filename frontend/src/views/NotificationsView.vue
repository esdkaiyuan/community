<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <!-- 页头：苹果式大标题 -->
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">通知</h1>
        <p class="mt-2 text-sm text-ink-mid">
          <template v-if="unread > 0">有 {{ unread }} 条未读，共 {{ total }} 条</template>
          <template v-else>全部已读，共 {{ total }} 条</template>
        </p>
      </div>
      <button v-if="unread > 0" class="btn-secondary text-sm" :disabled="marking" @click="markAllRead">
        {{ marking ? '处理中…' : '全部标为已读' }}
      </button>
    </div>

    <!-- 分段控件：全部 / 未读 -->
    <div class="mt-6 inline-flex rounded-full bg-sand p-1">
      <button
        v-for="opt in filterOptions"
        :key="opt.value"
        class="rounded-full px-4 py-1.5 text-sm transition-all duration-200"
        :class="filter === opt.value ? 'bg-cream font-medium text-ink shadow-sm' : 'text-ink-mid hover:text-ink'"
        @click="switchFilter(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- 通知列表 -->
    <div class="mt-6">
      <div v-if="loading" class="card divide-y divide-line overflow-hidden !p-0">
        <div v-for="i in 5" :key="i" class="flex items-start gap-3 px-5 py-4">
          <div class="h-10 w-10 shrink-0 animate-pulse rounded-full bg-sand"></div>
          <div class="min-w-0 flex-1 space-y-2 py-0.5">
            <div class="h-3.5 w-3/5 animate-pulse rounded bg-sand"></div>
            <div class="h-3 w-2/5 animate-pulse rounded bg-sand"></div>
          </div>
        </div>
      </div>

      <EmptyState
        v-else-if="!notifications.length"
        icon="bell"
        :title="filter === 'unread' ? '没有未读通知' : '还没有收到通知'"
        :description="
          filter === 'unread'
            ? '所有通知都已读完，继续保持。'
            : '有人评论、回复或点赞你的内容时，这里会第一时间告诉你。'
        "
      >
        <router-link v-if="filter === 'unread'" class="btn-secondary text-sm" to="/notifications?filter=all">
          查看全部通知
        </router-link>
      </EmptyState>

      <div v-else class="card divide-y divide-line overflow-hidden !p-0">
        <button
          v-for="(n, i) in notifications"
          :key="n.id"
          v-reveal="Math.min(i, 8) * 40"
          class="group flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-sand"
          :class="n.isRead ? '' : 'bg-pine-soft/40'"
          @click="openNotification(n)"
        >
          <span
            class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-sm font-bold text-pine-deep"
          >
            <img v-if="n.actor?.avatar" :src="n.actor.avatar" alt="" class="h-full w-full object-cover" />
            <template v-else>{{ (n.actor?.username || '友').slice(0, 1).toUpperCase() }}</template>
          </span>

          <span class="min-w-0 flex-1">
            <span class="block text-[15px] leading-snug text-ink">
              <span class="font-medium">{{ n.actor?.username || '有人' }}</span>
              {{ typeText(n.type) }}
              <span class="text-ink-mid">「{{ n.project?.title || '项目' }}」</span>
            </span>
            <span v-if="n.commentPreview" class="mt-1 block truncate text-[13px] text-ink-mid">
              {{ n.commentPreview }}
            </span>
            <span class="mt-1.5 flex items-center gap-2 text-xs text-ink-dim">
              <span>{{ relativeTime(n.createdAt) }}</span>
              <span class="text-pine-deep opacity-0 transition-opacity group-hover:opacity-100">前往查看 ›</span>
            </span>
          </span>

          <span v-if="!n.isRead" class="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-pine" title="未读"></span>
        </button>
      </div>

      <div v-if="notifications.length && notifications.length < total" class="mt-6 text-center">
        <button class="btn-ghost" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getNotifications, markRead } from '@/api/notification'
import { toast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'unread', label: '未读' }
]

const filter = ref(route.query.filter === 'unread' ? 'unread' : 'all')
const notifications = ref([])
const total = ref(0)
const unread = ref(0)
const page = ref(1)
const loading = ref(true)
const loadingMore = ref(false)
const marking = ref(false)
const PAGE_SIZE = 15

const typeText = (type) =>
  ({ comment: '评论了你的项目', reply: '回复了你在', like: '赞了你在' }[type] || '与你互动于')

const isUnreadView = computed(() => filter.value === 'unread')

const fetchPage = async (targetPage) => {
  const params = { page: targetPage, pageSize: PAGE_SIZE }
  if (isUnreadView.value) params.filter = 'unread'
  const res = await getNotifications(params)
  return res.data
}

const load = async () => {
  loading.value = true
  try {
    const data = await fetchPage(1)
    notifications.value = data.notifications
    total.value = data.total
    unread.value = data.unread
    page.value = data.page
  } catch {
    notifications.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (loadingMore.value) return
  loadingMore.value = true
  try {
    const data = await fetchPage(page.value + 1)
    notifications.value.push(...data.notifications)
    total.value = data.total
    unread.value = data.unread
    page.value = data.page
  } catch {
    // 错误已由拦截器 toast
  } finally {
    loadingMore.value = false
  }
}

const switchFilter = (value) => {
  if (filter.value === value) return
  filter.value = value
  router.replace({ query: value === 'unread' ? { filter: 'unread' } : {} })
  load()
}

const openNotification = async (n) => {
  if (!n.isRead) {
    n.isRead = true
    unread.value = Math.max(0, unread.value - 1)
    markRead({ ids: [n.id] }).catch(() => {})
    // 未读视图下，读过的条目自然离开列表
    if (isUnreadView.value) {
      notifications.value = notifications.value.filter((x) => x.id !== n.id)
      total.value = Math.max(0, total.value - 1)
    }
  }
  router.push({ path: `/project/${n.project?.id}`, hash: '#comments' })
}

const markAllRead = async () => {
  if (marking.value) return
  marking.value = true
  try {
    await markRead({ all: true })
    unread.value = 0
    if (isUnreadView.value) {
      notifications.value = []
      total.value = 0
    } else {
      notifications.value.forEach((n) => (n.isRead = true))
    }
    toast('已全部标为已读')
  } catch {
    // 错误已由拦截器 toast
  } finally {
    marking.value = false
  }
}

// 支持直接落地 /notifications?filter=unread
watch(
  () => route.query.filter,
  (val) => {
    const next = val === 'unread' ? 'unread' : 'all'
    if (next !== filter.value) {
      filter.value = next
      load()
    }
  }
)

onMounted(load)
</script>

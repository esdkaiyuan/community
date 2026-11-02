<template>
  <div class="mx-auto max-w-3xl px-4 py-10 pb-32 sm:px-6">
    <!-- 页头：手绘大标题 -->
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="eyebrow">Inbox</p>
        <h1 class="mt-3 font-brand text-[clamp(2rem,3vw,2.8rem)] font-bold tracking-normal text-ink">通知</h1>
        <p class="mt-2 text-footnote text-ink-mid">
          <template v-if="unread > 0">有 {{ unread }} 条未读，共 {{ total }} 条</template>
          <template v-else>全部已读，共 {{ total }} 条</template>
        </p>
      </div>
      <!-- 选择模式下只留一条出口，避免「全部标为已读」与「批量标记」两个入口并存 -->
      <div v-if="!selectMode && notifications.length" class="flex items-center gap-2">
        <button v-if="unread > 0" class="btn-secondary text-footnote" :disabled="marking" @click="markAllRead">
          {{ marking ? '处理中…' : '全部标为已读' }}
        </button>
        <button class="btn-ghost text-footnote" data-test="notif-select-toggle" @click="enterSelectMode">选择</button>
      </div>
    </div>

    <!-- 主筛选：已读状态（二选一，分段控件的典型场景） -->
    <AppSegmented
      :model-value="filter"
      :options="filterOptions"
      aria-label="通知筛选"
      class="mt-6"
      @update:model-value="switchFilter"
    />

    <!-- 次筛选：通知类型。6 项已超出分段控件的舒适区（2~5），故降级为 chip 行 -->
    <div class="mt-3 flex flex-wrap gap-2" role="group" aria-label="按类型筛选">
      <button
        v-for="t in TYPE_OPTIONS"
        :key="t.value"
        type="button"
        class="hig-chip"
        :class="type === t.value ? 'is-active' : ''"
        :aria-pressed="type === t.value"
        :data-value="t.value"
        data-test="notif-type-chip"
        @click="switchType(t.value)"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 通知列表 -->
    <div class="mt-6">
      <div v-if="loading" class="hig-list">
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
        :title="emptyTitle"
        :description="emptyDescription"
      >
        <router-link v-if="isFiltered" class="btn-secondary text-footnote" to="/notifications">查看全部通知</router-link>
      </EmptyState>

      <div v-else class="hig-list">
        <button
          v-for="(n, i) in notifications"
          :key="n.id"
          v-reveal="Math.min(i, 8) * 40"
          data-test="notif-row"
          class="group flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-sand"
          :class="n.isRead ? '' : 'bg-pine-soft/40'"
          @click="onRowClick(n)"
        >
          <!-- 选择模式：勾选圈取代头像位（HIG 编辑态——内容让位给选择控件） -->
          <span
            v-if="selectMode"
            class="hig-pick mt-0.5"
            :class="selected.has(n.id) ? 'hig-pick-on' : 'hig-pick-off'"
            data-test="notif-checkbox"
            :data-selected="selected.has(n.id) ? '1' : '0'"
            :aria-label="selected.has(n.id) ? '取消选择' : '选择这条通知'"
          >
            <AppIcon v-if="selected.has(n.id)" name="check" class="h-3 w-3" />
          </span>

          <span
            v-else
            class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full"
            :class="n.type === 'system' ? 'bg-amber-soft text-amber-warm' : 'bg-pine-soft text-pine-deep'"
          >
            <AppIcon v-if="n.type === 'system'" name="bell" class="h-[18px] w-[18px]" />
            <img v-else-if="n.actor?.avatar" :src="n.actor.avatar" alt="" class="h-full w-full object-cover" />
            <template v-else>{{ (n.actor?.username || '友').slice(0, 1).toUpperCase() }}</template>
          </span>

          <span class="min-w-0 flex-1">
            <span class="block text-subhead leading-snug text-ink">
              <template v-if="n.type === 'system'">
                <span class="font-medium">平台公告</span>
              </template>
              <template v-else>
                <span class="font-medium">{{ n.actor?.username || '有人' }}</span>
                {{ notificationText(n.type) }}
                <span class="text-ink-mid">「{{ n.project?.title || '项目' }}」</span>
              </template>
            </span>
            <span
              v-if="n.type === 'system' && n.message"
              class="mt-1 block whitespace-pre-line break-words text-footnote leading-relaxed text-ink-mid"
            >
              {{ n.message }}
            </span>
            <span v-else-if="n.commentPreview" class="mt-1 block truncate text-footnote text-ink-mid">
              {{ n.commentPreview }}
            </span>
            <span class="mt-1.5 flex items-center gap-2 text-caption1 text-ink-dim">
              <span>{{ relativeTime(n.createdAt) }}</span>
              <span>{{ typeLabel(n.type) }}</span>
              <span class="text-pine-deep opacity-0 transition-opacity group-hover:opacity-100">
                {{ selectMode || n.type === 'system' ? '' : '前往查看 ›' }}
              </span>
            </span>
          </span>

          <span v-if="!n.isRead && !selectMode" class="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-pine" title="未读"></span>
        </button>
      </div>

      <div v-if="notifications.length && notifications.length < total" class="mt-6 text-center">
        <button class="btn-ghost" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </div>

    <!-- 批量操作条：HIG 的编辑态浮层——贴底居中卡片，不占据文档流 -->
    <transition name="sheet">
      <div v-if="selectMode" class="fixed inset-x-0 bottom-0 z-40 px-4 pb-4">
        <div
          data-test="notif-bulk-bar"
          class="mx-auto flex max-w-3xl items-center gap-3 rounded-14 border border-[color:var(--glass-border)] bg-[color:var(--glass-nav)] px-4 py-3 shadow-pop backdrop-blur-xl backdrop-saturate-150"
        >
          <button class="text-footnote text-pine" data-test="notif-select-all" @click="toggleSelectAll">
            {{ allSelected ? '取消全选' : '全选' }}
          </button>
          <span class="flex-1 text-footnote text-ink-mid" data-test="notif-selected-count">
            已选 {{ selected.size }} 条
          </span>
          <button
            class="btn-primary !px-4 !py-1.5 text-footnote"
            :disabled="!selected.size || marking"
            data-test="notif-bulk-read"
            @click="bulkMarkRead"
          >
            {{ marking ? '处理中…' : '标记已读' }}
          </button>
          <button class="btn-ghost !px-3 !py-1.5 text-footnote" data-test="notif-done" @click="exitSelectMode">
            完成
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getNotifications, markRead } from '@/api/notification'
import { toast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import { notificationText, notificationTarget } from '@/utils/notification'
import EmptyState from '@/components/EmptyState.vue'
import AppSegmented from '@/components/AppSegmented.vue'
import AppIcon from '@/components/AppIcon.vue'

const route = useRoute()
const router = useRouter()

// 通知类型：取值与后端 Notification.type 的 ENUM 一致（schema.sql 同源）。
// 七项已超出分段控件的舒适区，故做成 chip 行而不是塞进 AppSegmented
const TYPE_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'system', label: '公告' },
  { value: 'comment', label: '评论' },
  { value: 'reply', label: '回复' },
  { value: 'like', label: '点赞' },
  { value: 'participate', label: '参与' },
  { value: 'mention', label: '提及' }
]

const TYPE_LABELS = TYPE_OPTIONS.reduce((acc, t) => ({ ...acc, [t.value]: t.label }), {})

const filterOptions = [
  { value: 'all', label: '全部', test: 'notif-filter-all' },
  { value: 'unread', label: '未读', test: 'notif-filter-unread' }
]

const filter = ref(route.query.filter === 'unread' ? 'unread' : 'all')
const type = ref(TYPE_OPTIONS.some((t) => t.value === route.query.type) ? route.query.type : 'all')
const notifications = ref([])
const total = ref(0)
const unread = ref(0)
const page = ref(1)
const loading = ref(true)
const loadingMore = ref(false)
const marking = ref(false)
const PAGE_SIZE = 15

// 选择模式（批量已读）
const selectMode = ref(false)
const selected = ref(new Set())

const isUnreadView = computed(() => filter.value === 'unread')
const isFiltered = computed(() => isUnreadView.value || type.value !== 'all')
const allSelected = computed(
  () => notifications.value.length > 0 && notifications.value.every((n) => selected.value.has(n.id))
)

const emptyTitle = computed(() => (isUnreadView.value ? '没有未读通知' : '没有这类通知'))
const emptyDescription = computed(() =>
  isUnreadView.value
    ? '所有通知都已读完，继续保持。'
    : '换个类型看看，或者回到全部通知。'
)

const typeLabel = (t) => TYPE_LABELS[t] || '互动'

const fetchPage = async (targetPage) => {
  const params = { page: targetPage, pageSize: PAGE_SIZE }
  if (isUnreadView.value) params.filter = 'unread'
  if (type.value !== 'all') params.type = type.value
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
    selected.value = new Set()
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

// 筛选态同步进 URL：可分享/可回退，也让验证脚本能直接深链到某一组合
const syncQuery = () => {
  const query = {}
  if (isUnreadView.value) query.filter = 'unread'
  if (type.value !== 'all') query.type = type.value
  router.replace({ query })
}

const switchFilter = (value) => {
  if (filter.value === value) return
  filter.value = value
  syncQuery()
  load()
}

const switchType = (value) => {
  if (type.value === value) return
  type.value = value
  syncQuery()
  load()
}

const enterSelectMode = () => {
  selectMode.value = true
  selected.value = new Set()
}

const exitSelectMode = () => {
  selectMode.value = false
  selected.value = new Set()
}

const toggleSelectAll = () => {
  if (allSelected.value) {
    selected.value = new Set()
  } else {
    selected.value = new Set(notifications.value.map((n) => n.id))
  }
}

const onRowClick = (n) => {
  if (selectMode.value) {
    const next = new Set(selected.value)
    next.has(n.id) ? next.delete(n.id) : next.add(n.id)
    selected.value = next
    return
  }
  openNotification(n)
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
  // 平台公告的正文就在当前列表里，点开只标记已读，不做原地跳转
  if (n.type === 'system') return
  router.push(notificationTarget(n))
}

// 批量已读：后端已支持 ids 数组，前端此前只暴露了「全部标为已读」这一个入口
const bulkMarkRead = async () => {
  const ids = [...selected.value]
  if (!ids.length || marking.value) return
  marking.value = true
  try {
    // 未读数按「选中项里真正未读的条数」递减，不依赖后端 affectedRows 语义 ——
    // 把已读行再 UPDATE 成 1 时，各 MySQL 配置对 affected 行的口径并不一致
    const wasUnread = notifications.value.filter((n) => ids.includes(n.id) && !n.isRead).length
    await markRead({ ids })
    unread.value = Math.max(0, unread.value - wasUnread)
    if (isUnreadView.value) {
      notifications.value = notifications.value.filter((n) => !ids.includes(n.id))
      total.value = Math.max(0, total.value - ids.length)
    } else {
      notifications.value.forEach((n) => {
        if (ids.includes(n.id)) n.isRead = true
      })
    }
    toast(`已将 ${ids.length} 条通知标为已读`)
    exitSelectMode()
  } catch {
    // 错误已由拦截器 toast
  } finally {
    marking.value = false
  }
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

// 支持直接落地 /notifications?filter=unread&type=comment
watch(
  () => [route.query.filter, route.query.type],
  ([qf, qt]) => {
    const nextFilter = qf === 'unread' ? 'unread' : 'all'
    const nextType = TYPE_OPTIONS.some((t) => t.value === qt) ? qt : 'all'
    if (nextFilter !== filter.value || nextType !== type.value) {
      filter.value = nextFilter
      type.value = nextType
      load()
    }
  }
)

onMounted(load)
</script>

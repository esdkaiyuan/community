<template>
  <div data-test="admin-notifications">
    <!-- 发送公告 -->
    <section class="hig-card p-5 sm:p-6">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-title3 font-semibold text-ink">发送站内公告</h2>
          <p class="mt-1 max-w-xl text-footnote leading-relaxed text-ink-mid">
            公告会以「平台公告」出现在收件人的通知中心。全站广播只发给正常状态的账号，停用账号和你自己不会收到。
          </p>
        </div>
        <AppSegmented
          :model-value="audience"
          :options="AUDIENCE_OPTIONS"
          aria-label="公告范围"
          test-id="admin-notice-audience"
          @update:model-value="setAudience"
        />
      </div>

      <div class="mt-4">
        <label class="form-label" for="admin-notice-message">公告内容</label>
        <textarea
          id="admin-notice-message"
          v-model="message"
          rows="3"
          maxlength="255"
          class="input resize-y leading-relaxed"
          placeholder="例如：本周六 20:00 将进行短时维护，期间发布与评论可能短暂不可用。"
          :aria-invalid="!!formError"
          @input="formError = ''"
        ></textarea>
        <div class="mt-1.5 flex items-center justify-between gap-3">
          <p v-if="formError" class="form-error !mt-0">{{ formError }}</p>
          <span v-else class="text-caption1 text-ink-dim">支持换行，最多 255 个字符。</span>
          <span class="shrink-0 text-caption1 tabular-nums text-ink-dim">{{ message.length }}/255</span>
        </div>
      </div>

      <div v-if="audience === 'single'" class="mt-3">
        <label class="form-label" for="admin-notice-user">接收用户 ID</label>
        <input
          id="admin-notice-user"
          v-model="userId"
          type="number"
          min="1"
          inputmode="numeric"
          class="input max-w-[12rem]"
          placeholder="例如 1024"
          @input="formError = ''"
        />
        <p class="mt-1 text-caption1 text-ink-dim">
          在「用户」分区可以查到账号 ID；只能发送给正常状态的账号。
        </p>
      </div>

      <div class="mt-4 flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          class="btn-primary"
          :disabled="sending || !message.trim()"
          @click="send"
        >
          <AppIcon name="bell" class="h-4 w-4" />
          {{ sending ? '发送中…' : audience === 'all' ? '发送给全部成员' : '发送公告' }}
        </button>
      </div>
    </section>

    <!-- 搜索 -->
    <div class="mt-8 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex items-center gap-3">
        <h2 class="hig-section-title">通知记录</h2>
        <span class="text-caption1 text-ink-dim">{{ fmt(summary.total) }} 条</span>
      </div>

      <form class="flex w-full max-w-sm items-center gap-2" @submit.prevent="applySearch">
        <div class="relative min-w-0 flex-1">
          <AppIcon
            name="search"
            class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-dim"
          />
          <input
            v-model="searchInput"
            type="search"
            class="input rounded-full py-2 pl-9 text-footnote"
            placeholder="搜索公告内容或接收人…"
            aria-label="搜索通知"
          />
        </div>
        <button type="submit" class="btn-secondary !px-4 !py-2 text-footnote">搜索</button>
        <button v-if="search" type="button" class="btn-ghost !px-2 text-footnote" @click="clearSearch">
          清除
        </button>
      </form>
    </div>

    <!-- 类型筛选 -->
    <div class="mt-3 flex flex-wrap gap-2" role="group" aria-label="按通知类型筛选">
      <button
        v-for="f in TYPE_FILTERS"
        :key="f.value"
        type="button"
        class="hig-chip"
        :class="type === f.value ? 'is-active' : ''"
        :aria-pressed="type === f.value"
        @click="switchType(f.value)"
      >
        {{ f.label }}
      </button>
    </div>

    <AppStatGrid
      class="mt-5"
      :items="[
        { label: '全部通知', value: fmt(summary.total) },
        { label: '平台公告', value: fmt(summary.system) },
        { label: '未读通知', value: fmt(summary.unread) }
      ]"
      cols="3"
    />

    <div v-if="loading" class="hig-list mt-5">
      <div v-for="i in 6" :key="i" class="flex items-start gap-3 px-4 py-4">
        <div class="h-10 w-10 shrink-0 animate-pulse rounded-full bg-sand"></div>
        <div class="min-w-0 flex-1 space-y-2">
          <div class="h-3.5 w-2/5 animate-pulse rounded bg-sand"></div>
          <div class="h-3 w-3/5 animate-pulse rounded bg-sand"></div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else-if="forbidden"
      icon="lock"
      title="需要管理员权限"
      description="当前账号没有管理台权限，或权限刚被撤销。"
    >
      <router-link to="/" class="btn-primary">返回广场</router-link>
    </EmptyState>

    <EmptyState
      v-else-if="failed"
      icon="triangle-alert"
      title="通知列表加载失败"
      description="服务暂时不可用，请稍后重试。"
    >
      <button class="btn-primary" @click="load">重新加载</button>
    </EmptyState>

    <div v-else-if="notifications.length" class="hig-list mt-5" data-test="admin-notification-list">
      <article
        v-for="n in notifications"
        :key="n.id"
        class="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start"
      >
        <div class="flex min-w-0 flex-1 items-start gap-3">
          <span
            class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
            :class="typeMeta(n.type).tone"
          >
            <AppIcon :name="typeMeta(n.type).icon" class="h-[18px] w-[18px]" />
          </span>

          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="text-subhead font-medium text-ink">{{ typeMeta(n.type).label }}</span>
              <span
                class="rounded-full px-2 py-0.5 text-caption2 font-medium"
                :class="n.isRead ? 'bg-sand text-ink-mid' : 'bg-pine-soft text-pine-deep'"
              >
                {{ n.isRead ? '已读' : '未读' }}
              </span>
              <span v-if="n.recipient" class="text-caption1 text-ink-dim">
                接收人 {{ n.recipient.username }}（#{{ n.recipient.id }}）
              </span>
              <span v-if="n.actor" class="text-caption1 text-ink-dim">
                · 发送者 {{ n.actor.username }}
              </span>
            </div>

            <p
              v-if="n.type === 'system'"
              class="mt-1.5 whitespace-pre-line break-words text-footnote leading-relaxed text-ink"
            >
              {{ n.message }}
            </p>
            <p v-else class="mt-1.5 truncate text-footnote text-ink-mid">
              <span v-if="n.project">「{{ n.project.title }}」</span>
              <span v-else>互动通知</span>
            </p>

            <p class="mt-1.5 text-caption1 text-ink-dim">#{{ n.id }} · {{ relativeTime(n.createdAt) }}</p>
          </div>
        </div>

        <div class="flex shrink-0 justify-end">
          <AdminActionButton
            icon="trash-2"
            label="删除"
            danger
            :disabled="busyId === n.id"
            @click="askDelete(n)"
          />
        </div>
      </article>
    </div>

    <EmptyState
      v-else
      icon="bell"
      :title="emptyTitle"
      :description="emptyDescription"
    >
      <button v-if="hasFilters" class="btn-secondary text-footnote" @click="resetFilters">
        清除筛选
      </button>
    </EmptyState>

    <Pagination
      v-if="!loading && !forbidden && !failed && total > pageSize"
      :page="page"
      :total="total"
      :page-size="pageSize"
      class="mt-6"
      @change="goPage"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  deleteAdminNotification,
  getAdminNotifications,
  sendAdminNotice
} from '@/api/admin'
import { confirm } from '@/composables/useConfirm'
import { toast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import AppIcon from '@/components/AppIcon.vue'
import AppSegmented from '@/components/AppSegmented.vue'
import AppStatGrid from '@/components/AppStatGrid.vue'
import EmptyState from '@/components/EmptyState.vue'
import Pagination from '@/components/Pagination.vue'
import AdminActionButton from '@/components/admin/AdminActionButton.vue'

const PAGE_SIZE = 12

const AUDIENCE_OPTIONS = [
  { value: 'all', label: '全站广播' },
  { value: 'single', label: '指定用户' }
]

const TYPE_META = {
  system: { label: '公告', icon: 'bell', tone: 'bg-amber-soft text-amber-warm' },
  comment: { label: '评论', icon: 'message-circle', tone: 'bg-pine-soft text-pine-deep' },
  reply: { label: '回复', icon: 'message-circle', tone: 'bg-pine-soft text-pine-deep' },
  like: { label: '点赞', icon: 'heart', tone: 'bg-clay/10 text-clay' },
  participate: { label: '参与', icon: 'users', tone: 'bg-green/10 text-green' },
  mention: { label: '提及', icon: 'tag', tone: 'bg-sand text-ink-mid' }
}
const TYPE_FILTERS = [
  { value: '', label: '全部' },
  ...Object.entries(TYPE_META).map(([value, meta]) => ({ value, label: meta.label }))
]
const typeMeta = (type) => TYPE_META[type] || { label: '通知', icon: 'bell', tone: 'bg-sand text-ink-mid' }

const notifications = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const summary = ref({ total: 0, system: 0, unread: 0 })

const type = ref('')
const searchInput = ref('')
const search = ref('')
const busyId = ref(null)

const audience = ref('all')
const message = ref('')
const userId = ref('')
const formError = ref('')
const sending = ref(false)

const loading = ref(true)
const failed = ref(false)
const forbidden = ref(false)

const fmt = (value) => Number(value || 0).toLocaleString('zh-CN')

const hasFilters = computed(() => Boolean(type.value || search.value))
const emptyTitle = computed(() => {
  if (search.value) return `没有匹配「${search.value}」的通知`
  if (type.value) return `没有「${typeMeta(type.value).label}」类型的通知`
  return '还没有通知'
})
const emptyDescription = computed(() => {
  if (search.value) return '换个关键词，或清除筛选查看全部通知。'
  if (type.value) return '换个类型看看，或回到全部通知。'
  return '用户在评论、点赞、参与项目时产生的通知会出现在这里。'
})

const load = async () => {
  loading.value = true
  failed.value = false
  forbidden.value = false
  const params = { page: page.value, pageSize: PAGE_SIZE }
  if (type.value) params.type = type.value
  if (search.value) params.search = search.value
  try {
    const res = await getAdminNotifications(params)
    const data = res.data
    notifications.value = data.notifications
    total.value = data.total
    page.value = data.page
    pageSize.value = data.pageSize
    summary.value = data.summary
  } catch (error) {
    notifications.value = []
    if (error.response?.status === 403) forbidden.value = true
    else failed.value = true
  } finally {
    loading.value = false
  }
}

const refresh = async () => {
  await load()
  if (!notifications.value.length && page.value > 1 && !failed.value && !forbidden.value) {
    page.value -= 1
    await load()
  }
}

const applySearch = () => {
  search.value = searchInput.value.trim()
  page.value = 1
  load()
}

const clearSearch = () => {
  searchInput.value = ''
  search.value = ''
  page.value = 1
  load()
}

const switchType = (value) => {
  if (type.value === value) return
  type.value = value
  page.value = 1
  load()
}

const resetFilters = () => {
  type.value = ''
  search.value = ''
  searchInput.value = ''
  page.value = 1
  load()
}

const goPage = (next) => {
  page.value = next
  load()
}

const setAudience = (value) => {
  audience.value = value
  formError.value = ''
}

const send = async () => {
  const text = message.value.trim()
  formError.value = ''
  if (!text) {
    formError.value = '公告内容不能为空'
    return
  }

  const targetId = Number(userId.value)
  if (audience.value === 'single' && (!Number.isInteger(targetId) || targetId <= 0)) {
    formError.value = '请填写有效的接收用户 ID'
    return
  }

  if (audience.value === 'all') {
    const ok = await confirm({
      title: '发送全站公告？',
      message: '公告会发送给所有正常状态的账号（不含你自己）。发送后可以在下方逐条删除。',
      confirmLabel: '发送'
    })
    if (!ok) return
  }

  sending.value = true
  try {
    const payload = { message: text }
    if (audience.value === 'single') payload.userId = targetId
    const res = await sendAdminNotice(payload)
    toast(`公告已发送给 ${res.data.created} 位用户`)
    message.value = ''
    userId.value = ''
    page.value = 1
    await load()
  } catch (error) {
    formError.value = error.response?.data?.message || '发送失败，请稍后重试'
  } finally {
    sending.value = false
  }
}

const askDelete = async (n) => {
  if (busyId.value) return
  const ok = await confirm({
    title: '删除这条通知？',
    message: '删除后它会立即从收件人的通知列表消失，且无法恢复。',
    confirmLabel: '删除',
    destructive: true
  })
  if (!ok) return

  busyId.value = n.id
  try {
    await deleteAdminNotification(n.id)
    toast('通知已删除')
    await refresh()
  } catch {
    // 错误已由拦截器提示
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

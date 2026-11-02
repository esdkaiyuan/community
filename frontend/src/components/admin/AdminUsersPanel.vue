<template>
  <div data-test="admin-users">
    <!-- 搜索 -->
    <form class="flex w-full max-w-lg items-center gap-2" @submit.prevent="applySearch">
      <div class="relative min-w-0 flex-1">
        <AppIcon
          name="search"
          class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-dim"
        />
        <input
          v-model="searchInput"
          type="search"
          class="input rounded-full py-2 pl-9 text-footnote"
          placeholder="搜索用户名或邮箱…"
          aria-label="搜索用户"
        />
      </div>
      <button type="submit" class="btn-secondary !px-4 !py-2 text-footnote">搜索</button>
      <button v-if="search" type="button" class="btn-ghost !px-2 text-footnote" @click="clearSearch">
        清除
      </button>
    </form>

    <!-- 状态 / 角色筛选 -->
    <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
      <div class="flex flex-wrap items-center gap-2" role="group" aria-label="按账号状态筛选">
        <span class="text-caption2 font-mono uppercase tracking-[0.14em] text-ink-dim">状态</span>
        <button
          v-for="f in STATE_FILTERS"
          :key="f.value"
          type="button"
          class="hig-chip"
          :class="state === f.value ? 'is-active' : ''"
          :aria-pressed="state === f.value"
          @click="switchState(f.value)"
        >
          {{ f.label }}
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2" role="group" aria-label="按角色筛选">
        <span class="text-caption2 font-mono uppercase tracking-[0.14em] text-ink-dim">角色</span>
        <button
          v-for="f in ROLE_FILTERS"
          :key="f.value"
          type="button"
          class="hig-chip"
          :class="role === f.value ? 'is-active' : ''"
          :aria-pressed="role === f.value"
          @click="switchRole(f.value)"
        >
          {{ f.label }}
        </button>
      </div>

      <span class="ml-auto text-caption1 text-ink-dim">
        共 {{ fmt(summary.total) }} 位 · 已停用 {{ fmt(summary.disabled) }} · 管理员 {{ fmt(summary.admins) }}
      </span>
    </div>
    <p class="mt-2 text-caption1 text-ink-dim">
      管理员账号由系统固定且唯一，管理台不提供授予或撤销。
    </p>

    <div v-if="loading" class="hig-list mt-5">
      <div v-for="i in 6" :key="i" class="flex items-center gap-3 px-4 py-4">
        <div class="h-11 w-11 shrink-0 animate-pulse rounded-full bg-sand"></div>
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
      title="用户列表加载失败"
      description="服务暂时不可用，请稍后重试。"
    >
      <button class="btn-primary" @click="load">重新加载</button>
    </EmptyState>

    <div v-else-if="users.length" class="hig-list mt-5" data-test="admin-user-list">
      <article
        v-for="u in users"
        :key="u.id"
        class="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center"
      >
        <div class="flex min-w-0 flex-1 items-center gap-3">
          <span class="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-footnote font-bold text-pine-deep">
            <img v-if="u.avatar" :src="u.avatar" alt="" class="h-full w-full object-cover" />
            <template v-else>{{ (u.username || '友').slice(0, 1).toUpperCase() }}</template>
          </span>

          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-1.5">
              <router-link
                :to="`/user/${u.id}`"
                class="truncate text-headline font-medium text-ink transition-colors hover:text-pine"
              >
                {{ u.username }}
              </router-link>
              <span
                v-if="u.isAdmin"
                class="rounded-full bg-amber-soft px-2 py-0.5 text-caption2 font-medium text-amber-warm"
              >
                管理员
              </span>
              <span
                v-if="!u.status"
                class="rounded-full bg-clay/10 px-2 py-0.5 text-caption2 font-medium text-clay"
              >
                已停用
              </span>
              <span
                v-if="isSelf(u)"
                class="rounded-full bg-sand px-2 py-0.5 text-caption2 font-medium text-ink-mid"
              >
                当前账号
              </span>
            </div>
            <p class="mt-1 truncate text-caption1 text-ink-dim">{{ u.email || '未绑定邮箱' }}</p>
            <p class="mt-1 text-caption1 tabular-nums text-ink-dim">
              #{{ u.id }} · 注册于 {{ relativeTime(u.createdAt) }} ·
              {{ fmt(u.projectCount) }} 个项目 · {{ fmt(u.commentCount) }} 条评论
            </p>
          </div>
        </div>

        <div
          v-if="isSelf(u)"
          class="shrink-0 rounded-10 bg-sand/60 px-3 py-2 text-caption1 text-ink-mid sm:max-w-[13rem]"
        >
          当前登录账号，不能在这里停用。
        </div>
        <div v-else class="flex flex-wrap items-center gap-1.5 sm:shrink-0 sm:justify-end">
          <AdminActionButton
            :icon="u.status ? 'x-circle' : 'check-circle'"
            :label="u.status ? '停用账号' : '恢复账号'"
            :danger="!!u.status"
            :disabled="busyId === u.id"
            @click="toggleStatus(u)"
          />
        </div>
      </article>
    </div>

    <EmptyState v-else icon="users" :title="emptyTitle" :description="emptyDescription">
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
import { getAdminUsers, updateAdminUser } from '@/api/admin'
import { confirm } from '@/composables/useConfirm'
import { toast } from '@/composables/useToast'
import { useUserStore } from '@/store/user'
import { relativeTime } from '@/utils/time'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import Pagination from '@/components/Pagination.vue'
import AdminActionButton from '@/components/admin/AdminActionButton.vue'

const PAGE_SIZE = 10

const STATE_FILTERS = [
  { value: '', label: '全部' },
  { value: 'active', label: '正常' },
  { value: 'disabled', label: '已停用' }
]
const ROLE_FILTERS = [
  { value: '', label: '全部' },
  { value: 'admin', label: '管理员' },
  { value: 'member', label: '成员' }
]

const userStore = useUserStore()

const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const summary = ref({ total: 0, disabled: 0, admins: 0 })

const state = ref('')
const role = ref('')
const searchInput = ref('')
const search = ref('')
const busyId = ref(null)

const loading = ref(true)
const failed = ref(false)
const forbidden = ref(false)

const fmt = (value) => Number(value || 0).toLocaleString('zh-CN')
const isSelf = (u) => Number(u.id) === Number(userStore.userId)

const hasFilters = computed(() => Boolean(state.value || role.value || search.value))
const emptyTitle = computed(() => {
  if (search.value) return `没有匹配「${search.value}」的账号`
  if (state.value === 'disabled') return '没有已停用的账号'
  if (role.value === 'admin') return '没有管理员账号'
  return '没有符合条件的账号'
})
const emptyDescription = computed(() => {
  if (search.value) return '换个用户名或邮箱试试，或清除筛选查看全部账号。'
  if (state.value === 'disabled') return '停用过的账号会出现在这里。'
  if (role.value === 'admin') return '系统中仅保留一个固定管理员账号。'
  return '换个筛选条件试试。'
})

const load = async () => {
  loading.value = true
  failed.value = false
  forbidden.value = false
  const params = { page: page.value, pageSize: PAGE_SIZE }
  if (state.value) params.state = state.value
  if (role.value) params.role = role.value
  if (search.value) params.search = search.value
  try {
    const res = await getAdminUsers(params)
    const data = res.data
    users.value = data.users
    total.value = data.total
    page.value = data.page
    pageSize.value = data.pageSize
    summary.value = data.summary
  } catch (error) {
    users.value = []
    if (error.response?.status === 403) forbidden.value = true
    else failed.value = true
  } finally {
    loading.value = false
  }
}

const refresh = async () => {
  await load()
  if (!users.value.length && page.value > 1 && !failed.value && !forbidden.value) {
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

const switchState = (value) => {
  if (state.value === value) return
  state.value = value
  page.value = 1
  load()
}

const switchRole = (value) => {
  if (role.value === value) return
  role.value = value
  page.value = 1
  load()
}

const resetFilters = () => {
  state.value = ''
  role.value = ''
  search.value = ''
  searchInput.value = ''
  page.value = 1
  load()
}

const goPage = (next) => {
  page.value = next
  load()
}

const toggleStatus = async (u) => {
  if (busyId.value) return
  const disabling = !!u.status
  const ok = await confirm({
    title: disabling ? `停用「${u.username}」？` : `恢复「${u.username}」？`,
    message: disabling
      ? '停用后该账号无法登录，已签发的登录状态也会在下次请求时失效。可以随时恢复。'
      : '恢复后该账号可以重新登录并正常使用。',
    confirmLabel: disabling ? '停用' : '恢复',
    destructive: disabling
  })
  if (!ok) return

  busyId.value = u.id
  try {
    await updateAdminUser(u.id, { status: disabling ? 0 : 1 })
    toast(disabling ? '账号已停用' : '账号已恢复')
    await refresh()
  } catch {
    // 错误已由拦截器提示
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

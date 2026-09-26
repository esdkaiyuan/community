<template>
  <header class="sticky top-0 z-50 border-b border-line bg-[color:var(--glass-nav)] backdrop-blur-xl backdrop-saturate-150">
    <div class="mx-auto flex h-12 max-w-7xl items-center gap-4 px-4 sm:px-6">
      <!-- Logo -->
      <router-link to="/" class="flex shrink-0 items-center gap-2">
        <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-pine">
          <svg viewBox="0 0 64 64" class="h-4 w-4" aria-hidden="true">
            <path d="M32 46c0-9 0-14 0-19" stroke="white" stroke-width="4" stroke-linecap="round" fill="none" />
            <path d="M32 30c0-7 5-11.5 11.5-11.5C43.5 25.5 38.5 30 32 30z" fill="rgba(255,255,255,0.7)" />
            <path d="M32 36c0-5.6-4.2-9.5-9.5-9.5 0 5.6 4.2 9.5 9.5 9.5z" fill="white" />
          </svg>
        </span>
        <span class="text-base font-semibold tracking-tight text-ink">共创社区</span>
      </router-link>

      <!-- 搜索框 -->
      <form class="mx-auto hidden max-w-md flex-1 md:block" @submit.prevent="handleSearch">
        <div class="relative">
          <svg
            class="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-dim"
            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索感兴趣的项目…"
            class="input rounded-full border-transparent bg-sand py-1.5 text-sm focus:border-pine focus:bg-cream"
          />
        </div>
      </form>

      <!-- 右侧操作区 -->
      <div class="ml-auto flex shrink-0 items-center gap-2 md:ml-0">
        <router-link v-if="userStore.isLoggedIn" to="/publish" class="btn-primary !px-4 !py-2">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span class="hidden sm:inline">发布项目</span>
          <span class="sm:hidden">发布</span>
        </router-link>

        <!-- 通知铃铛（已登录） -->
        <div v-if="userStore.isLoggedIn" ref="notifRef" class="relative">
          <button
            class="relative flex h-9 w-9 items-center justify-center rounded-full text-ink transition-colors hover:bg-sand"
            title="通知"
            @click="toggleNotif"
          >
            <AppIcon name="bell" class="h-[18px] w-[18px]" />
            <span
              v-if="unread > 0"
              class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#FF3B30] px-1 text-[10px] font-semibold tabular-nums text-white"
            >
              {{ unread > 99 ? '99+' : unread }}
            </span>
          </button>

          <transition name="menu">
            <div
              v-if="notifOpen"
              class="absolute right-0 top-full mt-2 w-80 overflow-hidden rounded-xl2 border border-[color:var(--glass-border)] bg-[color:var(--glass-menu)] shadow-pop backdrop-blur-xl backdrop-saturate-150"
            >
              <div class="flex items-center justify-between border-b border-line px-4 py-3">
                <span class="text-sm font-semibold text-ink">通知</span>
                <button
                  v-if="unread > 0"
                  class="text-xs text-pine transition-colors hover:text-pine-deep"
                  @click="markAllRead"
                >
                  全部标为已读
                </button>
              </div>

              <div class="max-h-80 overflow-y-auto">
                <template v-if="notifications.length">
                  <button
                    v-for="n in notifications"
                    :key="n.id"
                    class="flex w-full items-start gap-2.5 border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-sand"
                    :class="n.isRead ? '' : 'bg-pine-soft/40'"
                    @click="openNotification(n)"
                  >
                    <span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-xs font-bold text-pine-deep">
                      <img v-if="n.actor?.avatar" :src="n.actor.avatar" alt="" class="h-full w-full object-cover" />
                      <template v-else>{{ (n.actor?.username || '友').slice(0, 1).toUpperCase() }}</template>
                    </span>
                    <span class="min-w-0 flex-1">
                      <span class="block text-[13px] leading-snug text-ink">
                        <span class="font-medium">{{ n.actor?.username || '有人' }}</span>
                        {{ typeText(n.type) }}
                        <span class="text-ink-mid">「{{ n.project?.title || '项目' }}」</span>
                      </span>
                      <span v-if="n.commentPreview" class="mt-0.5 block truncate text-xs text-ink-dim">{{ n.commentPreview }}</span>
                      <span class="mt-1 block text-[11px] text-ink-dim">{{ relativeTime(n.createdAt) }}</span>
                    </span>
                    <span v-if="!n.isRead" class="mt-2 h-2 w-2 shrink-0 rounded-full bg-pine"></span>
                  </button>
                </template>
                <div v-else class="flex flex-col items-center gap-1.5 px-4 py-10 text-center">
                  <AppIcon name="bell" class="h-7 w-7 text-ink-dim/50" :stroke-width="1.5" />
                  <p class="text-sm text-ink-mid">暂无通知</p>
                  <p class="text-xs text-ink-dim">有人评论或点赞你的项目时会在这里提醒你。</p>
                </div>
              </div>
            </div>
          </transition>
        </div>

        <!-- 已登录：用户菜单 -->
        <div v-if="userStore.isLoggedIn" ref="menuRef" class="relative">
          <button
            class="flex items-center gap-2 rounded-full border border-line bg-cream py-1.5 pl-1.5 pr-3 transition-colors hover:border-pine"
            @click="menuOpen = !menuOpen"
          >
            <span class="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-xs font-bold text-pine-deep">
              <img v-if="avatar" :src="avatar" alt="" class="h-full w-full object-cover" />
              <template v-else>{{ initial }}</template>
            </span>
            <span class="max-w-[6rem] truncate text-sm text-ink">{{ userStore.username }}</span>
            <svg class="h-3.5 w-3.5 text-ink-dim transition-transform" :class="{ 'rotate-180': menuOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          <transition name="menu">
            <div
              v-if="menuOpen"
              class="absolute right-0 top-full mt-2 w-44 overflow-hidden rounded-xl border border-[color:var(--glass-border)] bg-[color:var(--glass-menu)] py-1.5 shadow-pop backdrop-blur-xl backdrop-saturate-150"
            >
              <router-link to="/profile" class="menu-item" @click="menuOpen = false">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
                </svg>
                个人中心
              </router-link>
              <router-link to="/publish" class="menu-item" @click="menuOpen = false">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                发布项目
              </router-link>
              <div class="mx-3 my-1 border-t border-line"></div>
              <button class="menu-item w-full text-clay" @click="handleLogout">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
                退出登录
              </button>
            </div>
          </transition>
        </div>

        <!-- 未登录 -->
        <template v-else>
          <router-link to="/login" class="btn-ghost">登录</router-link>
          <router-link to="/register" class="btn-primary !px-4 !py-2">注册</router-link>
        </template>
      </div>
    </div>

    <!-- 移动端搜索 -->
    <form class="border-t border-line px-4 py-2 md:hidden" @submit.prevent="handleSearch">
      <input v-model="keyword" type="search" placeholder="搜索感兴趣的项目…" class="input rounded-full py-2" />
    </form>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { toast } from '@/composables/useToast'
import { getNotifications, getUnreadCount, markRead } from '@/api/notification'
import { relativeTime } from '@/utils/time'
import AppIcon from '@/components/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const keyword = ref(route.query.search || '')
const menuOpen = ref(false)
const menuRef = ref(null)

// 通知状态
const notifOpen = ref(false)
const notifRef = ref(null)
const notifications = ref([])
const unread = ref(0)
let pollTimer = null

const avatar = computed(() => userStore.userInfo?.avatar || '')
const initial = computed(() => (userStore.username || '友').slice(0, 1).toUpperCase())

const typeText = (type) =>
  ({ comment: '评论了你的项目', reply: '回复了你在', like: '赞了你在' }[type] || '与你互动于')

const fetchUnread = async () => {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getUnreadCount()
    unread.value = res.data.unread
  } catch {
    // 静默失败：轮询场景不打扰用户
  }
}

const fetchNotifications = async () => {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getNotifications({ page: 1, pageSize: 15 })
    notifications.value = res.data.notifications
    unread.value = res.data.unread
  } catch {
    toast('通知加载失败', 'error')
  }
}

const toggleNotif = () => {
  notifOpen.value = !notifOpen.value
  if (notifOpen.value) fetchNotifications()
}

const openNotification = async (n) => {
  notifOpen.value = false
  if (!n.isRead) {
    n.isRead = true
    unread.value = Math.max(0, unread.value - 1)
    markRead({ ids: [n.id] }).catch(() => {})
  }
  router.push({ path: `/project/${n.project?.id}`, hash: '#comments' })
}

const markAllRead = () => {
  markRead({ all: true })
    .then(() => {
      notifications.value.forEach((n) => (n.isRead = true))
      unread.value = 0
    })
    .catch(() => toast('操作失败，请稍后再试', 'error'))
}

// 登录后轮询未读数；登出时清零
watch(
  () => userStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      fetchUnread()
      pollTimer = setInterval(fetchUnread, 60_000)
    } else {
      clearInterval(pollTimer)
      pollTimer = null
      unread.value = 0
      notifications.value = []
      notifOpen.value = false
    }
  },
  { immediate: true }
)

// 路由切换时顺手刷新未读数
watch(() => route.path, fetchUnread)

// 路由上的搜索词变化时同步输入框（例如清除搜索）
watch(
  () => route.query.search,
  (val) => {
    keyword.value = val || ''
  }
)

const handleSearch = () => {
  const search = keyword.value.trim()
  router.push({ path: '/', query: search ? { search } : {} })
}

const handleLogout = () => {
  menuOpen.value = false
  userStore.logout()
  toast('已退出登录', 'info')
  if (route.meta.requiresAuth) router.push('/')
}

// 点击外部关闭菜单与通知面板
const onClickOutside = (e) => {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
  if (notifRef.value && !notifRef.value.contains(e.target)) notifOpen.value = false
}
onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.menu-item {
  @apply flex items-center gap-2.5 px-4 py-2 text-sm text-ink transition-colors hover:bg-sand;
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

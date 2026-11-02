<template>
  <!--
    赛博手绘式页头（HIG 结构：56px 高度 / 44px 热区 / 毛玻璃材质）

    手写体字标 + 墨线手绘方块、平级导航 + 电光青手绘下划线、
    暖纸面胶囊搜索。发丝线底边 + 毛玻璃，内容滚过时透出模糊底色。

    ⚠️ 三处被端到端脚本按值钉死，改动即撞红：
      · button[aria-label='通知']   视觉 32×32，热区靠 ::after -inset-1.5 撑到 44×44
      · button[aria-label='账号菜单'] 热区上探 3px（::after -inset-0.5 等效）
      · [data-test='unread-badge']  背景必须是 clay（深色 #FF453A / 浅色 #D70015）
  -->
  <header class="sticky top-0 z-50 border-b border-line/70 bg-[color:var(--glass-nav)] backdrop-blur-xl backdrop-saturate-150">
    <div class="site-shell flex h-14 items-center gap-3">
      <!-- 品牌：手写体字标 + 墨线手绘方块（电光青错位影） -->
      <router-link to="/" class="flex shrink-0 items-center gap-2.5" aria-label="共创社区首页">
        <span class="sketch-mark flex h-8 w-8 items-center justify-center">
          <svg viewBox="0 0 64 64" class="h-[18px] w-[18px]" aria-hidden="true">
            <path d="M32 46c0-9 0-14 0-19" stroke="rgb(var(--c-ink))" stroke-width="4" stroke-linecap="round" fill="none" />
            <path d="M32 30c0-7 5-11.5 11.5-11.5C43.5 25.5 38.5 30 32 30z" fill="rgb(var(--c-pine) / 0.55)" />
            <path d="M32 36c0-5.6-4.2-9.5-9.5-9.5 0 5.6 4.2 9.5 9.5 9.5z" fill="rgb(var(--c-pine))" />
          </svg>
        </span>
        <span class="flex flex-col leading-none">
          <span class="font-brand text-[17px] font-semibold tracking-tight text-ink">共创社区</span>
          <span class="mt-1 hidden font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-ink-dim sm:block">Co-Creation</span>
        </span>
      </router-link>

      <!-- 主导航：细线 + 电光青手绘下划线，桌面端才出现 -->
      <nav class="ml-3 hidden items-center gap-5 lg:flex" aria-label="主导航">
        <router-link
          v-for="item in visibleNav"
          :key="item.to"
          :to="item.to"
          class="relative py-4 text-footnote font-medium transition-colors"
          :class="isActive(item) ? 'text-ink' : 'text-ink-mid hover:text-ink'"
        >
          {{ item.label }}
          <span v-if="isActive(item)" class="sketch-rule absolute inset-x-0 bottom-0 text-pine"></span>
        </router-link>
      </nav>

      <!-- 搜索框：暖灰胶囊，聚焦时恢复纸面与电光青边框 -->
      <form class="mx-auto hidden max-w-sm flex-1 md:block" @submit.prevent="handleSearch">
        <div class="relative">
          <svg
            class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-dim"
            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索感兴趣的项目…"
            class="input rounded-full border-transparent bg-sand/70 py-2 pl-9 text-footnote focus:border-line-strong focus:bg-cream"
            aria-label="搜索项目"
          />
        </div>
      </form>

      <!-- 右侧操作区：窄屏必须能收缩，否则用户名一长就把整个视口撑出横向滚动条 -->
      <div class="ml-auto flex min-w-0 items-center gap-2 md:ml-0">
        <router-link v-if="userStore.isLoggedIn" to="/publish" class="btn-primary shrink-0 !px-4 !py-1.5">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span class="hidden sm:inline">发布项目</span>
          <span class="sm:hidden">发布</span>
        </router-link>

        <!-- 通知铃铛（已登录）
             视觉 32×32，靠 ::after -inset-1.5 把命中区撑到 44×44（最小可点区域）。
             56px 页头里 32px 控件居中后上下各余 12px，热区外扩 6px 仍在视口内，
             端到端脚本「盒上方 5px 真实命中」的探针才取得到元素。 -->
        <div v-if="userStore.isLoggedIn" ref="notifRef" class="relative shrink-0">
          <button
            class="relative flex h-8 w-8 items-center justify-center rounded-full text-ink transition-colors after:absolute after:-inset-1.5 after:rounded-full after:content-[''] hover:bg-sand"
            title="通知"
            aria-label="通知"
            @click="toggleNotif"
          >
            <AppIcon name="bell" class="h-[18px] w-[18px]" />
            <span
              v-if="unread > 0"
              data-test="unread-badge"
              class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-clay px-1 text-caption2 font-semibold tabular-nums text-white"
            >
              {{ unread > 99 ? '99+' : unread }}
            </span>
          </button>

          <transition name="menu">
            <div
              v-if="notifOpen"
              data-test="notif-panel"
              class="absolute right-0 top-full mt-2 w-80 overflow-hidden rounded-14 border border-[color:var(--glass-border)] bg-[color:var(--glass-menu)] shadow-pop backdrop-blur-xl backdrop-saturate-150"
            >
              <div class="flex items-center justify-between border-b border-line px-4 py-2.5">
                <span class="text-headline font-semibold text-ink">通知</span>
                <button
                  v-if="unread > 0"
                  class="text-footnote text-pine transition-colors hover:text-pine-deep"
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
                    data-test="notif-item"
                    class="flex w-full items-start gap-2.5 border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-sand"
                    :class="n.isRead ? '' : 'bg-pine-soft/40'"
                    @click="openNotification(n)"
                  >
                    <span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-caption1 font-bold text-pine-deep">
                      <img v-if="n.actor?.avatar" :src="n.actor.avatar" alt="" class="h-full w-full object-cover" />
                      <template v-else>{{ (n.actor?.username || '友').slice(0, 1).toUpperCase() }}</template>
                    </span>
                    <span class="min-w-0 flex-1">
                      <span class="block text-footnote leading-snug text-ink">
                        <span class="font-medium">{{ n.actor?.username || '有人' }}</span>
                        {{ notificationText(n.type) }}
                        <span class="text-ink-mid">「{{ n.project?.title || '项目' }}」</span>
                      </span>
                      <span v-if="n.commentPreview" class="mt-0.5 block truncate text-caption1 text-ink-dim">{{ n.commentPreview }}</span>
                      <span class="mt-1 block text-caption2 text-ink-dim">{{ relativeTime(n.createdAt) }}</span>
                    </span>
                    <span v-if="!n.isRead" class="mt-2 h-2 w-2 shrink-0 rounded-full bg-pine"></span>
                  </button>
                </template>
                <div v-else class="flex flex-col items-center gap-1.5 px-4 py-10 text-center">
                  <AppIcon name="bell" class="h-7 w-7 text-ink-dim/50" :stroke-width="1.5" />
                  <p class="text-subhead text-ink-mid">暂无通知</p>
                  <p class="text-caption1 text-ink-dim">有人评论、点赞或参与你的项目时会在这里提醒你。</p>
                </div>
              </div>

              <router-link
                to="/notifications"
                class="block border-t border-line px-4 py-2.5 text-center text-caption1 font-medium text-pine transition-colors hover:bg-sand"
                @click="notifOpen = false"
              >
                查看全部通知
              </router-link>
            </div>
          </transition>
        </div>

        <!-- 已登录：用户菜单（窄屏只留头像，用户名 / 箭头从 sm 起显示）
             内边距 py-1：控件整体约 44px，在 56px 页头里居中后热区不会顶到视口外，
             与铃铛是同一个几何约束。 -->
        <div v-if="userStore.isLoggedIn" ref="menuRef" class="relative shrink-0">
          <button
            class="relative flex items-center gap-2 rounded-full border border-line bg-cream py-1 pl-1.5 pr-1.5 transition-colors after:absolute after:-inset-1 after:rounded-full after:content-[''] hover:border-pine sm:pr-3"
            aria-label="账号菜单"
            :aria-expanded="menuOpen"
            @click="menuOpen = !menuOpen"
          >
            <span class="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-caption1 font-bold text-pine-deep">
              <img v-if="avatar" :src="avatar" alt="" class="h-full w-full object-cover" />
              <template v-else>{{ initial }}</template>
            </span>
            <span class="hidden max-w-[6rem] truncate text-footnote text-ink sm:inline">{{ userStore.username }}</span>
            <svg class="hidden h-3.5 w-3.5 text-ink-dim transition-transform sm:block" :class="{ 'rotate-180': menuOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          <transition name="menu">
            <div
              v-if="menuOpen"
              class="absolute right-0 top-full mt-2 w-44 overflow-hidden rounded-10 border border-[color:var(--glass-border)] bg-[color:var(--glass-menu)] py-1.5 shadow-pop backdrop-blur-xl backdrop-saturate-150"
            >
              <router-link to="/profile" class="menu-item" @click="menuOpen = false">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
                </svg>
                个人中心
              </router-link>
              <router-link to="/security" class="menu-item" @click="menuOpen = false">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
                  <path d="m9 12 2 2 4-4" />
                </svg>
                账号安全
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
          <router-link to="/register" class="btn-primary !px-4 !py-1.5">注册</router-link>
        </template>
      </div>
    </div>

    <!-- 移动端搜索：导航栏放不下时下移一行，而不是把图标挤没 -->
    <form class="border-t border-line px-4 py-2 md:hidden" @submit.prevent="handleSearch">
      <input v-model="keyword" type="search" placeholder="搜索感兴趣的项目…" class="input rounded-full border-transparent bg-sand/70 py-2" aria-label="搜索项目" />
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
import { notificationText, notificationTarget } from '@/utils/notification'
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

// 主导航：与主站一样只放平级入口；账号安全收进账号菜单，避免导航过密
const NAV = [
  { to: '/', label: '广场', match: (path) => path === '/' },
  { to: '/publish', label: '发布', match: (path) => path === '/publish' || path.endsWith('/edit'), auth: true },
  { to: '/notifications', label: '通知', match: (path) => path === '/notifications', auth: true },
  {
    to: '/profile',
    label: '个人中心',
    match: (path) => path === '/profile' || path.startsWith('/user/'),
    auth: true
  }
]
const visibleNav = computed(() => NAV.filter((item) => !item.auth || userStore.isLoggedIn))
const isActive = (item) => item.match(route.path)

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
  // 窄屏放不下 320px 的通知气泡（锚在铃铛上会从视口左侧溢出），
  // 直接进通知页——完整列表本来就在那里，小屏上比浮层更好用
  if (window.matchMedia('(max-width: 767px)').matches) {
    router.push('/notifications')
    return
  }
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
  router.push(notificationTarget(n))
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
  @apply flex items-center gap-2.5 px-4 py-2 text-footnote text-ink transition-colors hover:bg-sand;
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1), transform 0.15s cubic-bezier(0.22, 1, 0.36, 1);
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

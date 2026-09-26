<template>
  <header class="sticky top-0 z-50 border-b border-line bg-white/72 backdrop-blur-xl backdrop-saturate-150">
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
              class="absolute right-0 top-full mt-2 w-44 overflow-hidden rounded-xl border border-white/60 bg-white/85 py-1.5 shadow-pop backdrop-blur-xl backdrop-saturate-150"
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

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const keyword = ref(route.query.search || '')
const menuOpen = ref(false)
const menuRef = ref(null)

const avatar = computed(() => userStore.userInfo?.avatar || '')
const initial = computed(() => (userStore.username || '友').slice(0, 1).toUpperCase())

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

// 点击外部关闭菜单
const onClickOutside = (e) => {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
}
onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
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

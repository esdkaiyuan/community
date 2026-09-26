<template>
  <div class="flex min-h-screen flex-col">
    <AppHeader />

    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AppFooter />
    <ToastHost />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import ToastHost from '@/components/ToastHost.vue'

// 启动时若已有 token，拉一次用户信息校验有效性（失效由拦截器统一登出）
const userStore = useUserStore()
onMounted(() => {
  if (userStore.isLoggedIn) {
    userStore.fetchMe().catch(() => {})
  }
})
</script>

<style>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
  .page-enter-from,
  .page-leave-to {
    transform: none;
  }
}
</style>

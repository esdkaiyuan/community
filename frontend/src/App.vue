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
    <!-- 全局确认框（替代 window.confirm）：由 composables/useConfirm 驱动 -->
    <AppConfirmHost />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import ToastHost from '@/components/ToastHost.vue'
import AppConfirmHost from '@/components/AppConfirmHost.vue'

// 启动时若已有 token，拉一次用户信息校验有效性（失效由拦截器统一登出）
const userStore = useUserStore()
onMounted(() => {
  if (userStore.isLoggedIn) {
    userStore.fetchMe().catch(() => {})
  }
})
</script>

<style>
/* 页面转场：HIG 曲线，250ms 进出场（系统级导航的默认手感） */
.page-enter-active,
.page-leave-active {
  transition:
    opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
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

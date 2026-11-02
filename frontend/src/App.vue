<template>
  <div class="flex min-h-screen flex-col">
    <!-- 登录 / 注册 / 找回密码是独立整屏页面：不渲染页头与页脚，画面里只留表单窗口 -->
    <AppHeader v-if="!isAuthLayout" />

    <!-- 小屏顶对齐：三张卡片内容长短不同，垂直居中会让切换时卡片上沿上下跳；
         桌面端高度已统一，仍保持垂直居中。 -->
    <main :class="isAuthLayout ? 'auth-stage flex flex-1 items-start justify-center md:items-center' : 'flex-1'">
      <router-view v-slot="{ Component }">
        <!-- 登录 / 注册 / 找回密码之间切换必须瞬时完成：不做淡出淡入，
             否则旧卡片先消失、新卡片再出现，中间会闪一下空白，看起来像窗口在抽动。 -->
        <component :is="Component" v-if="isAuthLayout" />
        <transition v-else name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AppFooter v-if="!isAuthLayout" />
    <ToastHost />
    <!-- 全局确认框（替代 window.confirm）：由 composables/useConfirm 驱动 -->
    <AppConfirmHost />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/store/user'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import ToastHost from '@/components/ToastHost.vue'
import AppConfirmHost from '@/components/AppConfirmHost.vue'

const route = useRoute()
const isAuthLayout = computed(() => Boolean(route.meta.authLayout))

// 启动时若已有 token，拉一次用户信息校验有效性（失效由拦截器统一登出）
const userStore = useUserStore()
onMounted(() => {
  if (userStore.isLoggedIn) {
    userStore.fetchMe().catch(() => {})
  }
})
</script>

<style>
/* 页面转场只做透明度：路由切换时元素不会位移或拉伸。
   认证页之间不参与转场（见模板），所以这里只保留普通页面的规则。 */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
}
</style>

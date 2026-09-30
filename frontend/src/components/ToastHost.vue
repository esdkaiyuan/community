<template>
  <Teleport to="body">
    <!-- 位置：右上角（macOS/iOS 通知位）。刻意避开 sticky 导航栏（h-49px），
         否则提示会压在搜索框上；小屏改为顶部通栏，留出同样的间隔 -->
    <div
      class="pointer-events-none fixed inset-x-3 top-[60px] z-[120] flex flex-col gap-2.5 sm:inset-x-auto sm:right-4 sm:top-[68px] sm:w-[380px]"
      role="region"
      aria-label="提示消息"
    >
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          :data-test="`toast-${t.type}`"
          :role="t.type === 'error' ? 'alert' : 'status'"
          class="toast-card pointer-events-auto flex items-start gap-3 rounded-2xl border border-line/70 bg-[color:var(--glass-toast)] px-4 py-3 shadow-toast backdrop-blur-2xl backdrop-saturate-150"
          @mouseenter="pause(t.id)"
          @mouseleave="resume(t.id)"
        >
          <span
            class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
            :class="tintMap[t.type] || tintMap.info"
          >
            <AppIcon :name="iconMap[t.type] || iconMap.info" class="h-3.5 w-3.5" :stroke-width="2.2" />
          </span>

          <p class="min-w-0 flex-1 break-words text-[13.5px] leading-relaxed text-ink">{{ t.message }}</p>

          <button
            type="button"
            class="-mr-1 -mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-ink-dim transition-colors hover:bg-sand hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pine/40"
            aria-label="关闭提示"
            @click="dismiss(t.id)"
          >
            <AppIcon name="x" class="h-3.5 w-3.5" :stroke-width="2.2" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { dismiss, pause, resume, toasts } from '@/composables/useToast'
import AppIcon from '@/components/AppIcon.vue'

const iconMap = {
  success: 'check-circle',
  error: 'x-circle',
  info: 'info'
}

// Apple 系统色：绿 green（#34C759/#30D158 随主题）/ 红 clay（#D70015/#FF453A）/ 蓝 pine
// 一律走设计令牌，不写死 hex——深色模式下自动翻转（写死值在第 17 轮深色走查中被抓）
// 图标用「同色淡底 + 同色描线」，比纯色图标更容易一眼分辨类型，也不刺眼
const tintMap = {
  success: 'bg-green/10 text-green',
  error: 'bg-clay/10 text-clay',
  info: 'bg-pine/10 text-pine'
}
</script>

<style scoped>
/* 进场：从右侧滑入 + 微缩（与 macOS 通知一致的方向感），退场反向并淡出 */
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(14px) scale(0.97);
}
/* 堆叠重排时让其它卡片平滑让位，而不是瞬移 */
.toast-move {
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active,
  .toast-move {
    transition: none;
  }
}
</style>

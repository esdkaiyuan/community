<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed inset-x-0 top-5 z-[100] flex flex-col items-center gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-center gap-2.5 rounded-2xl border border-line bg-white/95 px-4 py-2.5 text-sm text-ink shadow-pop backdrop-blur animate-toast-in"
        >
          <AppIcon :name="iconMap[t.type] || iconMap.info" class="h-4.5 w-4.5 shrink-0" :class="colorMap[t.type] || colorMap.info" />
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { toasts } from '@/composables/useToast'
import AppIcon from '@/components/AppIcon.vue'

const iconMap = {
  success: 'check-circle',
  error: 'x-circle',
  info: 'info'
}

// Apple 系统色：绿 #34C759 / 红 #E30000 / 蓝 #0071E3
const colorMap = {
  success: 'text-[#34C759]',
  error: 'text-[#E30000]',
  info: 'text-pine'
}
</script>

<style scoped>
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

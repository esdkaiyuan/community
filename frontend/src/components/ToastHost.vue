<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed inset-x-0 top-5 z-[100] flex flex-col items-center gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-center gap-2 rounded-full border px-4 py-2 text-sm shadow-pop animate-toast-in"
          :class="styleMap[t.type] || styleMap.info"
        >
          <span class="text-base leading-none">{{ iconMap[t.type] || iconMap.info }}</span>
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { toasts } from '@/composables/useToast'

const styleMap = {
  success: 'border-pine/30 bg-pine-tint text-pine-deep',
  error: 'border-clay/30 bg-[#FBEBE7] text-clay',
  info: 'border-line-strong bg-cream text-ink'
}

const iconMap = {
  success: '✓',
  error: '✕',
  info: 'ℹ'
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

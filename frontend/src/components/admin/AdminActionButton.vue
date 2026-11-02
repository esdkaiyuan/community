<template>
  <!-- 管理台行内操作按钮：移动端 44px 热区，桌面端收紧到 36px -->
  <button
    type="button"
    class="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[8px] px-2.5 text-footnote font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45 sm:min-h-9"
    :class="danger ? 'text-clay hover:bg-clay/10' : 'text-ink-mid hover:bg-sand hover:text-ink'"
    :disabled="disabled"
    @click="emit('click')"
  >
    <AppIcon :name="icon" class="h-4 w-4 shrink-0" />
    <span>{{ label }}</span>
  </button>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  danger: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['click'])
</script>

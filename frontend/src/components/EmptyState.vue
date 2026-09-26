<template>
  <div class="flex flex-col items-center justify-center py-20 text-center">
    <div class="flex h-16 w-16 items-center justify-center rounded-full bg-cream text-ink-dim shadow-card">
      <AppIcon :name="icon" class="h-7 w-7" />
    </div>
    <p class="mt-4 text-base font-medium text-ink">{{ title }}</p>
    <p v-if="description" class="mt-1.5 max-w-xs text-sm text-ink-mid">{{ description }}</p>
    <div v-if="$slots.default" class="mt-5">
      <slot />
    </div>
  </div>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'

defineProps({
  icon: { type: String, default: 'sprout' },
  title: { type: String, required: true },
  description: { type: String, default: '' }
})
</script>

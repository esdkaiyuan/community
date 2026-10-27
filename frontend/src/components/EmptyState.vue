<template>
  <!--
    Apple HIG 空状态（Empty State）

    「这里还没有内容」的那一屏。HIG 的要求是把它当成一个正常的页面状态来设计，
    而不是塞一句灰字了事：图形（图标）+ 一句结论（标题）+ 一句解释（说明）+ 出路（操作）。

    层级靠字号与颜色拉开，不用卡片框住——空状态不该看起来像一个待填充的容器。
  -->
  <div class="flex flex-col items-center justify-center py-20 text-center">
    <div class="flex h-16 w-16 items-center justify-center rounded-full bg-cream text-ink-dim shadow-card">
      <AppIcon :name="icon" class="h-7 w-7" :stroke-width="1.5" />
    </div>
    <p class="mt-4 text-title3 font-semibold text-ink">{{ title }}</p>
    <p v-if="description" class="mt-1.5 max-w-xs text-footnote leading-relaxed text-ink-mid">
      {{ description }}
    </p>
    <div v-if="$slots.default" class="mt-6">
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

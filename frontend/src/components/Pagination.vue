<template>
  <nav v-if="totalPages > 1" class="flex items-center justify-center gap-1.5">
    <button class="page-btn" :disabled="page <= 1" @click="go(page - 1)" aria-label="上一页">
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <template v-for="(item, i) in pageItems" :key="i">
      <span v-if="item === '…'" class="px-1.5 text-sm text-ink-dim">…</span>
      <button
        v-else
        class="page-btn"
        :class="{ 'is-active': item === page }"
        @click="go(item)"
      >
        {{ item }}
      </button>
    </template>

    <button class="page-btn" :disabled="page >= totalPages" @click="go(page + 1)" aria-label="下一页">
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="m9 6 6 6-6 6" />
      </svg>
    </button>
  </nav>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  total: { type: Number, required: true },
  pageSize: { type: Number, default: 12 }
})

const emit = defineEmits(['change'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

// 页码折叠：1 … p-1 p p+1 … n
const pageItems = computed(() => {
  const n = totalPages.value
  const p = props.page
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1)

  const items = [1]
  if (p > 3) items.push('…')
  for (let i = Math.max(2, p - 1); i <= Math.min(n - 1, p + 1); i++) items.push(i)
  if (p < n - 2) items.push('…')
  items.push(n)
  return items
})

const go = (p) => {
  if (p >= 1 && p <= totalPages.value && p !== props.page) emit('change', p)
}
</script>

<style scoped>
.page-btn {
  @apply flex h-9 min-w-[2.25rem] items-center justify-center rounded-lg border border-line bg-cream px-2 text-sm text-ink-mid transition-colors hover:border-pine hover:text-pine disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-line disabled:hover:text-ink-mid;
}
.page-btn.is-active {
  @apply border-pine bg-pine text-white hover:text-white;
}
</style>

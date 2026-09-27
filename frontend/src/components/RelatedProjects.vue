<template>
  <!-- 没有线索（无共同标签也无同分类）时整块不渲染：宁可不放，也不拿无关内容冒充推荐 -->
  <section v-if="list.length" v-reveal class="mt-12" data-test="related-section">
    <div class="mb-5 flex items-center justify-between">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-ink">
        <span class="h-4 w-1 rounded-full bg-pine"></span>
        相关项目
      </h2>
      <router-link
        to="/"
        class="inline-flex items-center gap-1 text-sm text-pine-deep transition-opacity hover:opacity-70"
      >
        去广场逛逛
        <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 6 6 6-6 6" />
        </svg>
      </router-link>
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-3" data-test="related-list">
      <router-link
        v-for="p in list"
        :key="p.id"
        :to="`/project/${p.id}`"
        data-test="related-item"
        class="card group overflow-hidden !p-0 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
      >
        <div class="relative aspect-[16/9] overflow-hidden">
          <img
            v-if="p.coverImage && !isFailed(p.id)"
            :src="p.coverImage"
            :alt="p.title"
            loading="lazy"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            @error="markFailed(p.id)"
          />
          <div
            v-else
            class="flex h-full w-full items-center justify-center"
            :style="{ background: coverPalette(p.id).bg }"
          >
            <span class="select-none font-display text-3xl font-bold opacity-90" :style="{ color: coverPalette(p.id).fg }">
              {{ p.title?.slice(0, 1) || '创' }}
            </span>
          </div>
        </div>

        <div class="p-4">
          <h3 class="truncate text-[15px] font-semibold text-ink transition-colors group-hover:text-pine">
            {{ p.title }}
          </h3>
          <!-- 把推荐依据写在脸上：共同标签 / 同分类 -->
          <p class="mt-1.5 flex items-center gap-1 truncate text-xs text-ink-dim" :title="reasonText(p)">
            <AppIcon name="tag" class="h-3 w-3 shrink-0" />
            {{ reasonText(p) }}
          </p>
        </div>
      </router-link>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getRelatedProjects } from '@/api/project'
import { coverPalette } from '@/utils/placeholder'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  projectId: { type: [Number, String], required: true },
  limit: { type: Number, default: 3 }
})

const list = ref([])
const failed = ref(new Set())

const isFailed = (id) => failed.value.has(id)
const markFailed = (id) => failed.value.add(id)

// 推荐依据优先用共同标签（比同分类更能说明「为什么是它」）
const reasonText = (p) => {
  const reason = p.relatedReason || {}
  const parts = []
  if (reason.sharedTags?.length) parts.push(`共同标签 ${reason.sharedTags.map((t) => `#${t}`).join(' ')}`)
  if (reason.sameCategory) parts.push(`同分类 · ${p.categoryName}`)
  return parts.join(' · ')
}

const fetchRelated = async () => {
  if (!props.projectId) return
  try {
    const res = await getRelatedProjects(props.projectId, { limit: props.limit })
    list.value = res.data || []
  } catch {
    list.value = [] // 推荐失败不该影响详情页主体，静默退化
  }
}

// 详情页在同一个路由里切换项目（看完了顺便看下一个），要跟着重拉
watch(() => props.projectId, fetchRelated, { immediate: true })
</script>

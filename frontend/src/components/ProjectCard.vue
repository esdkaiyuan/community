<template>
  <router-link
    :to="`/project/${project.id}`"
    class="card group block overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:border-line-strong hover:shadow-card-hover"
  >
    <!-- 封面 -->
    <div class="relative aspect-[16/9] overflow-hidden">
      <img
        v-if="project.coverImage && !imgFailed"
        :src="project.coverImage"
        :alt="project.title"
        loading="lazy"
        class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
        @error="imgFailed = true"
      />
      <!-- 无封面：按项目 id 生成的暖色占位图 -->
      <div
        v-else
        class="flex h-full w-full items-center justify-center transition-transform duration-500 group-hover:scale-[1.04]"
        :style="{ background: placeholder.bg }"
      >
        <span class="select-none font-display text-5xl font-bold opacity-90" :style="{ color: placeholder.fg }">
          {{ project.title?.slice(0, 1) || '创' }}
        </span>
      </div>

      <!-- 徽标 -->
      <div class="absolute left-3 top-3 flex gap-1.5">
        <span v-if="project.isRecommend" class="rounded-full bg-amber-warm px-2 py-0.5 text-xs font-medium text-white shadow">推荐</span>
        <span v-if="project.isHot" class="rounded-full bg-clay px-2 py-0.5 text-xs font-medium text-white shadow">热门</span>
      </div>
      <span
        v-if="project.categoryName"
        class="absolute bottom-3 left-3 rounded-full bg-black/45 px-2.5 py-0.5 text-xs text-white backdrop-blur-sm"
      >
        {{ project.categoryName }}
      </span>
    </div>

    <!-- 内容 -->
    <div class="p-4">
      <h3 class="truncate text-base font-semibold text-ink transition-colors group-hover:text-pine">
        {{ project.title }}
      </h3>
      <p class="mt-1.5 line-clamp-2 min-h-[2.5rem] text-sm leading-relaxed text-ink-mid">
        {{ project.description }}
      </p>

      <div v-if="project.tags?.length" class="mt-2.5 flex flex-wrap gap-1.5">
        <span v-for="tag in project.tags.slice(0, 3)" :key="tag" class="chip"># {{ tag }}</span>
      </div>

      <div class="mt-3.5 flex items-center justify-between border-t border-line pt-3">
        <!-- 创建者 -->
        <div class="flex min-w-0 items-center gap-2">
          <span class="flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-[10px] font-bold text-pine-deep">
            <img v-if="project.creator?.avatar" :src="project.creator.avatar" alt="" class="h-full w-full object-cover" />
            <template v-else>{{ (project.creator?.username || '友').slice(0, 1).toUpperCase() }}</template>
          </span>
          <span class="truncate text-xs text-ink-mid">{{ project.creator?.username || '匿名共创者' }}</span>
        </div>

        <!-- 数据 -->
        <div class="flex shrink-0 items-center gap-3 text-xs text-ink-dim">
          <span class="flex items-center gap-1" title="点赞">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20.4 12.6 12 21l-8.4-8.4a5.3 5.3 0 1 1 7.5-7.5l.9.9.9-.9a5.3 5.3 0 1 1 7.5 7.5z" />
            </svg>
            {{ project.likeCount || 0 }}
          </span>
          <span class="flex items-center gap-1" title="参与人数">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="9" cy="8" r="3.5" />
              <path d="M2.5 20c0-3.5 2.9-5.5 6.5-5.5s6.5 2 6.5 5.5" />
              <path d="M16 5a3.5 3.5 0 0 1 0 7M21.5 20c0-3-2-4.8-4.8-5.3" />
            </svg>
            {{ project.participantCount || 0 }}
          </span>
        </div>
      </div>
    </div>
  </router-link>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  project: { type: Object, required: true }
})

const imgFailed = ref(false)

// 无封面时按 id 从 Apple 中性色系取一组稳定配色
const PALETTES = [
  { bg: 'linear-gradient(135deg, #E8E8ED 0%, #D2D2D7 100%)', fg: '#6E6E73' },
  { bg: 'linear-gradient(135deg, #E8F1FD 0%, #C5DFFF 100%)', fg: '#0066CC' },
  { bg: 'linear-gradient(135deg, #FDF0E4 0%, #FFDDB8 100%)', fg: '#C93400' },
  { bg: 'linear-gradient(135deg, #FCE8E9 0%, #FFD1D4 100%)', fg: '#D70015' },
  { bg: 'linear-gradient(135deg, #F0F0F3 0%, #D8DAE5 100%)', fg: '#3A3A3C' },
  { bg: 'linear-gradient(135deg, #E8F5F4 0%, #C2E8E5 100%)', fg: '#00796B' }
]

const placeholder = computed(() => PALETTES[(Number(props.project.id) || 0) % PALETTES.length])
</script>

<template>
  <article
    class="card group relative transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
  >
    <!-- 整卡点击（stretched link）：单个 <a> 铺满卡片，合法 HTML；
         内容层 pointer-events-none 让点击穿透到链接，交互元素各自 z-10 抬起 -->
    <router-link
      :to="`/project/${project.id}`"
      class="absolute inset-0 z-0 rounded-xl2"
      :aria-label="`查看项目：${project.title}`"
      data-test="card-link"
    ></router-link>

    <div class="pointer-events-none relative">
      <!-- 封面 -->
      <div class="relative aspect-[16/9] overflow-hidden rounded-t-xl2">
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

        <!-- 徽标（苹果式白玻璃轻徽章） -->
        <div class="absolute left-3 top-3 flex gap-1.5">
          <span v-if="project.isRecommend" class="inline-flex items-center gap-1 rounded-full bg-[color:var(--glass-badge)] px-2.5 py-0.5 text-[11px] font-medium text-ink shadow-sm backdrop-blur-md">
            <AppIcon name="star" class="h-3 w-3 text-amber-warm" />推荐
          </span>
          <span v-if="project.isHot" class="inline-flex items-center gap-1 rounded-full bg-[color:var(--glass-badge)] px-2.5 py-0.5 text-[11px] font-medium text-ink shadow-sm backdrop-blur-md">
            <AppIcon name="flame" class="h-3 w-3 text-clay" />热门
          </span>
        </div>
        <span
          v-if="project.categoryName"
          class="absolute bottom-3 left-3 rounded-full bg-black/40 px-2.5 py-0.5 text-xs text-white backdrop-blur-md"
        >
          {{ project.categoryName }}
        </span>
      </div>

      <!-- 内容 -->
      <div class="p-5">
        <h3 class="truncate text-[17px] font-semibold text-ink transition-colors group-hover:text-pine">
          {{ project.title }}
        </h3>
        <p class="mt-1.5 line-clamp-2 min-h-[2.5rem] text-sm leading-relaxed text-ink-mid">
          {{ project.description }}
        </p>

        <div v-if="project.tags?.length" class="mt-2.5 flex flex-wrap gap-1.5">
          <router-link
            v-for="tag in project.tags.slice(0, 3)"
            :key="tag"
            :to="{ path: '/', query: { tag } }"
            class="chip-link pointer-events-auto relative z-10"
            data-test="card-tag"
            :title="`看看「${tag}」标签下的项目`"
          >
            # {{ tag }}
          </router-link>
        </div>

        <div class="mt-4 flex items-center justify-between border-t border-line pt-3.5">
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
    </div>

    <!-- 就地收藏：不进入详情页，桌面悬停出现、触屏常显 -->
    <button
      type="button"
      class="absolute right-3 top-3 z-10 inline-flex h-7 w-7 items-center justify-center rounded-full bg-[color:var(--glass-badge)] shadow-sm backdrop-blur-md transition-all duration-200 hover:scale-110 active:scale-95 disabled:cursor-wait disabled:opacity-70"
      :class="[
        project.favorited
          ? 'text-pine'
          : 'text-ink-mid sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100',
        { 'fav-pop': favoritePulse }
      ]"
      :title="project.favorited ? '取消收藏' : '收藏项目'"
      :aria-label="project.favorited ? '取消收藏' : '收藏项目'"
      :aria-pressed="project.favorited"
      :disabled="favoriteActing"
      @click.prevent.stop="toggleFavorite"
    >
      <svg
        class="h-3.5 w-3.5"
        viewBox="0 0 24 24"
        :fill="project.favorited ? 'currentColor' : 'none'"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M19 21 12 16.4 5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
    </button>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as projectApi from '@/api/project'
import { useUserStore } from '@/store/user'
import { setUserFlag } from '@/utils/storage'
import { toast } from '@/composables/useToast'
import { useFavoritePulse } from '@/composables/useFavoritePulse'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  project: { type: Object, required: true }
})

// 收藏状态变化时通知父级（列表模式下用于把取消收藏的卡片移出「只看收藏」）
const emit = defineEmits(['favorite-change'])

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const { favoritePulse, playFavoritePulse } = useFavoritePulse()

const imgFailed = ref(false)
const favoriteActing = ref(false)

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

// 本地状态 + 标记 + 播报，三处保持一致
const applyFavorite = (value) => {
  const p = props.project
  p.favorited = value
  setUserFlag('favorite', userStore.userId, p.id, value)
  emit('favorite-change', { id: p.id, favorited: value })
}

const toggleFavorite = async () => {
  if (favoriteActing.value) return
  if (!userStore.isLoggedIn) {
    toast('登录后就能收藏项目', 'info')
    router.push({ name: 'Login', query: { redirect: route.fullPath } })
    return
  }

  favoriteActing.value = true
  const next = !props.project.favorited
  try {
    if (next) await projectApi.favoriteProject(props.project.id)
    else await projectApi.unfavoriteProject(props.project.id)

    applyFavorite(next)
    if (next) {
      playFavoritePulse()
      toast('已加入收藏')
    } else {
      toast('已取消收藏', 'info')
    }
  } catch (e) {
    // 本地状态与服务端不一致时纠正（如换设备后重复收藏）
    const msg = e.response?.data?.message || ''
    if (msg.includes('已收藏')) applyFavorite(true)
    else if (msg.includes('尚未收藏')) applyFavorite(false)
    else toast('操作失败，请稍后重试', 'error')
  } finally {
    favoriteActing.value = false
  }
}
</script>

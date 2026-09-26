<template>
  <div class="mx-auto max-w-5xl px-4 py-8 sm:px-6">
    <!-- 骨架 -->
    <div v-if="loading" class="space-y-6">
      <div class="skeleton h-5 w-40"></div>
      <div class="skeleton aspect-[21/9] w-full !rounded-xl2"></div>
      <div class="skeleton h-8 w-2/3"></div>
      <div class="skeleton h-4 w-full"></div>
      <div class="skeleton h-4 w-5/6"></div>
    </div>

    <!-- 不存在 -->
    <EmptyState
      v-else-if="notFound"
      icon="search"
      title="项目不存在或已被删除"
      description="它可能已经完成使命，去看看其他项目吧。"
    >
      <router-link to="/" class="btn-primary">回到项目广场</router-link>
    </EmptyState>

    <template v-else-if="project">
      <!-- 滚动玻璃条：滚过封面后浮现（apple.com 产品页式） -->
      <transition name="bar">
        <div
          v-if="scrolled"
          class="fixed inset-x-0 top-12 z-40 border-b border-[color:var(--glass-border)] bg-[color:var(--glass-nav)] backdrop-blur-xl backdrop-saturate-150"
        >
          <div class="mx-auto flex h-12 max-w-5xl items-center gap-3 px-4 sm:px-6">
            <span class="min-w-0 flex-1 truncate text-sm font-semibold text-ink">{{ project.title }}</span>
            <button
              class="btn-ghost !px-3 !py-1.5 text-sm"
              :class="liked ? '!text-clay' : ''"
              :disabled="acting"
              @click="handleLike"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" :fill="liked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.4 12.6 12 21l-8.4-8.4a5.3 5.3 0 1 1 7.5-7.5l.9.9.9-.9a5.3 5.3 0 1 1 7.5 7.5z" />
              </svg>
              {{ project.likeCount }}
            </button>
            <button
              class="!px-4 !py-1.5 text-sm"
              :class="participated ? 'btn-secondary' : 'btn-primary'"
              :disabled="acting"
              @click="handleParticipate"
            >
              {{ participated ? '已参与' : '参与共创' }}
            </button>
          </div>
        </div>
      </transition>

      <!-- 面包屑 -->
      <nav class="mb-5 flex items-center gap-1.5 text-sm text-ink-dim">
        <router-link to="/" class="transition-colors hover:text-pine">项目广场</router-link>
        <span>/</span>
        <router-link
          v-if="project.categoryName"
          :to="{ path: '/', query: { categoryId: project.categoryId } }"
          class="transition-colors hover:text-pine"
        >
          {{ project.categoryName }}
        </router-link>
        <span v-if="project.categoryName">/</span>
        <span class="truncate text-ink-mid">{{ project.title }}</span>
      </nav>

      <!-- 封面（无边框白卡材质，与全站卡片一致） -->
      <div class="relative aspect-[21/9] overflow-hidden rounded-xl2 shadow-card">
        <img
          v-if="project.coverImage && !imgFailed"
          :src="project.coverImage"
          :alt="project.title"
          class="h-full w-full object-cover"
          @error="imgFailed = true"
        />
        <div v-else class="flex h-full w-full items-center justify-center" :style="{ background: placeholder.bg }">
          <span class="select-none font-display text-7xl font-bold opacity-90" :style="{ color: placeholder.fg }">
            {{ project.title?.slice(0, 1) }}
          </span>
        </div>
        <div class="absolute left-4 top-4 flex gap-2">
          <span v-if="project.isRecommend" class="inline-flex items-center gap-1 rounded-full bg-[color:var(--glass-badge)] px-2.5 py-1 text-xs font-medium text-ink shadow-sm backdrop-blur-md"><AppIcon name="star" class="h-3 w-3 text-amber-warm" />编辑推荐</span>
          <span v-if="project.isHot" class="inline-flex items-center gap-1 rounded-full bg-[color:var(--glass-badge)] px-2.5 py-1 text-xs font-medium text-ink shadow-sm backdrop-blur-md"><AppIcon name="flame" class="h-3 w-3 text-clay" />热门</span>
        </div>
      </div>

      <div class="mt-8 grid gap-8 lg:grid-cols-[1fr_300px]">
        <!-- 主内容 -->
        <div class="min-w-0">
          <h1 class="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{{ project.title }}</h1>

          <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-ink-dim">
            <span v-if="project.categoryName" class="chip">{{ project.categoryName }}</span>
            <span>发布于 {{ formatDate(project.createdAt) }}</span>
            <span v-if="project.viewCount">{{ project.viewCount }} 次浏览</span>
          </div>

          <div v-if="project.tags?.length" class="mt-4 flex flex-wrap gap-2">
            <span v-for="tag in project.tags" :key="tag" class="chip"># {{ tag }}</span>
          </div>

          <div v-reveal class="card mt-6 p-6 sm:p-8">
            <h2 class="mb-5 flex items-center gap-2 text-lg font-semibold text-ink">
              <span class="h-4 w-1 rounded-full bg-pine"></span>
              项目介绍
            </h2>
            <!-- 苹果式分层排版：首段导语 17px 深色强调，后续段落 15px 次级灰 -->
            <div class="space-y-4">
              <p
                v-for="(para, i) in descriptionParagraphs"
                :key="i"
                :class="i === 0 ? 'text-[17px] font-medium leading-relaxed text-ink' : 'text-[15px] leading-loose text-ink-mid'"
              >
                {{ para }}
              </p>
            </div>
          </div>
        </div>

        <!-- 侧栏 -->
        <aside class="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <!-- 操作卡（磨砂玻璃材质） -->
          <div class="rounded-xl2 border border-[color:var(--glass-border)] bg-[color:var(--glass-card)] p-5 shadow-card backdrop-blur-xl backdrop-saturate-150">
            <!-- 规格条：苹果官网参数式发丝线网格 -->
            <div class="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line">
              <div class="bg-cream py-3.5 text-center">
                <p class="text-2xl font-semibold tabular-nums text-ink">{{ project.participantCount }}</p>
                <p class="mt-0.5 text-xs text-ink-mid">共创伙伴</p>
              </div>
              <div class="bg-cream py-3.5 text-center">
                <p class="text-2xl font-semibold tabular-nums text-ink">{{ project.likeCount }}</p>
                <p class="mt-0.5 text-xs text-ink-mid">收获点赞</p>
              </div>
              <div class="bg-cream py-3.5 text-center">
                <p class="text-2xl font-semibold tabular-nums text-ink">{{ project.viewCount ?? 0 }}</p>
                <p class="mt-0.5 text-xs text-ink-mid">浏览次数</p>
              </div>
              <div class="bg-cream py-3.5 text-center">
                <p class="text-2xl font-semibold tabular-nums text-ink">{{ createdShort }}</p>
                <p class="mt-0.5 text-xs text-ink-mid">发布日期</p>
              </div>
            </div>

            <div class="mt-4 space-y-2.5">
              <button
                class="w-full !py-3"
                :class="participated ? 'btn-secondary' : 'btn-primary'"
                :disabled="acting"
                @click="handleParticipate"
              >
                <span v-if="participated" class="inline-flex items-center gap-1.5"><AppIcon name="check" class="h-4 w-4" />已参与 · 点击退出</span>
                <span v-else class="inline-flex items-center gap-1.5"><AppIcon name="users" class="h-4 w-4" />参与共创</span>
              </button>
              <button
                class="w-full !py-3"
                :class="liked ? 'btn-secondary !border-clay/40 !text-clay' : 'btn-secondary'"
                :disabled="acting"
                @click="handleLike"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" :fill="liked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20.4 12.6 12 21l-8.4-8.4a5.3 5.3 0 1 1 7.5-7.5l.9.9.9-.9a5.3 5.3 0 1 1 7.5 7.5z" />
                </svg>
                {{ liked ? '已点赞' : '点个赞' }}
              </button>
            </div>

            <!-- 创建者操作 -->
            <div v-if="isOwner" class="mt-4 border-t border-line pt-4">
              <p class="mb-2 text-xs text-ink-dim">你是该项目的创建者</p>
              <button class="btn-ghost w-full !text-clay hover:!bg-[#FBE9EB]" :disabled="acting" @click="handleDelete">
                删除项目
              </button>
            </div>
          </div>

          <!-- 创建者卡 -->
          <div class="card p-5">
            <p class="mb-3 text-xs font-medium tracking-wide text-ink-dim">发起人</p>
            <div class="flex items-center gap-3">
              <span class="flex h-11 w-11 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-base font-bold text-pine-deep">
                <img v-if="project.creator?.avatar" :src="project.creator.avatar" alt="" class="h-full w-full object-cover" />
                <template v-else>{{ (project.creator?.username || '友').slice(0, 1).toUpperCase() }}</template>
              </span>
              <div class="min-w-0">
                <p class="truncate font-medium text-ink">{{ project.creator?.username || '匿名共创者' }}</p>
                <p class="text-xs text-ink-dim">项目发起人</p>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <!-- 评论区（App Store 评价风） -->
      <CommentSection :project-id="project.id" />
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as projectApi from '@/api/project'
import { useUserStore } from '@/store/user'
import { getUserFlag, setUserFlag } from '@/utils/storage'
import { toast } from '@/composables/useToast'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/AppIcon.vue'
import CommentSection from '@/components/CommentSection.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const project = ref(null)
const loading = ref(true)
const notFound = ref(false)
const acting = ref(false)
const imgFailed = ref(false)

const liked = ref(false)
const participated = ref(false)

// 项目介绍分层：按空行/换行拆段，首段作为导语强调（苹果产品页排版）
const descriptionParagraphs = computed(() =>
  (project.value?.description || '')
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
)

// 同步点赞/参与状态：优先采用服务端权威数据，未登录时退回本地标记
const syncFlags = () => {
  const uid = userStore.userId
  const pid = route.params.id
  liked.value = project.value?.liked ?? getUserFlag('like', uid, pid)
  participated.value = project.value?.participated ?? getUserFlag('join', uid, pid)
}

const isOwner = computed(
  () => userStore.isLoggedIn && project.value?.creator?.id === userStore.userId
)

const PALETTES = [
  { bg: 'linear-gradient(135deg, #E8E8ED 0%, #D2D2D7 100%)', fg: '#6E6E73' },
  { bg: 'linear-gradient(135deg, #E8F1FD 0%, #C5DFFF 100%)', fg: '#0066CC' },
  { bg: 'linear-gradient(135deg, #FDF0E4 0%, #FFDDB8 100%)', fg: '#C93400' },
  { bg: 'linear-gradient(135deg, #FCE8E9 0%, #FFD1D4 100%)', fg: '#D70015' },
  { bg: 'linear-gradient(135deg, #F0F0F3 0%, #D8DAE5 100%)', fg: '#3A3A3C' },
  { bg: 'linear-gradient(135deg, #E8F5F4 0%, #C2E8E5 100%)', fg: '#00796B' }
]
const placeholder = computed(() => PALETTES[(Number(project.value?.id) || 0) % PALETTES.length])

// 规格条用短日期
const createdShort = computed(() => {
  if (!project.value?.createdAt) return '—'
  const d = new Date(project.value.createdAt)
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

// 滚过封面后浮现顶部玻璃操作条（apple.com 产品页式）
const scrolled = ref(false)
const onScroll = () => {
  scrolled.value = window.scrollY > 420
}
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

const formatDate = (str) => {
  if (!str) return ''
  const d = new Date(str)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
}

const requireLogin = () => {
  if (userStore.isLoggedIn) return true
  toast('请先登录', 'info')
  router.push({ name: 'Login', query: { redirect: route.fullPath } })
  return false
}

const fetchDetail = async () => {
  loading.value = true
  notFound.value = false
  try {
    const res = await projectApi.getProject(route.params.id)
    project.value = res.data
    syncFlags()
  } catch (e) {
    if (e.response?.status === 404) notFound.value = true
  } finally {
    loading.value = false
  }
}

const handleLike = async () => {
  if (!requireLogin() || acting.value) return
  acting.value = true
  try {
    if (liked.value) {
      const res = await projectApi.unlikeProject(project.value.id)
      project.value.likeCount = res.data.likeCount
      liked.value = false
      setUserFlag('like', userStore.userId, project.value.id, false)
    } else {
      const res = await projectApi.likeProject(project.value.id)
      project.value.likeCount = res.data.likeCount
      liked.value = true
      setUserFlag('like', userStore.userId, project.value.id, true)
      toast('点赞成功，为创意加油！')
    }
  } catch (e) {
    // 本地状态与服务端不一致时纠正（如换设备后重复点赞）
    const msg = e.response?.data?.message || ''
    if (msg.includes('已点赞')) {
      liked.value = true
      setUserFlag('like', userStore.userId, project.value.id, true)
    } else if (msg.includes('尚未点赞')) {
      liked.value = false
      setUserFlag('like', userStore.userId, project.value.id, false)
    }
  } finally {
    acting.value = false
  }
}

const handleParticipate = async () => {
  if (!requireLogin() || acting.value) return
  acting.value = true
  try {
    if (participated.value) {
      const res = await projectApi.cancelParticipate(project.value.id)
      project.value.participantCount = res.data.participantCount
      participated.value = false
      setUserFlag('join', userStore.userId, project.value.id, false)
      toast('已退出该项目', 'info')
    } else {
      const res = await projectApi.participateProject(project.value.id)
      project.value.participantCount = res.data.participantCount
      participated.value = true
      setUserFlag('join', userStore.userId, project.value.id, true)
      toast('参与成功，欢迎加入共创！')
    }
  } catch (e) {
    const msg = e.response?.data?.message || ''
    if (msg.includes('已参与')) {
      participated.value = true
      setUserFlag('join', userStore.userId, project.value.id, true)
    } else if (msg.includes('未参与')) {
      participated.value = false
      setUserFlag('join', userStore.userId, project.value.id, false)
    }
  } finally {
    acting.value = false
  }
}

const handleDelete = async () => {
  if (!window.confirm('确定删除该项目吗？此操作不可恢复。')) return
  acting.value = true
  try {
    await projectApi.deleteProject(project.value.id)
    toast('项目已删除', 'info')
    router.push('/')
  } finally {
    acting.value = false
  }
}

watch(() => route.params.id, fetchDetail, { immediate: true })
</script>

<style scoped>
.bar-enter-active,
.bar-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.bar-enter-from,
.bar-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

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
      icon="🔍"
      title="项目不存在或已被删除"
      description="它可能已经完成使命，去看看其他项目吧。"
    >
      <router-link to="/" class="btn-primary">回到项目广场</router-link>
    </EmptyState>

    <template v-else-if="project">
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

      <!-- 封面 -->
      <div class="relative aspect-[21/9] overflow-hidden rounded-xl2 border border-line">
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
          <span v-if="project.isRecommend" class="rounded-full bg-amber-warm px-2.5 py-1 text-xs font-medium text-white shadow">⭐ 编辑推荐</span>
          <span v-if="project.isHot" class="rounded-full bg-clay px-2.5 py-1 text-xs font-medium text-white shadow">🔥 热门</span>
        </div>
      </div>

      <div class="mt-8 grid gap-8 lg:grid-cols-[1fr_300px]">
        <!-- 主内容 -->
        <div class="min-w-0">
          <h1 class="font-display text-3xl font-bold leading-snug text-ink">{{ project.title }}</h1>

          <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-ink-dim">
            <span v-if="project.categoryName" class="chip">{{ project.categoryName }}</span>
            <span>发布于 {{ formatDate(project.createdAt) }}</span>
            <span v-if="project.viewCount">{{ project.viewCount }} 次浏览</span>
          </div>

          <div v-if="project.tags?.length" class="mt-4 flex flex-wrap gap-2">
            <span v-for="tag in project.tags" :key="tag" class="chip"># {{ tag }}</span>
          </div>

          <div class="card mt-6 p-6 sm:p-8">
            <h2 class="mb-4 flex items-center gap-2 text-lg font-semibold text-ink">
              <span class="h-4 w-1 rounded-full bg-pine"></span>
              项目介绍
            </h2>
            <p class="whitespace-pre-wrap text-[15px] leading-loose text-ink-mid">{{ project.description }}</p>
          </div>
        </div>

        <!-- 侧栏 -->
        <aside class="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <!-- 操作卡 -->
          <div class="card p-5">
            <div class="grid grid-cols-2 gap-3 text-center">
              <div class="rounded-xl bg-pine-tint py-3">
                <p class="text-2xl font-bold text-pine-deep">{{ project.participantCount }}</p>
                <p class="mt-0.5 text-xs text-ink-mid">共创伙伴</p>
              </div>
              <div class="rounded-xl bg-amber-soft py-3">
                <p class="text-2xl font-bold text-amber-warm">{{ project.likeCount }}</p>
                <p class="mt-0.5 text-xs text-ink-mid">收到点赞</p>
              </div>
            </div>

            <div class="mt-4 space-y-2.5">
              <button
                class="w-full !py-3"
                :class="participated ? 'btn-secondary' : 'btn-primary'"
                :disabled="acting"
                @click="handleParticipate"
              >
                {{ participated ? '✓ 已参与 · 点击退出' : '🤝 参与共创' }}
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
              <button class="btn-ghost w-full !text-clay hover:!bg-[#FBEBE7]" :disabled="acting" @click="handleDelete">
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
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as projectApi from '@/api/project'
import { useUserStore } from '@/store/user'
import { getUserFlag, setUserFlag } from '@/utils/storage'
import { toast } from '@/composables/useToast'
import EmptyState from '@/components/EmptyState.vue'

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
  { bg: 'linear-gradient(135deg, #DCEBDD 0%, #B9D8BE 100%)', fg: '#2E6B4F' },
  { bg: 'linear-gradient(135deg, #F5E6CE 0%, #EBD1A6 100%)', fg: '#9A6A22' },
  { bg: 'linear-gradient(135deg, #E2E8F2 0%, #C3CFE4 100%)', fg: '#44598B' },
  { bg: 'linear-gradient(135deg, #F3E0DA 0%, #E7C3B6 100%)', fg: '#A05540' },
  { bg: 'linear-gradient(135deg, #E9E4F4 0%, #D2C8EA 100%)', fg: '#63549B' },
  { bg: 'linear-gradient(135deg, #E0EFEE 0%, #BCDEDC 100%)', fg: '#2F6E6A' }
]
const placeholder = computed(() => PALETTES[(Number(project.value?.id) || 0) % PALETTES.length])

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

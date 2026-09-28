<template>
  <div class="mx-auto max-w-5xl px-4 py-10 sm:px-6">
    <!-- 加载 -->
    <div v-if="loading" class="space-y-6">
      <div class="skeleton h-40 w-full !rounded-xl2"></div>
      <div class="skeleton h-8 w-48"></div>
      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <ProjectCardSkeleton v-for="i in 3" :key="i" />
      </div>
    </div>

    <!-- 用户不存在 -->
    <EmptyState
      v-else-if="notFound"
      icon="user"
      title="找不到这位共创者"
      description="Ta 可能已经注销，或者链接里的编号不对。"
    >
      <router-link to="/" class="btn-primary">回到项目广场</router-link>
    </EmptyState>

    <template v-else>
      <!-- 个人信息卡 -->
      <div class="card relative overflow-hidden p-6 sm:p-8" data-test="user-profile">
        <div class="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-pine-soft blur-2xl" aria-hidden="true"></div>

        <div class="relative flex flex-col gap-6 sm:flex-row sm:items-center">
          <span class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-pine text-3xl font-bold text-white">
            <img v-if="profile?.user?.avatar" :src="profile.user.avatar" alt="" class="h-full w-full object-cover" />
            <template v-else>{{ (profile?.user?.username || '友').slice(0, 1).toUpperCase() }}</template>
          </span>

          <div class="min-w-0 flex-1">
            <h1 class="font-display text-2xl font-bold text-ink" data-test="user-name">{{ profile?.user?.username }}</h1>
            <p class="mt-1 text-sm text-ink-dim">{{ joinedText }}</p>
            <p class="mt-2 text-sm leading-relaxed text-ink-mid">
              {{ profile?.user?.bio || '这位共创者还没有写简介。' }}
            </p>
          </div>

          <!-- 自己的主页才给编辑入口 -->
          <router-link v-if="isMe" to="/profile" class="btn-secondary shrink-0" data-test="user-edit-self">
            编辑我的资料
          </router-link>
        </div>

        <!-- 数据概览：苹果参数式发丝线规格条 -->
        <div class="relative mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-line sm:grid-cols-4" data-test="user-stats">
          <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
            <p class="text-xl font-semibold tabular-nums text-ink">{{ profile?.stats?.projectCount ?? '—' }}</p>
            <p class="mt-0.5 text-xs text-ink-dim">发布项目</p>
          </div>
          <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
            <p class="text-xl font-semibold tabular-nums text-ink">{{ profile?.stats?.joinedCount ?? '—' }}</p>
            <p class="mt-0.5 text-xs text-ink-dim">参与共创</p>
          </div>
          <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
            <p class="text-xl font-semibold tabular-nums text-ink">{{ profile?.stats?.likeReceived ?? '—' }}</p>
            <p class="mt-0.5 text-xs text-ink-dim">收到点赞</p>
          </div>
          <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
            <p class="text-xl font-semibold tabular-nums text-ink">{{ joinMonth }}</p>
            <p class="mt-0.5 text-xs text-ink-dim">加入于</p>
          </div>
        </div>
      </div>

      <!-- TA 发布的项目 -->
      <div class="mt-10">
        <div class="mb-5 flex items-center justify-between">
          <h2 class="flex items-center gap-2 text-lg font-semibold text-ink">
            <span class="h-4 w-1 rounded-full bg-pine"></span>
            {{ isMe ? '我发布的项目' : 'TA 发布的项目' }}
            <span v-if="!loadingCreated" data-test="created-count" class="text-sm font-normal text-ink-dim">（{{ createdCount }}）</span>
          </h2>
          <!-- 预览只 6 条，被截断才给入口；跳广场用现成的 creatorId 筛选 -->
          <router-link
            v-if="!loadingCreated && hasMoreCreated"
            data-test="view-all-created"
            :to="{ path: '/', query: { creatorId: route.params.id } }"
            class="btn-ghost !py-1 text-xs"
          >
            查看全部
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m9 6 6 6-6 6" />
            </svg>
          </router-link>
        </div>

        <div v-if="loadingCreated" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <ProjectCardSkeleton v-for="i in 2" :key="i" />
        </div>

        <EmptyState
          v-else-if="!created.length"
          icon="lightbulb"
          title="还没有发布过项目"
          description="想法攒够了就会开花，先去看看别人的。"
        >
          <router-link to="/" class="btn-secondary">去发现项目</router-link>
        </EmptyState>

        <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3" data-test="user-created">
          <ProjectCard v-for="(p, i) in created" :key="p.id" v-reveal="Math.min(i, 5) * 60" :project="p" />
        </div>
      </div>

      <!-- TA 参与的共创 -->
      <div class="mt-12">
        <div class="mb-5 flex items-center justify-between">
          <h2 class="flex items-center gap-2 text-lg font-semibold text-ink">
            <span class="h-4 w-1 rounded-full bg-pine"></span>
            {{ isMe ? '我参与的共创' : 'TA 参与的共创' }}
            <span v-if="!loadingJoined" data-test="joined-count" class="text-sm font-normal text-ink-dim">（{{ joinedCount }}）</span>
          </h2>
          <router-link
            v-if="!loadingJoined && hasMoreJoined"
            data-test="view-all-joined"
            :to="{ path: '/', query: { participantId: route.params.id } }"
            class="btn-ghost !py-1 text-xs"
          >
            查看全部
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m9 6 6 6-6 6" />
            </svg>
          </router-link>
        </div>

        <div v-if="loadingJoined" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <ProjectCardSkeleton v-for="i in 2" :key="i" />
        </div>

        <EmptyState
          v-else-if="!joined.length"
          icon="users"
          title="还没有参与别人的项目"
          description="参与不算承诺，点一下「参与共创」就能加入。"
        >
          <router-link to="/" class="btn-secondary">去逛逛</router-link>
        </EmptyState>

        <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3" data-test="user-joined">
          <ProjectCard v-for="(p, i) in joined" :key="p.id" v-reveal="Math.min(i, 5) * 60" :project="p" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getProjects } from '@/api/project'
import { getPublicProfile } from '@/api/user'
import { useUserStore } from '@/store/user'
import ProjectCard from '@/components/ProjectCard.vue'
import ProjectCardSkeleton from '@/components/ProjectCardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const userStore = useUserStore()

const profile = ref(null)
const loading = ref(true)
const notFound = ref(false)

const created = ref([])
const joined = ref([])
const loadingCreated = ref(true)
const loadingJoined = ref(true)

const PAGE_SIZE = 6

const isMe = computed(() => !!profile.value && Number(profile.value.user.id) === Number(userStore.userId))

// 括号里的计数要说真话：列表只预览 6 条，展示「6 / 8」会让人以为 TA 就这么多，
// 所以优先用服务端的真实统计，取不到才退回本页条数
const createdCount = computed(() => Number(profile.value?.stats?.projectCount ?? created.value.length))
const joinedCount = computed(() => Number(profile.value?.stats?.joinedCount ?? joined.value.length))

// 「查看全部」只在列表确实被截断时出现，点了却还是这几条就是假入口
const hasMoreCreated = computed(() => created.value.length > 0 && createdCount.value > created.value.length)
const hasMoreJoined = computed(() => joined.value.length > 0 && joinedCount.value > joined.value.length)

const joinedText = computed(() => {
  const d = profile.value?.user?.joinedAt ? new Date(profile.value.user.joinedAt) : null
  if (!d || Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月加入`
})

const joinMonth = computed(() => {
  const d = profile.value?.user?.joinedAt ? new Date(profile.value.user.joinedAt) : null
  if (!d || Number.isNaN(d.getTime())) return '—'
  return `${d.getFullYear() % 100}/${String(d.getMonth() + 1).padStart(2, '0')}`
})

const loadProfile = async () => {
  const id = route.params.id
  loading.value = true
  notFound.value = false
  profile.value = null
  try {
    profile.value = (await getPublicProfile(id)).data
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
}

const loadCreated = async () => {
  const id = route.params.id
  loadingCreated.value = true
  try {
    created.value = (await getProjects({ page: 1, pageSize: PAGE_SIZE, sort: 'latest', creatorId: id })).data.projects
  } catch {
    created.value = []
  } finally {
    loadingCreated.value = false
  }
}

// 参与过的共创：复用广场列表接口（不含 TA 自己发起的，避免两块列表重复）
const loadJoined = async () => {
  const id = route.params.id
  loadingJoined.value = true
  try {
    joined.value = (await getProjects({ page: 1, pageSize: PAGE_SIZE, sort: 'latest', participantId: id })).data.projects
  } catch {
    joined.value = []
  } finally {
    loadingJoined.value = false
  }
}

// 同路由换用户（从 A 的主页点进 B）要重拉三块
watch(
  () => route.params.id,
  async (id) => {
    if (!id) return
    await loadProfile()
    if (!notFound.value) {
      loadCreated()
      loadJoined()
    }
  },
  { immediate: true }
)
</script>

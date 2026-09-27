<template>
  <div class="mx-auto max-w-5xl px-4 py-10 sm:px-6">
    <!-- 个人信息卡 -->
    <div class="card relative overflow-hidden p-6 sm:p-8">
      <div class="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-pine-soft blur-2xl" aria-hidden="true"></div>

      <div class="relative flex flex-col gap-6 sm:flex-row sm:items-center">
        <span class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-pine text-3xl font-bold text-white">
          <img v-if="user?.avatar" :src="user.avatar" alt="" class="h-full w-full object-cover" />
          <template v-else>{{ (user?.username || '友').slice(0, 1).toUpperCase() }}</template>
        </span>

        <div class="min-w-0 flex-1">
          <h1 class="font-display text-2xl font-bold text-ink">{{ user?.username }}</h1>
          <p class="mt-1 text-sm text-ink-dim">{{ user?.email }}</p>
          <p class="mt-2 text-sm leading-relaxed text-ink-mid">
            {{ user?.bio || '这位共创者还没有写简介。' }}
          </p>
        </div>

        <button class="btn-secondary shrink-0" @click="openEdit">编辑资料</button>
      </div>

      <!-- 数据概览：苹果参数式发丝线规格条 -->
      <div class="relative mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-line sm:grid-cols-4">
        <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
          <p class="text-xl font-semibold tabular-nums text-ink">{{ stats?.projectCount ?? '—' }}</p>
          <p class="mt-0.5 text-xs text-ink-dim">发布项目</p>
        </div>
        <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
          <p class="text-xl font-semibold tabular-nums text-ink">{{ stats?.commentCount ?? '—' }}</p>
          <p class="mt-0.5 text-xs text-ink-dim">参与评论</p>
        </div>
        <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
          <p class="text-xl font-semibold tabular-nums text-ink">{{ stats?.favoriteCount ?? '—' }}</p>
          <p class="mt-0.5 text-xs text-ink-dim">收藏项目</p>
        </div>
        <div class="bg-cream px-4 py-3.5 text-center sm:text-left">
          <p class="text-xl font-semibold tabular-nums text-ink">{{ stats?.likeReceived ?? '—' }}</p>
          <p class="mt-0.5 text-xs text-ink-dim">收到点赞</p>
        </div>
      </div>
    </div>

    <!-- 我发布的项目 -->
    <div class="mt-10">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-ink">
          <span class="h-4 w-1 rounded-full bg-pine"></span>
          我发布的项目
          <span v-if="!loadingProjects" class="text-sm font-normal text-ink-dim">（{{ myProjects.length }}）</span>
        </h2>
        <router-link to="/publish" class="btn-ghost text-sm">+ 发布新项目</router-link>
      </div>

      <div v-if="loadingProjects" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <ProjectCardSkeleton v-for="i in 3" :key="i" />
      </div>

      <EmptyState
        v-else-if="!myProjects.length"
        icon="lightbulb"
        title="你还没有发布过项目"
        description="有什么想法在脑子里转了很久？写下来，让它见见光。"
      >
        <router-link to="/publish" class="btn-primary">发布第一个项目</router-link>
      </EmptyState>

      <div v-else data-test="profile-my-projects" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <ProjectCard
          v-for="(p, i) in myProjects"
          :key="p.id"
          v-reveal="Math.min(i, 5) * 60"
          :project="p"
          editable
        />
      </div>
    </div>

    <!-- 我的收藏 -->
    <div class="mt-12">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-ink">
          <span class="h-4 w-1 rounded-full bg-pine"></span>
          我的收藏
          <span v-if="!loadingFavorites" class="text-sm font-normal text-ink-dim">（{{ favoriteTotal }}）</span>
        </h2>
      </div>

      <div v-if="loadingFavorites" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <ProjectCardSkeleton v-for="i in 3" :key="i" />
      </div>

      <EmptyState
        v-else-if="!myFavorites.length"
        icon="bookmark"
        title="还没有收藏任何项目"
        description="遇到感兴趣的项目，点一下收藏，之后在这里能快速找到。"
      >
        <router-link to="/" class="btn-secondary">去发现项目</router-link>
      </EmptyState>

      <template v-else>
        <div data-test="profile-favorites" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <ProjectCard
            v-for="(p, i) in myFavorites"
            :key="p.id"
            v-reveal="Math.min(i, 5) * 60"
            :project="p"
            @favorite-change="onFavoriteChange"
          />
        </div>
        <div v-if="myFavorites.length < favoriteTotal" class="mt-6 text-center">
          <button class="btn-ghost" :disabled="loadingMoreFavorites" @click="loadMoreFavorites">
            {{ loadingMoreFavorites ? '加载中…' : '加载更多' }}
          </button>
        </div>
      </template>
    </div>

    <!-- 我参与的讨论 -->
    <div class="mt-12">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-ink">
          <span class="h-4 w-1 rounded-full bg-pine"></span>
          我参与的讨论
          <span v-if="!loadingComments" class="text-sm font-normal text-ink-dim">（{{ commentTotal }}）</span>
        </h2>
      </div>

      <div v-if="loadingComments" class="space-y-3">
        <div v-for="i in 3" :key="i" class="card h-[76px] animate-pulse !shadow-sm" style="animation-delay: 0ms"></div>
      </div>

      <EmptyState
        v-else-if="!myComments.length"
        icon="message-circle"
        title="还没有参与过讨论"
        description="去逛逛别人的项目，留下你的第一条评论吧。"
      >
        <router-link to="/" class="btn-primary">去逛逛</router-link>
      </EmptyState>

      <template v-else>
        <div class="card divide-y divide-line overflow-hidden !p-0">
          <router-link
            v-for="(c, i) in myComments"
            :key="c.id"
            v-reveal="Math.min(i, 6) * 50"
            data-test="profile-discussion"
            :to="c.project ? `/project/${c.project.id}#comments` : '/'"
            class="group block px-5 py-4 transition-colors hover:bg-pine-soft/40"
          >
            <div class="flex items-center gap-2">
              <span class="min-w-0 flex-1 truncate text-sm font-medium text-pine-deep">
                {{ c.project?.title || '项目已删除' }}
              </span>
              <span v-if="c.parentId" class="chip !px-2 !py-0.5 text-[11px]">回复</span>
              <span class="shrink-0 text-xs tabular-nums text-ink-dim">{{ relativeTime(c.createdAt) }}</span>
            </div>
            <p class="mt-1.5 line-clamp-2 text-[15px] leading-relaxed text-ink-mid">{{ c.content }}</p>
            <div class="mt-2 flex items-center gap-1 text-xs tabular-nums text-ink-dim">
              <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.4 12.6 12 21l-8.4-8.4a5.3 5.3 0 1 1 7.5-7.5l.9.9.9-.9a5.3 5.3 0 1 1 7.5 7.5z" />
              </svg>
              {{ c.likeCount }}
              <span class="ml-auto hidden items-center gap-0.5 text-pine-deep opacity-0 transition-opacity group-hover:opacity-100 sm:inline-flex">
                查看对话
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </span>
            </div>
          </router-link>
        </div>

        <div v-if="myComments.length < commentTotal" class="mt-5 text-center">
          <button class="btn-ghost" :disabled="loadingMore" @click="loadMoreComments">
            {{ loadingMore ? '加载中…' : '加载更多' }}
          </button>
        </div>
      </template>
    </div>

    <!-- 编辑资料弹窗 -->
    <Teleport to="body">
      <transition name="modal">
        <div
          v-if="editing"
          class="fixed inset-0 z-[90] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
          @click.self="editing = false"
        >
          <div class="card w-full max-w-md p-6 shadow-pop sm:p-8">
            <h3 class="font-display text-xl font-bold text-ink">编辑资料</h3>

            <form class="mt-6 space-y-5" @submit.prevent="handleSave">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-ink" for="edit-username">用户名</label>
                <input id="edit-username" v-model.trim="editForm.username" type="text" class="input" maxlength="20" />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-ink" for="edit-avatar">头像链接</label>
                <input id="edit-avatar" v-model.trim="editForm.avatar" type="url" class="input" placeholder="https://…" />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-ink" for="edit-bio">个人简介</label>
                <textarea
                  id="edit-bio"
                  v-model.trim="editForm.bio"
                  class="input min-h-[90px] resize-y"
                  placeholder="用一两句话介绍自己…"
                  maxlength="200"
                ></textarea>
              </div>

              <div class="flex justify-end gap-3 pt-2">
                <button type="button" class="btn-ghost" @click="editing = false">取消</button>
                <button type="submit" class="btn-primary" :disabled="saving">
                  {{ saving ? '保存中…' : '保存' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useUserStore } from '@/store/user'
import { getProjects } from '@/api/project'
import { getMyComments, getMyFavorites, getMyStats, updateProfile } from '@/api/user'
import { toast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import ProjectCard from '@/components/ProjectCard.vue'
import ProjectCardSkeleton from '@/components/ProjectCardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore = useUserStore()
const user = computed(() => userStore.userInfo)

const myProjects = ref([])
const loadingProjects = ref(true)

const stats = ref(null)

const myFavorites = ref([])
const favoriteTotal = ref(0)
const favoritePage = ref(1)
const loadingFavorites = ref(true)
const loadingMoreFavorites = ref(false)
const FAVORITE_PAGE_SIZE = 6

const myComments = ref([])
const commentTotal = ref(0)
const commentPage = ref(1)
const loadingComments = ref(true)
const loadingMore = ref(false)
const COMMENT_PAGE_SIZE = 10

const editing = ref(false)
const saving = ref(false)
const editForm = reactive({ username: '', avatar: '', bio: '' })

const openEdit = () => {
  editForm.username = user.value?.username || ''
  editForm.avatar = user.value?.avatar || ''
  editForm.bio = user.value?.bio || ''
  editing.value = true
}

const handleSave = async () => {
  if (saving.value) return
  saving.value = true
  try {
    await updateProfile({
      username: editForm.username,
      avatar: editForm.avatar,
      bio: editForm.bio
    })
    await userStore.fetchMe()
    toast('资料已更新')
    editing.value = false
  } catch {
    // 错误已由拦截器 toast
  } finally {
    saving.value = false
  }
}

// 服务端按创建者过滤，只拉自己的项目
const fetchMyProjects = async () => {
  loadingProjects.value = true
  try {
    const res = await getProjects({ page: 1, pageSize: 12, sort: 'latest', creatorId: userStore.userId })
    myProjects.value = res.data.projects
  } catch {
    myProjects.value = []
  } finally {
    loadingProjects.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await getMyStats()
    stats.value = res.data
  } catch {
    stats.value = null
  }
}

const initFavorites = async () => {
  loadingFavorites.value = true
  try {
    const res = await getMyFavorites({ page: 1, pageSize: FAVORITE_PAGE_SIZE })
    myFavorites.value = res.data.projects
    favoriteTotal.value = res.data.total
    favoritePage.value = res.data.page
  } catch {
    myFavorites.value = []
    favoriteTotal.value = 0
  } finally {
    loadingFavorites.value = false
  }
}

const loadMoreFavorites = async () => {
  if (loadingMoreFavorites.value) return
  loadingMoreFavorites.value = true
  try {
    const res = await getMyFavorites({ page: favoritePage.value + 1, pageSize: FAVORITE_PAGE_SIZE })
    myFavorites.value.push(...res.data.projects)
    favoriteTotal.value = res.data.total
    favoritePage.value = res.data.page
  } catch {
    // 错误已由拦截器 toast
  } finally {
    loadingMoreFavorites.value = false
  }
}

// 在「我的收藏」里就地取消收藏，卡片即时移出列表，计数同步
const onFavoriteChange = ({ id, favorited }) => {
  if (favorited) return
  myFavorites.value = myFavorites.value.filter((p) => p.id !== id)
  if (favoriteTotal.value > 0) favoriteTotal.value -= 1
  if (stats.value) stats.value.favoriteCount = Math.max(0, (stats.value.favoriteCount ?? 1) - 1)
}

const fetchMyComments = async (page = 1) => {
  const res = await getMyComments({ page, pageSize: COMMENT_PAGE_SIZE })
  return res.data
}

const loadMoreComments = async () => {
  if (loadingMore.value) return
  loadingMore.value = true
  try {
    const data = await fetchMyComments(commentPage.value + 1)
    myComments.value.push(...data.comments)
    commentTotal.value = data.total
    commentPage.value = data.page
  } catch {
    // 错误已由拦截器 toast
  } finally {
    loadingMore.value = false
  }
}

const initComments = async () => {
  loadingComments.value = true
  try {
    const data = await fetchMyComments(1)
    myComments.value = data.comments
    commentTotal.value = data.total
    commentPage.value = data.page
  } catch {
    myComments.value = []
  } finally {
    loadingComments.value = false
  }
}

onMounted(async () => {
  // 确保 userId 可用后再过滤
  if (!user.value) await userStore.fetchMe().catch(() => {})
  fetchMyProjects()
  fetchStats()
  initFavorites()
  initComments()
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>

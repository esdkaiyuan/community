<template>
  <div>
    <!-- ============ Hero ============ -->
    <section v-if="!isFiltering" class="relative overflow-hidden border-b border-line bg-cream">
      <!-- 装饰：柔和光晕（克制） -->
      <div class="pointer-events-none absolute inset-0" aria-hidden="true">
        <div class="absolute left-1/2 top-0 h-80 w-[36rem] -translate-x-1/2 -translate-y-1/3 rounded-full bg-pine-soft opacity-50 blur-3xl"></div>
      </div>

      <div class="relative mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-28">
        <div class="animate-fade-up">
          <p class="inline-flex items-center gap-1.5 text-sm font-medium text-pine">
            <AppIcon name="sprout" class="h-4 w-4" />
            已有 {{ total }} 个项目正在共创
          </p>
          <h1 class="mt-4 text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-6xl">
            一起想，一起做<br />
            <span class="text-pine">让好创意落地生根</span>
          </h1>
          <p class="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-ink-mid">
            在这里发布你的项目构想，找到志同道合的伙伴；或者加入别人的项目，贡献你的一份力量。
          </p>
          <div class="mt-9 flex flex-wrap items-center justify-center gap-5">
            <router-link to="/publish" class="btn-primary !px-7 !py-3 text-base">
              发布我的项目
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
                <path d="M5 12h14m-6-6 6 6-6 6" />
              </svg>
            </router-link>
            <a
              href="#projects"
              class="inline-flex items-center gap-0.5 text-base font-medium text-pine transition-colors hover:text-pine-deep hover:underline"
            >
              浏览项目广场
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m9 6 6 6-6 6" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 项目广场 ============ -->
    <section id="projects" class="mx-auto max-w-7xl scroll-mt-20 px-4 py-10 sm:px-6">
      <!-- 搜索结果提示 -->
      <div v-if="query.search" class="mb-6 flex items-center gap-3">
        <h2 class="text-lg font-semibold text-ink">「{{ query.search }}」的搜索结果</h2>
        <button class="btn-ghost !py-1 text-xs" @click="clearSearch">
          清除搜索
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 分类 -->
      <div class="flex flex-wrap items-center gap-2">
        <button class="cat-pill" :class="{ 'is-active': !query.categoryId }" @click="setCategory(null)">
          全部
        </button>
        <button
          v-for="cat in categories"
          :key="cat.id"
          class="cat-pill"
          :class="{ 'is-active': query.categoryId === String(cat.id) }"
          @click="setCategory(cat.id)"
        >
          <AppIcon v-if="cat.icon" :name="categoryIcon(cat.icon)" class="h-3.5 w-3.5" />
          {{ cat.name }}
          <span class="text-xs opacity-60">{{ cat.count }}</span>
        </button>
      </div>

      <!-- 筛选 / 排序 -->
      <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-for="f in FILTERS"
            :key="f.value"
            class="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm transition-colors"
            :class="query.filter === f.value ? 'bg-sand font-semibold text-ink' : 'text-ink-mid hover:bg-sand/60'"
            @click="toggleFilter(f.value)"
          >
            <AppIcon :name="f.icon" class="h-3.5 w-3.5" />
            {{ f.label }}
          </button>

          <!-- 只看收藏（登录后可用，跨分类的个人视图） -->
          <span v-if="userStore.isLoggedIn" class="mx-0.5 h-5 w-px shrink-0 bg-line" aria-hidden="true"></span>
          <button
            v-if="userStore.isLoggedIn"
            class="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm transition-colors"
            :class="onlyFavorited ? 'bg-sand font-semibold text-pine' : 'text-ink-mid hover:bg-sand/60'"
            :aria-pressed="onlyFavorited"
            @click="toggleFavorited"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" :fill="onlyFavorited ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21 12 16.4 5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
            只看收藏
          </button>
        </div>

        <div class="flex items-center gap-1 text-sm">
          <span class="mr-1 text-xs text-ink-dim">排序</span>
          <button
            v-for="s in SORTS"
            :key="s.value"
            class="rounded-full px-3 py-1.5 transition-colors"
            :class="query.sort === s.value ? 'font-semibold text-pine' : 'text-ink-mid hover:bg-sand/60'"
            @click="setSort(s.value)"
          >
            {{ s.label }}
          </button>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <ProjectCardSkeleton v-for="i in 8" :key="i" />
      </div>

      <!-- 加载失败 -->
      <EmptyState
        v-else-if="loadError"
        icon="triangle-alert"
        title="加载失败了"
        description="可能是网络或服务暂时不可用，请稍后重试。"
      >
        <button class="btn-primary" @click="fetchProjects">重新加载</button>
      </EmptyState>

      <!-- 空结果：只看收藏 -->
      <EmptyState
        v-else-if="!projects.length && onlyFavorited"
        icon="bookmark"
        title="还没有收藏任何项目"
        description="在项目详情页点一下「收藏」，把心动的创意收进这里慢慢看。"
      >
        <button class="btn-primary" @click="toggleFavorited">去看看全部项目</button>
      </EmptyState>

      <!-- 空结果 -->
      <EmptyState
        v-else-if="!projects.length"
        icon="sprout"
        :title="query.search ? '没有找到相关项目' : '这里还很安静'"
        :description="query.search ? '换个关键词试试，或者浏览全部项目。' : '成为第一个发布项目的人，让创意在这里发芽。'"
      >
        <router-link to="/publish" class="btn-primary">发布第一个项目</router-link>
      </EmptyState>

      <!-- 项目网格 -->
      <template v-else>
        <div class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <ProjectCard
            v-for="(p, i) in projects"
            :key="p.id"
            v-reveal="Math.min(i, 7) * 60"
            :project="p"
            @favorite-change="onFavoriteChange"
          />
        </div>

        <div class="mt-10">
          <Pagination :page="page" :total="total" :page-size="PAGE_SIZE" @change="setPage" />
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProjects } from '@/api/project'
import { getCategories } from '@/api/category'
import { categoryIcon } from '@/utils/categoryIcon'
import { useUserStore } from '@/store/user'
import AppIcon from '@/components/AppIcon.vue'
import ProjectCard from '@/components/ProjectCard.vue'
import ProjectCardSkeleton from '@/components/ProjectCardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import Pagination from '@/components/Pagination.vue'

const PAGE_SIZE = 12
const FILTERS = [
  { label: '编辑推荐', value: 'recommend', icon: 'star' },
  { label: '热门', value: 'hot', icon: 'flame' }
]
const SORTS = [
  { label: '最新', value: 'latest' },
  { label: '最热', value: 'hot' },
  { label: '参与最多', value: 'participants' }
]

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const categories = ref([])
const projects = ref([])
const total = ref(0)
const loading = ref(true)
const loadError = ref(false)

// 筛选状态完全由路由 query 驱动，可分享、可后退
const query = reactive({
  categoryId: route.query.categoryId || null,
  search: route.query.search || '',
  filter: route.query.filter || '',
  favorited: route.query.favorited || '',
  sort: route.query.sort || 'latest'
})
const page = ref(Number(route.query.page) || 1)

// 「只看收藏」是登录用户的个人视图，未登录时即便 query 带着也不生效
const onlyFavorited = computed(() => query.favorited === '1' && userStore.isLoggedIn)

const isFiltering = computed(
  () =>
    !!(
      query.search ||
      query.categoryId ||
      query.filter ||
      onlyFavorited.value ||
      (route.query.page && page.value > 1)
    )
)

const syncRoute = () => {
  const q = {}
  if (query.categoryId) q.categoryId = query.categoryId
  if (query.search) q.search = query.search
  if (query.filter) q.filter = query.filter
  if (onlyFavorited.value) q.favorited = '1'
  if (query.sort !== 'latest') q.sort = query.sort
  if (page.value > 1) q.page = page.value
  router.push({ path: '/', query: q })
}

const setCategory = (id) => {
  query.categoryId = id ? String(id) : null
  page.value = 1
  syncRoute()
}
const toggleFilter = (f) => {
  query.filter = query.filter === f ? '' : f
  page.value = 1
  syncRoute()
}
const toggleFavorited = () => {
  query.favorited = onlyFavorited.value ? '' : '1'
  page.value = 1
  syncRoute()
}
const setSort = (s) => {
  query.sort = s
  page.value = 1
  syncRoute()
}
const setPage = (p) => {
  page.value = p
  syncRoute()
  document.getElementById('projects')?.scrollIntoView({ behavior: 'smooth' })
}
const clearSearch = () => {
  query.search = ''
  page.value = 1
  syncRoute()
}

// 「只看收藏」视图里取消收藏即移出列表，并把总数同步减一
const onFavoriteChange = ({ id, favorited }) => {
  if (!onlyFavorited.value || favorited) return
  projects.value = projects.value.filter((p) => p.id !== id)
  if (total.value > 0) total.value -= 1
}

const fetchProjects = async () => {
  loading.value = true
  loadError.value = false
  try {
    const res = await getProjects({
      page: page.value,
      pageSize: PAGE_SIZE,
      categoryId: query.categoryId || undefined,
      search: query.search || undefined,
      filter: query.filter || undefined,
      favorited: onlyFavorited.value ? '1' : undefined,
      sort: query.sort
    })
    projects.value = res.data.projects
    total.value = res.data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

const fetchCategories = async () => {
  try {
    const res = await getCategories()
    categories.value = res.data
  } catch {
    // 分类加载失败不阻塞页面
  }
}

// 外部路由变化（如导航栏搜索、页脚快捷链接）时同步并重新拉取
watch(
  () => route.query,
  (q) => {
    if (route.path !== '/') return
    query.categoryId = q.categoryId || null
    query.search = q.search || ''
    query.filter = q.filter || ''
    query.favorited = q.favorited || ''
    query.sort = q.sort || 'latest'
    page.value = Number(q.page) || 1
    fetchProjects()
  }
)

// 登出后「只看收藏」失效，需要清掉筛选并回到全量列表
watch(
  () => userStore.isLoggedIn,
  (loggedIn) => {
    if (!loggedIn && query.favorited) {
      query.favorited = ''
      page.value = 1
      syncRoute()
    }
  }
)

onMounted(() => {
  fetchCategories()
  fetchProjects()
})
</script>


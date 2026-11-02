<template>
  <div data-test="admin-projects">
    <!-- 搜索 + 排序 -->
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <form class="flex w-full max-w-lg items-center gap-2" @submit.prevent="applySearch">
        <div class="relative min-w-0 flex-1">
          <AppIcon
            name="search"
            class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-dim"
          />
          <input
            v-model="searchInput"
            type="search"
            class="input rounded-full py-2 pl-9 text-footnote"
            placeholder="搜索项目标题…"
            aria-label="搜索项目"
          />
        </div>
        <button type="submit" class="btn-secondary !px-4 !py-2 text-footnote">搜索</button>
        <button
          v-if="search"
          type="button"
          class="btn-ghost !px-2 text-footnote"
          @click="clearSearch"
        >
          清除
        </button>
      </form>

      <div class="flex items-center gap-3">
        <span class="hidden text-caption2 font-mono uppercase tracking-[0.14em] text-ink-dim sm:inline">排序</span>
        <AppSegmented
          :model-value="sort"
          :options="SORTS"
          aria-label="项目排序"
          test-id="admin-project-sort"
          @update:model-value="setSort"
        />
      </div>
    </div>

    <!-- 状态筛选 + 全局汇总 -->
    <div class="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label="按项目状态筛选">
      <button
        v-for="f in STATE_FILTERS"
        :key="f.value"
        type="button"
        class="hig-chip"
        :class="state === f.value ? 'is-active' : ''"
        :aria-pressed="state === f.value"
        @click="switchState(f.value)"
      >
        {{ f.label }}
      </button>
      <span class="ml-auto text-caption1 text-ink-dim">
        共 {{ fmt(summary.total) }} 个项目 · 已下架 {{ fmt(summary.hidden) }} · 推荐 {{ fmt(summary.recommend) }}
      </span>
    </div>

    <div v-if="loading" class="hig-list mt-5">
      <div v-for="i in 6" :key="i" class="flex items-center gap-3 px-4 py-4">
        <div class="h-12 w-12 shrink-0 animate-pulse rounded-10 bg-sand"></div>
        <div class="min-w-0 flex-1 space-y-2">
          <div class="h-3.5 w-2/5 animate-pulse rounded bg-sand"></div>
          <div class="h-3 w-3/5 animate-pulse rounded bg-sand"></div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else-if="forbidden"
      icon="lock"
      title="需要管理员权限"
      description="当前账号没有管理台权限，或权限刚被撤销。"
    >
      <router-link to="/" class="btn-primary">返回广场</router-link>
    </EmptyState>

    <EmptyState
      v-else-if="failed"
      icon="triangle-alert"
      title="项目列表加载失败"
      description="服务暂时不可用，请稍后重试。"
    >
      <button class="btn-primary" @click="load">重新加载</button>
    </EmptyState>

    <div v-else-if="projects.length" class="hig-list mt-5" data-test="admin-project-list">
      <article
        v-for="p in projects"
        :key="p.id"
        class="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center"
      >
        <div class="flex min-w-0 flex-1 items-center gap-3">
          <span class="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-10 bg-sand text-ink-dim">
            <img v-if="p.coverImage" :src="p.coverImage" alt="" class="h-full w-full object-cover" />
            <AppIcon v-else name="image" class="h-5 w-5" />
          </span>

          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-1.5">
              <router-link
                v-if="!p.isHidden"
                :to="`/project/${p.id}`"
                class="truncate text-headline font-medium text-ink transition-colors hover:text-pine"
              >
                {{ p.title }}
              </router-link>
              <span v-else class="truncate text-headline font-medium text-ink">{{ p.title }}</span>
              <span
                v-if="p.isHidden"
                class="rounded-full bg-clay/10 px-2 py-0.5 text-caption2 font-medium text-clay"
              >
                已下架
              </span>
              <span
                v-if="p.isRecommend"
                class="rounded-full bg-amber-soft px-2 py-0.5 text-caption2 font-medium text-amber-warm"
              >
                推荐
              </span>
            </div>
            <p class="mt-1 truncate text-caption1 text-ink-dim">
              #{{ p.id }} · {{ p.creator?.username || '未知作者' }}
              <span v-if="p.categoryName"> · {{ p.categoryName }}</span>
              · {{ relativeTime(p.createdAt) }}
            </p>
            <p class="mt-1 text-caption1 tabular-nums text-ink-dim">
              {{ fmt(p.viewCount) }} 浏览 · {{ fmt(p.likeCount) }} 赞 · {{ fmt(p.commentCount) }} 评论 ·
              {{ fmt(p.participantCount) }} 参与
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-1.5 sm:shrink-0 sm:justify-end">
          <AdminActionButton
            icon="star"
            :label="p.isRecommend ? '取消推荐' : '推荐'"
            :disabled="busyId === p.id"
            @click="toggleRecommend(p)"
          />
          <AdminActionButton
            :icon="p.isHidden ? 'check-circle' : 'x-circle'"
            :label="p.isHidden ? '恢复上线' : '下架'"
            :disabled="busyId === p.id"
            @click="toggleHidden(p)"
          />
          <AdminActionButton
            icon="trash-2"
            label="删除"
            danger
            :disabled="busyId === p.id"
            @click="askDelete(p)"
          />
        </div>
      </article>
    </div>

    <EmptyState
      v-else
      icon="lightbulb"
      :title="emptyTitle"
      :description="emptyDescription"
    >
      <button v-if="hasFilters" class="btn-secondary text-footnote" @click="resetFilters">
        清除筛选
      </button>
    </EmptyState>

    <Pagination
      v-if="!loading && !forbidden && !failed && total > pageSize"
      :page="page"
      :total="total"
      :page-size="pageSize"
      class="mt-6"
      @change="goPage"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { deleteAdminProject, getAdminProjects, updateAdminProject } from '@/api/admin'
import { confirm } from '@/composables/useConfirm'
import { toast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import AppIcon from '@/components/AppIcon.vue'
import AppSegmented from '@/components/AppSegmented.vue'
import EmptyState from '@/components/EmptyState.vue'
import Pagination from '@/components/Pagination.vue'
import AdminActionButton from '@/components/admin/AdminActionButton.vue'

const PAGE_SIZE = 10

const STATE_FILTERS = [
  { value: '', label: '全部' },
  { value: 'visible', label: '正常' },
  { value: 'hidden', label: '已下架' },
  { value: 'recommend', label: '推荐' }
]
const SORTS = [
  { value: 'new', label: '最新' },
  { value: 'hot', label: '最热' }
]

const projects = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const summary = ref({ total: 0, hidden: 0, recommend: 0 })

const state = ref('')
const sort = ref('new')
const searchInput = ref('')
const search = ref('')
const busyId = ref(null)

const loading = ref(true)
const failed = ref(false)
const forbidden = ref(false)

const fmt = (value) => Number(value || 0).toLocaleString('zh-CN')

const hasFilters = computed(() => Boolean(state.value || search.value))
const emptyTitle = computed(() => {
  if (search.value) return `没有匹配「${search.value}」的项目`
  if (state.value === 'hidden') return '没有已下架的项目'
  if (state.value === 'recommend') return '还没有推荐项目'
  return '这里还没有项目'
})
const emptyDescription = computed(() => {
  if (search.value) return '换个关键词，或清除筛选查看全部项目。'
  if (state.value === 'hidden') return '项目被下架后会出现在这里。'
  if (state.value === 'recommend') return '在项目行上点「推荐」，它就会出现在广场的推荐位。'
  return '还没有人发布项目。'
})

const load = async () => {
  loading.value = true
  failed.value = false
  forbidden.value = false
  const params = { page: page.value, pageSize: PAGE_SIZE }
  if (state.value) params.state = state.value
  if (search.value) params.search = search.value
  if (sort.value === 'hot') params.sort = 'hot'
  try {
    const res = await getAdminProjects(params)
    const data = res.data
    projects.value = data.projects
    total.value = data.total
    page.value = data.page
    pageSize.value = data.pageSize
    summary.value = data.summary
  } catch (error) {
    projects.value = []
    if (error.response?.status === 403) forbidden.value = true
    else failed.value = true
  } finally {
    loading.value = false
  }
}

// 状态变更后重拉当前页；若刚处理掉本页最后一条，回退一页，不要停在空页
const refresh = async () => {
  await load()
  if (!projects.value.length && page.value > 1 && !failed.value && !forbidden.value) {
    page.value -= 1
    await load()
  }
}

const applySearch = () => {
  search.value = searchInput.value.trim()
  page.value = 1
  load()
}

const clearSearch = () => {
  searchInput.value = ''
  search.value = ''
  page.value = 1
  load()
}

const switchState = (value) => {
  if (state.value === value) return
  state.value = value
  page.value = 1
  load()
}

const setSort = (value) => {
  if (sort.value === value) return
  sort.value = value
  page.value = 1
  load()
}

const resetFilters = () => {
  state.value = ''
  search.value = ''
  searchInput.value = ''
  page.value = 1
  load()
}

const goPage = (next) => {
  page.value = next
  load()
}

const toggleRecommend = async (p) => {
  if (busyId.value) return
  const next = !p.isRecommend
  busyId.value = p.id
  try {
    await updateAdminProject(p.id, { isRecommend: next })
    toast(next ? '已设为推荐项目' : '已取消推荐')
    await refresh()
  } catch {
    // 错误已由拦截器提示
  } finally {
    busyId.value = null
  }
}

const toggleHidden = async (p) => {
  if (busyId.value) return
  const next = !p.isHidden
  busyId.value = p.id
  try {
    await updateAdminProject(p.id, { isHidden: next })
    toast(next ? '项目已下架' : '项目已恢复上线')
    await refresh()
  } catch {
    // 错误已由拦截器提示
  } finally {
    busyId.value = null
  }
}

const askDelete = async (p) => {
  if (busyId.value) return
  const ok = await confirm({
    title: '删除项目？',
    message: `「${p.title}」将从广场与详情页消失（软删除，可在数据库中恢复），并写入审计日志。`,
    confirmLabel: '删除',
    destructive: true
  })
  if (!ok) return

  busyId.value = p.id
  try {
    await deleteAdminProject(p.id)
    toast('项目已删除')
    await refresh()
  } catch {
    // 错误已由拦截器提示
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div data-test="admin-overview">
    <div v-if="loading" class="grid gap-4 md:grid-cols-3">
      <div v-for="i in 3" :key="i" class="hig-card p-5">
        <div class="h-4 w-16 animate-pulse rounded bg-sand"></div>
        <div class="mt-5 grid grid-cols-2 gap-4">
          <div v-for="j in 4" :key="j" class="space-y-2">
            <div class="h-6 w-12 animate-pulse rounded bg-sand"></div>
            <div class="h-3 w-16 animate-pulse rounded bg-sand"></div>
          </div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else-if="forbidden"
      icon="lock"
      title="需要管理员权限"
      description="当前账号没有管理台权限，或权限刚被撤销。可以返回广场继续浏览。"
    >
      <router-link to="/" class="btn-primary">返回广场</router-link>
    </EmptyState>

    <EmptyState
      v-else-if="failed"
      icon="triangle-alert"
      title="概览加载失败"
      description="服务暂时不可用，请稍后重试。"
    >
      <button class="btn-primary" @click="load">重新加载</button>
    </EmptyState>

    <template v-else-if="data">
      <!-- 三组核心指标：成员 / 项目 / 互动 -->
      <div class="grid gap-4 md:grid-cols-3">
        <section v-for="group in groups" :key="group.key" class="hig-card overflow-hidden">
          <header class="flex items-center gap-3 border-b border-line/70 px-5 py-4">
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-10" :class="group.tone">
              <AppIcon :name="group.icon" class="h-[18px] w-[18px]" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-headline font-semibold text-ink">{{ group.title }}</p>
              <p class="text-caption1 text-ink-dim">{{ group.subtitle }}</p>
            </div>
          </header>
          <div class="grid grid-cols-2 gap-px bg-line">
            <div v-for="cell in group.cells" :key="cell.label" class="bg-cream px-4 py-3.5">
              <p
                class="text-title3 font-semibold tabular-nums"
                :class="cell.danger ? 'text-clay' : 'text-ink'"
              >
                {{ fmt(cell.value) }}
              </p>
              <p class="mt-0.5 text-caption1 text-ink-mid">{{ cell.label }}</p>
            </div>
          </div>
        </section>
      </div>

      <!-- 最近动态：注册与发布并列，管理动作单独占一行 -->
      <div class="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <div class="flex items-center justify-between px-1">
            <h2 class="hig-section-title">最近注册</h2>
            <router-link
              :to="{ path: '/admin', query: { tab: 'users' } }"
              class="text-caption1 text-pine transition-colors hover:text-pine-deep"
            >
              用户管理 ›
            </router-link>
          </div>

          <div v-if="data.recentUsers.length" class="hig-list mt-2">
            <router-link
              v-for="u in data.recentUsers"
              :key="u.id"
              :to="`/user/${u.id}`"
              class="hig-row hig-row-interactive"
            >
              <span class="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-caption1 font-bold text-pine-deep">
                <img v-if="u.avatar" :src="u.avatar" alt="" class="h-full w-full object-cover" />
                <template v-else>{{ (u.username || '友').slice(0, 1).toUpperCase() }}</template>
              </span>
              <span class="min-w-0 flex-1">
                <span class="flex flex-wrap items-center gap-1.5">
                  <span class="truncate text-subhead font-medium text-ink">{{ u.username }}</span>
                  <span
                    v-if="u.isAdmin"
                    class="rounded-full bg-amber-soft px-2 py-0.5 text-caption2 font-medium text-amber-warm"
                  >
                    管理员
                  </span>
                  <span
                    v-if="!u.status"
                    class="rounded-full bg-clay/10 px-2 py-0.5 text-caption2 font-medium text-clay"
                  >
                    已停用
                  </span>
                </span>
                <span class="mt-0.5 block truncate text-caption1 text-ink-dim">{{ u.email }}</span>
              </span>
              <span class="shrink-0 text-caption1 text-ink-dim">{{ relativeTime(u.createdAt) }}</span>
            </router-link>
          </div>
          <div v-else class="hig-card mt-2 px-5 py-8 text-center text-footnote text-ink-mid">
            还没有注册用户。
          </div>
        </section>

        <section>
          <div class="flex items-center justify-between px-1">
            <h2 class="hig-section-title">最近发布</h2>
            <router-link
              :to="{ path: '/admin', query: { tab: 'projects' } }"
              class="text-caption1 text-pine transition-colors hover:text-pine-deep"
            >
              项目管理 ›
            </router-link>
          </div>

          <div v-if="data.recentProjects.length" class="hig-list mt-2">
            <component
              :is="p.isHidden ? 'div' : 'router-link'"
              v-for="p in data.recentProjects"
              :key="p.id"
              v-bind="p.isHidden ? {} : { to: `/project/${p.id}` }"
              class="hig-row"
              :class="p.isHidden ? '' : 'hig-row-interactive'"
            >
              <span class="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-[7px] bg-sand text-ink-dim">
                <img v-if="p.coverImage" :src="p.coverImage" alt="" class="h-full w-full object-cover" />
                <AppIcon v-else name="image" class="h-4 w-4" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="flex flex-wrap items-center gap-1.5">
                  <span class="truncate text-subhead font-medium text-ink">{{ p.title }}</span>
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
                </span>
                <span class="mt-0.5 block truncate text-caption1 text-ink-dim">
                  {{ p.creator?.username || '未知作者' }}
                  <span v-if="p.categoryName"> · {{ p.categoryName }}</span>
                </span>
              </span>
              <span class="shrink-0 text-caption1 text-ink-dim">{{ relativeTime(p.createdAt) }}</span>
            </component>
          </div>
          <div v-else class="hig-card mt-2 px-5 py-8 text-center text-footnote text-ink-mid">
            还没有发布项目。
          </div>
        </section>
      </div>

      <!-- 最近管理动作：来自 activity_logs 的 admin.* 白名单 -->
      <section class="mt-8">
        <div class="flex items-center justify-between px-1">
          <h2 class="hig-section-title">最近管理动作</h2>
          <router-link to="/security" class="text-caption1 text-pine transition-colors hover:text-pine-deep">
            查看我的操作记录 ›
          </router-link>
        </div>

        <div v-if="data.recentAdminActivity.length" class="hig-list mt-2">
          <article
            v-for="log in data.recentAdminActivity"
            :key="log.id"
            class="flex items-start gap-3 px-4 py-3.5"
          >
            <span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-soft text-amber-warm">
              <AppIcon :name="actionIcon(log.action)" class="h-4 w-4" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="break-words text-subhead leading-snug text-ink">{{ log.summary }}</p>
              <p class="mt-1 text-caption1 text-ink-dim">{{ relativeTime(log.createdAt) }}</p>
            </div>
          </article>
        </div>
        <div v-else class="hig-card mt-2 px-5 py-8 text-center text-footnote text-ink-mid">
          还没有管理操作记录。下架项目、停用账号或发送公告后会显示在这里。
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAdminOverview } from '@/api/admin'
import { relativeTime } from '@/utils/time'
import { actionIcon } from '@/utils/audit'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'

const data = ref(null)
const loading = ref(true)
const failed = ref(false)
const forbidden = ref(false)

const fmt = (value) => Number(value || 0).toLocaleString('zh-CN')

const groups = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    {
      key: 'users',
      title: '成员',
      subtitle: `共 ${fmt(d.users.total)} 个账号`,
      icon: 'users',
      tone: 'bg-pine-soft text-pine-deep',
      cells: [
        { label: '正常', value: d.users.active },
        { label: '已停用', value: d.users.disabled, danger: d.users.disabled > 0 },
        { label: '管理员', value: d.users.admins },
        { label: '注册总数', value: d.users.total }
      ]
    },
    {
      key: 'projects',
      title: '项目',
      subtitle: `共 ${fmt(d.projects.total)} 个项目`,
      icon: 'lightbulb',
      tone: 'bg-amber-soft text-amber-warm',
      cells: [
        { label: '正常上线', value: Math.max(0, d.projects.total - d.projects.hidden) },
        { label: '已下架', value: d.projects.hidden, danger: d.projects.hidden > 0 },
        { label: '推荐中', value: d.projects.recommend },
        { label: '本周新增', value: d.projects.newThisWeek }
      ]
    },
    {
      key: 'interactions',
      title: '互动',
      subtitle: `共 ${fmt(d.comments.total)} 条评论`,
      icon: 'message-circle',
      tone: 'bg-green/10 text-green',
      cells: [
        { label: '评论总数', value: d.comments.total },
        { label: '本周评论', value: d.comments.newThisWeek },
        { label: '站内通知', value: d.notifications.total },
        { label: '未读通知', value: d.notifications.unread }
      ]
    }
  ]
})

const load = async () => {
  loading.value = true
  failed.value = false
  forbidden.value = false
  try {
    const res = await getAdminOverview()
    data.value = res.data
  } catch (error) {
    if (error.response?.status === 403) forbidden.value = true
    else failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

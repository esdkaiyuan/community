<template>
  <div class="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    <!-- 骨架 -->
    <div v-if="loading" class="space-y-5">
      <div class="skeleton h-5 w-40"></div>
      <div class="skeleton h-[420px] w-full !rounded-[22px]"></div>
      <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div class="skeleton h-72 w-full"></div>
        <div class="skeleton h-72 w-full"></div>
      </div>
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
      <!-- 滚动玻璃条：滚过档案头图后浮现 -->
      <transition name="bar">
        <div
          v-if="scrolled"
          class="fixed inset-x-0 top-14 z-40 border-b border-[color:var(--glass-border)] bg-[color:var(--glass-nav)] backdrop-blur-xl backdrop-saturate-150"
        >
          <div class="mx-auto flex h-12 max-w-5xl items-center gap-3 px-4 sm:px-6">
            <span class="min-w-0 flex-1 truncate font-mono text-caption1 text-ink-dim">FILE {{ fileNo }}</span>
            <span class="hidden min-w-0 max-w-[16rem] truncate text-footnote font-semibold text-ink sm:inline">{{ project.title }}</span>
            <!-- 整项目加密时，动作按钮一律收起：内容都没解锁，点赞/参与没有意义 -->
            <template v-if="!project.locked">
              <button
                class="btn-ghost !px-3 !py-1.5 text-footnote"
                :class="liked ? '!text-clay' : ''"
                :disabled="acting"
                :aria-label="liked ? '取消点赞' : '点赞'"
                @click="handleLike"
              >
                <AppIcon name="heart" class="h-4 w-4" />
                {{ project.likeCount }}
              </button>
              <button
                class="btn-ghost !px-3 !py-1.5 text-footnote"
                title="查看评论"
                @click="scrollToComments"
              >
                <AppIcon name="message-circle" class="h-4 w-4" />
                {{ commentCount }}
              </button>
              <button
                class="btn-ghost !px-3 !py-1.5 text-footnote"
                :class="[favorited ? '!text-pine' : '', { 'fav-pop': favoritePulse }]"
                :title="favorited ? '取消收藏' : '收藏项目'"
                :disabled="acting"
                @click="handleFavorite"
              >
                <AppIcon name="bookmark" class="h-4 w-4" />
              </button>
              <button
                class="!px-4 !py-1.5 text-footnote"
                :class="participated ? 'btn-secondary' : 'btn-primary'"
                :disabled="acting"
                @click="handleParticipate"
              >
                {{ participated ? '已参与' : '参与共创' }}
              </button>
            </template>
          </div>
        </div>
      </transition>

      <!-- 面包屑 -->
      <nav class="mb-5 flex min-w-0 items-center gap-1.5 text-footnote text-ink-dim">
        <router-link to="/" class="shrink-0 transition-colors hover:text-pine">项目广场</router-link>
        <span class="shrink-0">/</span>
        <router-link
          v-if="project.categoryName"
          :to="{ path: '/', query: { categoryId: project.categoryId } }"
          class="hidden shrink-0 transition-colors hover:text-pine sm:inline"
        >
          {{ project.categoryName }}
        </router-link>
        <span v-if="project.categoryName" class="hidden shrink-0 sm:inline">/</span>
        <span class="truncate text-ink-mid">{{ project.title }}</span>
      </nav>

      <!-- ============ 项目档案头图 ============ -->
      <section class="project-hero" data-test="detail-hero">
        <div class="cyber-grid-light project-hero__grid" aria-hidden="true"></div>
        <span class="project-hero__watermark" aria-hidden="true">{{ fileNo }}</span>

        <div class="relative grid gap-8 p-6 sm:p-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-center lg:gap-10 lg:p-10">
          <!-- 封面（移动端在前，桌面端在右） -->
          <div class="order-1 lg:order-2">
            <div class="hero-cover group">
              <div class="relative aspect-[16/9] overflow-hidden">
                <img
                  v-if="project.coverImage && !imgFailed"
                  :src="project.coverImage"
                  :alt="project.title"
                  class="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
                  @error="imgFailed = true"
                />
                <div v-else class="flex h-full w-full items-center justify-center" :style="{ background: placeholder.bg }">
                  <span class="select-none font-display text-8xl font-bold opacity-90" :style="{ color: placeholder.fg }">
                    {{ project.title?.slice(0, 1) || '创' }}
                  </span>
                </div>

                <div class="absolute inset-0 bg-gradient-to-t from-[#08090c]/55 via-transparent to-transparent"></div>

                <div class="absolute left-3 top-3 flex flex-wrap gap-1.5">
                  <span v-if="project.isRecommend" class="hero-badge">
                    <AppIcon name="star" class="h-3 w-3 text-amber-warm" />编辑推荐
                  </span>
                  <span v-if="project.isHot" class="hero-badge">
                    <AppIcon name="flame" class="h-3 w-3 text-clay" />热门
                  </span>
                </div>

                <span class="absolute bottom-3 left-3 font-mono text-caption2 uppercase tracking-[0.14em] text-white/75">
                  {{ project.categoryName || 'UNCATEGORIZED' }}
                </span>
              </div>
              <span class="hero-cover__tab" aria-hidden="true">SKETCH / {{ fileNo }}</span>
            </div>
          </div>

          <!-- 档案正文 -->
          <div class="order-2 min-w-0 lg:order-1">
            <div class="flex flex-wrap items-center gap-2.5">
              <span class="hero-file">FILE / {{ fileNo }}</span>
              <span class="hero-status" :class="statusInfo.tone === 'closed' ? 'hero-status--closed' : 'hero-status--open'">
                <span class="hero-status__dot"></span>
                {{ statusInfo.label }}
              </span>
            </div>

            <p v-if="project.categoryName" class="mt-5 font-mono text-caption1 uppercase tracking-[0.2em] text-[#5BE0EB]/80">
              {{ project.categoryName }}
            </p>
            <h1 class="mt-2 max-w-[18ch] text-balance font-brand text-[clamp(2.1rem,4.4vw,3.6rem)] font-bold leading-[1.12] tracking-[-0.01em] text-white">
              {{ project.title }}
            </h1>

            <p
              class="mt-4 line-clamp-3 max-w-xl text-subhead leading-[1.85]"
              :class="project.locked ? 'flex items-center gap-2 text-white/45' : 'text-white/[0.62]'"
              data-test="detail-lede"
            >
              <AppIcon v-if="project.locked" name="lock" class="h-4 w-4 shrink-0" />
              {{ heroLede }}
            </p>

            <div class="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-footnote text-white/55" data-test="detail-meta">
              <span>发布于 {{ relativeTime(project.createdAt) }}</span>
              <span
                v-if="isExpired"
                class="inline-flex items-center gap-1 text-[#FF9F9A]"
                data-test="detail-expired"
              >
                <AppIcon name="lock" class="h-3.5 w-3.5" />
                已于 {{ endDateShort }} 截止
              </span>
              <span v-else-if="endDateShort" class="inline-flex items-center gap-1 text-white/55">
                <AppIcon name="history" class="h-3.5 w-3.5" />
                截止 {{ endDateShort }}
              </span>
            </div>

            <a
              v-if="repoUrl"
              :href="repoUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-3 inline-flex items-center gap-1.5 text-footnote text-white/65 underline decoration-white/25 underline-offset-4 transition-colors hover:text-[#5BE0EB] hover:decoration-[#5BE0EB]/60"
              data-test="detail-repo"
            >
              <AppIcon name="external-link" class="h-4 w-4" />
              查看仓库
            </a>
            <!-- 仓库加密：仓库地址没有下发，这里换成一个就地展开的解锁入口 -->
            <button
              v-else-if="project.repoLocked && !project.locked"
              type="button"
              class="mt-3 inline-flex items-center gap-1.5 text-footnote text-[#5BE0EB] underline decoration-[#5BE0EB]/30 underline-offset-4 transition-colors hover:decoration-[#5BE0EB]/70"
              data-test="detail-repo-locked"
              @click="showRepoUnlock = !showRepoUnlock"
            >
              <AppIcon name="lock" class="h-4 w-4" />
              {{ showRepoUnlock ? '收起密码输入' : '仓库地址已加密 · 输入密码查看' }}
            </button>

            <ProjectUnlockForm
              v-if="showRepoUnlock && project.repoLocked && !project.locked"
              :project-id="project.id"
              mode="repo"
              class="mt-4 max-w-xl"
              @unlocked="handleRepoUnlocked"
            />

            <div v-if="project.tags?.length" class="mt-5 flex flex-wrap gap-2">
              <router-link
                v-for="tag in project.tags"
                :key="tag"
                :to="{ path: '/', query: { tag } }"
                class="hero-tag"
                data-test="detail-tag"
                :title="`看看「${tag}」标签下的项目`"
              >
                # {{ tag }}
              </router-link>
            </div>
          </div>
        </div>

        <!-- 参数条：档案式 ledger -->
        <div class="project-ledger" data-test="detail-spec">
          <div v-for="item in specItems" :key="item.label" class="project-ledger__cell" :data-test="item.test || undefined">
            <p class="font-mono text-title3 font-semibold tabular-nums text-white">{{ item.value }}</p>
            <p class="mt-1 font-mono text-caption2 uppercase tracking-[0.14em] text-white/50">{{ item.label }}</p>
          </div>
        </div>
      </section>

      <!-- 整项目加密：正文、侧栏、推荐与评论全部收起，只留一个解锁入口 -->
      <section v-if="project.locked" class="mt-6" data-test="detail-locked">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-12 border border-dashed border-line bg-sand/40 px-4 py-3">
          <p class="text-caption1 leading-relaxed text-ink-dim">
            该项目的介绍、标签、仓库地址与共创伙伴都已加密。
          </p>
          <span class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">LOCKED / PASSWORD REQUIRED</span>
        </div>
        <ProjectUnlockForm :project-id="project.id" mode="project" @unlocked="handleProjectUnlocked" />
      </section>

      <!-- ============ 正文 + 侧栏 ============ -->
      <div v-if="!project.locked" class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div class="order-2 min-w-0 lg:order-1">
          <article v-reveal class="dossier-card">
            <header class="flex items-end justify-between gap-3 border-b border-line pb-4">
              <div>
                <p class="mono-label">01 / BRIEF</p>
                <h2 class="mt-1.5 font-brand text-title2 font-bold text-ink">项目介绍</h2>
              </div>
              <span class="shrink-0 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">
                {{ descriptionParagraphs.length }} PARAGRAPHS
              </span>
            </header>

            <div v-if="descriptionParagraphs.length" class="mt-6 space-y-5">
              <p
                v-for="(para, i) in descriptionParagraphs"
                :key="i"
                :class="i === 0 ? 'text-headline font-medium leading-[1.9] text-ink' : 'text-subhead leading-[1.95] text-ink-mid'"
              >
                {{ para }}
              </p>
            </div>
            <p v-else class="mt-6 text-subhead leading-relaxed text-ink-mid">
              发起人还没有写下详细介绍，可以在评论区直接聊聊你的想法。
            </p>

            <!-- 页脚：开放状态 / 仓库入口，补全资料感 -->
            <footer class="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <span class="inline-flex items-center gap-2 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">
                <span class="h-1.5 w-1.5 rounded-full" :class="isExpired ? 'bg-ink-dim/50' : 'bg-green'"></span>
                {{ isExpired ? '招募已结束' : '持续招募共创伙伴' }}
              </span>
              <a
                v-if="repoUrl"
                :href="repoUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 text-caption1 text-ink-mid transition-colors hover:text-pine"
              >
                查看仓库
                <AppIcon name="external-link" class="h-3.5 w-3.5" />
              </a>
            </footer>
          </article>
        </div>

        <aside class="order-1 space-y-5 lg:order-2 lg:sticky lg:top-24 lg:self-start">
          <!-- 行动卡 -->
          <div class="action-dock">
            <div class="flex items-center justify-between">
              <p class="mono-label">SUPPORT</p>
              <span class="font-mono text-caption1 tabular-nums text-ink-dim">{{ project.participantCount ?? 0 }} JOINED</span>
            </div>

            <button
              class="mt-4 w-full !py-3"
              :class="participated ? 'btn-secondary' : 'btn-primary'"
              :disabled="acting"
              @click="handleParticipate"
            >
              <span v-if="participated" class="inline-flex items-center gap-1.5"><AppIcon name="check" class="h-4 w-4" />已参与 · 点击退出</span>
              <span v-else class="inline-flex items-center gap-1.5"><AppIcon name="users" class="h-4 w-4" />参与共创</span>
            </button>

            <div class="mt-2 grid grid-cols-2 gap-2">
              <button
                class="w-full !py-2.5"
                :class="liked ? 'btn-secondary !border-clay/40 !text-clay' : 'btn-secondary'"
                :disabled="acting"
                @click="handleLike"
              >
                <AppIcon name="heart" class="h-4 w-4" />
                {{ liked ? '已点赞' : '点赞' }} · {{ project.likeCount ?? 0 }}
              </button>
              <button
                class="w-full !py-2.5"
                :class="[favorited ? 'btn-secondary !border-pine/40 !text-pine' : 'btn-secondary', { 'fav-pop': favoritePulse }]"
                :disabled="acting"
                @click="handleFavorite"
              >
                <AppIcon name="bookmark" class="h-4 w-4" />
                {{ favorited ? '已收藏' : '收藏' }}
              </button>
            </div>

            <!-- 创建者操作 -->
            <div v-if="isOwner" class="mt-4 border-t border-line pt-4">
              <p class="mb-2 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">OWNER CONTROLS</p>
              <div class="space-y-2">
                <router-link
                  :to="`/project/${project.id}/edit`"
                  class="btn-secondary w-full !py-2.5 text-footnote"
                  data-test="detail-edit"
                >
                  <AppIcon name="pencil" class="h-4 w-4" />
                  编辑项目
                </router-link>
                <button class="btn-ghost w-full !py-2.5 text-footnote !text-clay hover:!bg-clay/10" :disabled="acting" @click="handleDelete">
                  删除项目
                </button>
              </div>
            </div>
          </div>

          <!-- 发起人 -->
          <div class="initiator-card">
            <div class="flex items-center justify-between">
              <p class="mono-label">INITIATOR</p>
              <router-link
                v-if="project.creator?.id"
                :to="`/user/${project.creator.id}`"
                class="font-mono text-caption2 uppercase tracking-[0.12em] text-pine transition-opacity hover:opacity-70"
              >
                PROFILE ↗
              </router-link>
            </div>

            <div class="mt-3 flex items-center gap-3">
              <span class="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-callout font-bold text-pine-deep">
                <img v-if="project.creator?.avatar" :src="project.creator.avatar" alt="" class="h-full w-full object-cover" />
                <template v-else>{{ (project.creator?.username || '友').slice(0, 1).toUpperCase() }}</template>
              </span>
              <div class="min-w-0 flex-1">
                <router-link
                  v-if="project.creator?.id"
                  :to="`/user/${project.creator.id}`"
                  data-test="detail-creator"
                  class="block truncate text-subhead font-semibold text-ink transition-colors hover:text-pine"
                >
                  {{ project.creator?.username || '匿名共创者' }}
                </router-link>
                <p v-else class="truncate text-subhead font-semibold text-ink">匿名共创者</p>
                <p class="mt-0.5 font-mono text-caption2 uppercase tracking-[0.1em] text-ink-dim">项目发起人</p>
              </div>
            </div>

            <router-link
              v-if="project.creator?.id"
              :to="`/user/${project.creator.id}`"
              class="mt-4 inline-flex w-full items-center justify-between rounded-10 bg-sand/70 px-3.5 py-2.5 text-footnote font-medium text-ink transition-colors hover:bg-sand"
              data-test="detail-creator-home"
            >
              看看 TA 的其他项目
              <AppIcon name="chevronRight" class="h-3.5 w-3.5 text-ink-dim" />
            </router-link>
          </div>

          <!-- 共创伙伴：头像堆叠 + 完整名单 -->
          <ProjectParticipants
            :project-id="project.id"
            :participants="project.participants || []"
            :count="project.participantCount || 0"
          />
        </aside>
      </div>

      <!-- 看完继续逛 -->
      <RelatedProjects v-if="!project.locked" :project-id="project.id" />

      <!-- 评论区 -->
      <CommentSection
        v-if="!project.locked"
        :project-id="project.id"
        :creator-id="project.creator?.id"
        @change="commentCount = $event"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as projectApi from '@/api/project'
import { useUserStore } from '@/store/user'
import { getUserFlag, setUserFlag } from '@/utils/storage'
import { toast } from '@/composables/useToast'
import { useFavoritePulse } from '@/composables/useFavoritePulse'
import { confirm } from '@/composables/useConfirm'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/AppIcon.vue'
import CommentSection from '@/components/CommentSection.vue'
import ProjectParticipants from '@/components/ProjectParticipants.vue'
import ProjectUnlockForm from '@/components/ProjectUnlockForm.vue'
import RelatedProjects from '@/components/RelatedProjects.vue'
import { coverPalette } from '@/utils/placeholder'
import { relativeTime } from '@/utils/time'

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
const favorited = ref(false)

// 仓库加密的就地解锁面板：只在用户点入口后展开，避免一进页面就弹密码框
const showRepoUnlock = ref(false)

// 收藏成功的一次性微动效（动画本体在 style.css 的 .fav-pop）
const { favoritePulse, playFavoritePulse } = useFavoritePulse()

// 评论总数（由评论区组件上报，供顶部玻璃操作条展示）
const commentCount = ref(0)

const scrollToComments = () => {
  document.getElementById('comments')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// 项目介绍分层：按空行/换行拆段，首段作为导语强调
const descriptionParagraphs = computed(() =>
  (project.value?.description || '')
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
)

// 头图导语：取介绍第一段；过长的段落交给 CSS line-clamp 收口
// 整项目加密时 description 已被服务端清空，这里必须换成明确的锁定说明，
// 否则会退化成「发起人还没写介绍」的假象
const heroLede = computed(() => {
  if (project.value?.locked) return '这是一个加密项目，输入访问密码后可查看完整介绍与共创伙伴。'
  return descriptionParagraphs.value[0] || '发起人正在整理项目介绍，欢迎先在评论区聊聊你的想法。'
})

// 档案编号：把数据库自增 id 变成四位数的卷宗号
const fileNo = computed(() => String(project.value?.id ?? 0).padStart(4, '0'))

const statusInfo = computed(() => {
  if (isExpired.value) return { label: '已截止', tone: 'closed' }
  if (project.value?.endDate) return { label: '招募中', tone: 'open' }
  return { label: '持续开放', tone: 'open' }
})

// 同步点赞/参与状态：优先采用服务端权威数据，未登录时退回本地标记
const syncFlags = () => {
  const uid = userStore.userId
  const pid = route.params.id
  liked.value = project.value?.liked ?? getUserFlag('like', uid, pid)
  participated.value = project.value?.participated ?? getUserFlag('join', uid, pid)
  favorited.value = project.value?.favorited ?? getUserFlag('favorite', uid, pid)
}

const isOwner = computed(
  () => userStore.isLoggedIn && project.value?.creator?.id === userStore.userId
)

// 占位配色统一来自 utils/placeholder —— 卡片、相关推荐、详情页三处必须同源，
// 否则同一个项目在不同页面会显示不同颜色的封面
const placeholder = computed(() => coverPalette(project.value?.id))

// 规格条用短日期。跨年的项目必须带年份——只写「5 月 9 日」会让人以为是今年，
// 而库里确实躺着 2026-05 的种子数据。当年内省略年份，保持参数表的克制。
const createdShort = computed(() => {
  if (!project.value?.createdAt) return '—'
  const d = new Date(project.value.createdAt)
  const md = `${d.getMonth() + 1} 月 ${d.getDate()} 日`
  return d.getFullYear() === new Date().getFullYear() ? md : `${d.getFullYear()} 年 ${md}`
})

// 仓库地址：只认 http/https（`javascript:` 是 XSS 执行入口）
const repoUrl = computed(() => {
  const raw = project.value?.repositoryUrl
  if (typeof raw !== 'string') return ''
  const url = raw.trim()
  if (!/^https?:\/\//i.test(url)) return ''
  return url
})

// 「已截止」判定：只看日期部分，避免 new Date('YYYY-MM-DD') 被当成 UTC 午夜
const isExpired = computed(() => {
  const raw = project.value?.endDate
  if (typeof raw !== 'string') return false
  const m = raw.trim().match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return false
  const today = new Date()
  const todayKey = today.getFullYear() * 10000 + (today.getMonth() + 1) * 100 + today.getDate()
  const endKey = Number(m[1]) * 10000 + Number(m[2]) * 100 + Number(m[3])
  return endKey < todayKey
})

const endDateShort = computed(() => {
  const raw = project.value?.endDate
  if (typeof raw !== 'string') return ''
  const m = raw.trim().match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return ''
  return `${m[1]} 年 ${Number(m[2])} 月 ${Number(m[3])} 日`
})

// 档案参数条。data-test 逐格固定：端到端脚本按 detail-views / detail-created
// 直接取格子里的读数（首个子元素 p 是数值）。
const specItems = computed(() => [
  { label: '共创伙伴', value: project.value?.participantCount ?? 0 },
  { label: '收获点赞', value: project.value?.likeCount ?? 0 },
  { label: '浏览次数', value: project.value?.viewCount ?? 0, test: 'detail-views' },
  { label: '发布日期', value: createdShort.value, test: 'detail-created' }
])

// 滚过封面后浮现顶部玻璃操作条
const scrolled = ref(false)
const onScroll = () => {
  scrolled.value = window.scrollY > 420
}
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

const requireLogin = () => {
  if (userStore.isLoggedIn) return true
  toast('请先登录', 'info')
  router.push({ name: 'Login', query: { redirect: route.fullPath } })
  return false
}

const fetchDetail = async () => {
  loading.value = true
  notFound.value = false
  showRepoUnlock.value = false
  try {
    const res = await projectApi.getProject(route.params.id)
    project.value = res.data
    syncFlags()
    // 从通知跳转过来时定位到评论区
    if (route.hash === '#comments') {
      await nextTick()
      setTimeout(() => scrollToComments(), 300)
    }
  } catch (e) {
    if (e.response?.status === 404) notFound.value = true
  } finally {
    loading.value = false
  }
}

// 仓库解锁：把地址并回当前项目并收起面板，页面其余部分保持原样
const handleRepoUnlocked = (data) => {
  if (!project.value) return
  project.value.repositoryUrl = data?.repositoryUrl || null
  project.value.repoLocked = false
  showRepoUnlock.value = false
}

// 整项目解锁：接口回的是完整详情，直接替换即可让正文、侧栏、评论区一起出现
const handleProjectUnlocked = (data) => {
  if (!data?.project) return
  project.value = data.project
  syncFlags()
  commentCount.value = data.project.commentCount || 0
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

// 参与 / 退出后即时更新共创伙伴堆叠，不必等下一次详情请求
const addSelfToParticipants = () => {
  const list = project.value?.participants
  if (!Array.isArray(list) || list.some((p) => p.id === userStore.userId)) return
  list.push({
    id: userStore.userId,
    username: userStore.username || '我',
    avatar: userStore.avatar || '',
    role: 'member',
    joinedAt: new Date().toISOString()
  })
}
const removeSelfFromParticipants = () => {
  const list = project.value?.participants
  if (!Array.isArray(list)) return
  project.value.participants = list.filter((p) => p.id !== userStore.userId)
}

const handleParticipate = async () => {
  if (!requireLogin() || acting.value) return
  acting.value = true
  try {
    if (participated.value) {
      const res = await projectApi.cancelParticipate(project.value.id)
      project.value.participantCount = res.data.participantCount
      participated.value = false
      removeSelfFromParticipants()
      setUserFlag('join', userStore.userId, project.value.id, false)
      toast('已退出该项目', 'info')
    } else {
      const res = await projectApi.participateProject(project.value.id)
      project.value.participantCount = res.data.participantCount
      participated.value = true
      addSelfToParticipants()
      setUserFlag('join', userStore.userId, project.value.id, true)
      toast('参与成功，欢迎加入共创！')
    }
  } catch (e) {
    const msg = e.response?.data?.message || ''
    if (msg.includes('已参与')) {
      participated.value = true
      addSelfToParticipants()
      setUserFlag('join', userStore.userId, project.value.id, true)
    } else if (msg.includes('未参与')) {
      participated.value = false
      removeSelfFromParticipants()
      setUserFlag('join', userStore.userId, project.value.id, false)
    }
  } finally {
    acting.value = false
  }
}

const handleFavorite = async () => {
  if (!requireLogin() || acting.value) return
  acting.value = true
  try {
    if (favorited.value) {
      await projectApi.unfavoriteProject(project.value.id)
      favorited.value = false
      setUserFlag('favorite', userStore.userId, project.value.id, false)
      toast('已取消收藏', 'info')
    } else {
      await projectApi.favoriteProject(project.value.id)
      favorited.value = true
      setUserFlag('favorite', userStore.userId, project.value.id, true)
      playFavoritePulse()
      toast('已加入收藏，可在个人中心查看')
    }
  } catch (e) {
    // 本地状态与服务端不一致时纠正（如换设备后重复收藏）
    const msg = e.response?.data?.message || ''
    if (msg.includes('已收藏')) {
      favorited.value = true
      setUserFlag('favorite', userStore.userId, project.value.id, true)
    } else if (msg.includes('尚未收藏')) {
      favorited.value = false
      setUserFlag('favorite', userStore.userId, project.value.id, false)
    }
  } finally {
    acting.value = false
  }
}

// 破坏性操作走 HIG 警告框而不是原生 confirm
const handleDelete = async () => {
  const ok = await confirm({
    title: '删除这个项目？',
    message: '项目及其下的评论会一并删除，此操作不可恢复。',
    confirmLabel: '删除',
    destructive: true
  })
  if (!ok) return
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
/* ============ 档案头图：深色工程纸 + 手绘错位影 ============ */
.project-hero {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border: 1.5px solid rgb(var(--c-ink) / 0.42);
  border-radius: 22px 26px 20px 28px / 26px 20px 28px 22px;
  background: #0a0c10;
  box-shadow: 6px 6px 0 rgba(91, 224, 235, 0.2);
}

.project-hero__grid {
  position: absolute;
  inset: 0;
  opacity: 0.5;
  pointer-events: none;
  -webkit-mask-image: radial-gradient(ellipse 88% 80% at 62% 30%, #000 18%, transparent 82%);
  mask-image: radial-gradient(ellipse 88% 80% at 62% 30%, #000 18%, transparent 82%);
}

.project-hero__watermark {
  position: absolute;
  right: 1.5rem;
  bottom: 3.25rem;
  z-index: 0;
  font-family: 'SF Pro Display', -apple-system, sans-serif;
  font-size: 8.5rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.06em;
  color: rgba(255, 255, 255, 0.04);
  pointer-events: none;
  user-select: none;
}

.hero-file {
  @apply inline-flex items-center rounded-full px-3 py-1 font-mono text-caption2 uppercase tracking-[0.16em];
  color: rgba(246, 241, 229, 0.6);
  border: 1px solid rgba(246, 241, 229, 0.14);
}

.hero-status {
  @apply inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-mono text-caption2 font-medium uppercase tracking-[0.12em];
  border: 1px solid rgba(91, 224, 235, 0.28);
  background: rgba(91, 224, 235, 0.08);
  color: #bff5fa;
}
.hero-status--open .hero-status__dot {
  @apply h-1.5 w-1.5 rounded-full;
  background: #5be0eb;
  box-shadow: 0 0 0 3px rgba(91, 224, 235, 0.16);
}
.hero-status--closed {
  border-color: rgba(215, 0, 21, 0.35);
  background: rgba(215, 0, 21, 0.14);
  color: #ff9f9a;
}
.hero-status--closed .hero-status__dot {
  @apply h-1.5 w-1.5 rounded-full;
  background: #ff9f9a;
}

.hero-badge {
  @apply inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-caption2 font-medium text-white;
  border: 1px solid rgba(91, 224, 235, 0.24);
  background: rgba(8, 9, 12, 0.72);
  backdrop-filter: blur(8px);
}

.hero-tag {
  @apply inline-flex items-center rounded-full px-3 py-1 font-mono text-caption2 uppercase tracking-[0.06em] transition-colors;
  color: rgba(246, 241, 229, 0.72);
  border: 1px solid rgba(246, 241, 229, 0.16);
  background: rgba(246, 241, 229, 0.05);
}
.hero-tag:hover {
  color: #0a0c10;
  border-color: rgba(91, 224, 235, 0.7);
  background: #5be0eb;
}

/* 封面：纸质照片 + 手绘框 + 右上角档案标签 */
.hero-cover {
  position: relative;
  border-radius: 16px 20px 14px 22px / 20px 14px 22px 16px;
  border: 1.5px solid rgba(246, 241, 229, 0.28);
  background: #12141a;
  box-shadow: 8px 9px 0 rgba(91, 224, 235, 0.16);
  transform: rotate(0.6deg);
}
.hero-cover > div {
  border-radius: inherit;
}
.hero-cover__tab {
  @apply absolute -top-3 right-4 font-mono text-caption2 uppercase tracking-[0.14em];
  padding: 0.25rem 0.6rem;
  color: #0a0c10;
  background: #5be0eb;
  border-radius: 3px 8px 3px 8px;
  transform: rotate(-2deg);
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.25);
}

/* 参数条：档案底部的登记表 */
.project-ledger {
  @apply grid grid-cols-2 sm:grid-cols-4;
  position: relative;
  border-top: 1px solid rgba(246, 241, 229, 0.12);
  background: rgba(246, 241, 229, 0.02);
}
.project-ledger__cell {
  @apply px-5 py-4;
}
.project-ledger__cell + .project-ledger__cell {
  border-left: 1px solid rgba(246, 241, 229, 0.09);
}
.project-ledger__cell:nth-child(3) {
  border-left: none;
}
@media (min-width: 640px) {
  .project-ledger__cell:nth-child(3) {
    border-left: 1px solid rgba(246, 241, 229, 0.09);
  }
}
@media (max-width: 639px) {
  .project-ledger__cell:nth-child(n + 3) {
    border-top: 1px solid rgba(246, 241, 229, 0.09);
  }
}

/* 正文卡片：白纸 + 极轻的档案折角 */
.dossier-card {
  @apply bg-cream p-6 sm:p-8;
  border: 1.5px solid rgb(var(--c-ink) / 0.13);
  border-radius: 18px 22px 16px 24px / 22px 16px 24px 18px;
  box-shadow: 3px 4px 0 rgb(var(--c-ink) / 0.05);
}

/* 侧栏行动卡 */
.action-dock {
  @apply bg-cream p-5;
  border: 1.5px solid rgb(var(--c-ink) / 0.13);
  border-radius: 16px 20px 14px 22px / 20px 14px 22px 16px;
  box-shadow: 3px 4px 0 rgb(var(--c-ink) / 0.05);
}

.initiator-card {
  @apply bg-cream p-5;
  border: 1.5px solid rgb(var(--c-line));
  border-radius: 14px 18px 12px 20px / 18px 12px 20px 14px;
  box-shadow: 2px 3px 0 rgb(var(--c-ink) / 0.04);
}

.bar-enter-active,
.bar-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.bar-enter-from,
.bar-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .hero-cover {
    transform: none;
  }
  .bar-enter-active,
  .bar-leave-active {
    transition: none;
  }
}
</style>

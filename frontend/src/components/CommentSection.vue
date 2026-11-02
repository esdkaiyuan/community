<template>
  <section id="comments" class="mt-14 scroll-mt-24">
    <!-- 分区标题：App Store「评分与评论」式大标题 + 发丝线分隔 -->
    <div class="flex items-end justify-between gap-4">
      <div>
        <p class="mono-label mb-1">DISCUSSION</p>
        <h2 class="text-title2 font-semibold tracking-tight text-ink sm:text-title1">评论</h2>
      </div>
      <span class="pb-1 text-footnote tabular-nums text-ink-dim">{{ total ? `${total} 条` : '' }}</span>
    </div>
    <div class="mt-4 h-px bg-line"></div>

    <!-- 输入区（已登录）：聚焦时描边点亮，@ 候选浮在输入框下方 -->
    <div v-if="userStore.isLoggedIn" class="comment-composer card mt-6 p-4 sm:p-5">
      <div class="flex gap-3.5">
        <Avatar :user="selfUser" size="md" />
        <div class="min-w-0 flex-1">
          <textarea
            ref="composerInput"
            v-model="draft"
            rows="2"
            maxlength="500"
            data-test="comment-input"
            aria-label="写下评论"
            placeholder="分享你的想法，@用户名 可提及他人"
            class="comment-textarea w-full resize-none border-0 bg-transparent p-0 text-subhead leading-relaxed text-ink placeholder:text-ink-dim/70 focus:outline-none"
            @input="autosizeComposer"
            @keydown="onComposerKeydown"
          ></textarea>

          <!-- @ 提及候选：行尾输入 @ 时出现，点选补全 -->
          <div
            v-if="rootCandidates.length"
            data-test="mention-pop"
            class="mt-2 overflow-hidden rounded-xl border border-line bg-cream shadow-toast"
          >
            <p class="mono-label px-3 pt-2 pb-1">提及共创者</p>
            <button
              v-for="u in rootCandidates"
              :key="u.id"
              type="button"
              data-test="mention-option"
              class="flex w-full items-center gap-2 px-3 py-2 text-left text-footnote text-ink transition-colors hover:bg-sand"
              @click="pickMention(u.username)"
            >
              <span
                class="flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-caption2 font-bold text-pine-deep"
              >
                <img v-if="u.avatar" :src="u.avatar" alt="" class="h-full w-full object-cover" />
                <template v-else>{{ (u.username || '友').slice(0, 1).toUpperCase() }}</template>
              </span>
              <span class="truncate">@{{ u.username }}</span>
            </button>
          </div>

          <div class="mt-2.5 flex items-center justify-between gap-3 border-t border-line pt-2.5">
            <div class="flex min-w-0 items-center gap-2.5">
              <span class="shrink-0 text-caption1 tabular-nums text-ink-dim" data-test="comment-counter">{{ draft.length }}/500</span>
              <span class="hidden truncate text-caption1 text-ink-dim sm:inline">Ctrl / ⌘ + Enter 快速发布</span>
            </div>
            <button
              class="btn-primary shrink-0 !px-5 !py-1.5 text-footnote"
              data-test="comment-submit"
              :disabled="!draft || submitting"
              @click="handleSubmit"
            >
              {{ submitting ? '发布中…' : '发布' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区（未登录）：玻璃提示条 -->
    <div
      v-else
      class="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl2 border border-[color:var(--glass-border)] bg-[color:var(--glass-card)] px-5 py-4 backdrop-blur-xl backdrop-saturate-150"
    >
      <div class="flex items-center gap-2.5">
        <AppIcon name="message-circle" class="h-4 w-4 shrink-0 text-pine" />
        <p class="text-footnote text-ink-mid" data-test="comment-login-hint">登录后即可参与讨论</p>
      </div>
      <router-link :to="{ name: 'Login', query: { redirect: route.fullPath } }" class="btn-secondary !py-1.5 text-footnote">
        登录
      </router-link>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loading" class="mt-8 space-y-6">
      <div v-for="i in 3" :key="i" class="flex gap-3.5">
        <div class="skeleton h-10 w-10 shrink-0 !rounded-full"></div>
        <div class="flex-1 space-y-2 pt-1">
          <div class="skeleton h-3.5 w-28"></div>
          <div class="skeleton h-3.5 w-full"></div>
          <div class="skeleton h-3.5 w-2/3"></div>
        </div>
      </div>
    </div>

    <!-- 评论列表：发丝线分隔，根评论 + 两级回复 -->
    <ul v-else-if="comments.length" class="mt-2">
      <li
        v-for="(c, i) in comments"
        :id="`comment-${c.id}`"
        :key="c.id"
        v-reveal="i < 4 ? i * 60 : 0"
        data-test="comment-item"
        class="scroll-mt-24 border-b border-line py-6 last:border-b-0"
        :class="{ 'comment-flash': flashId === c.id }"
      >
        <!-- 根评论：身份行 / 正文 / 操作行三段，操作按钮不再和用户名挤在一行 -->
        <div class="flex gap-3 sm:gap-3.5">
          <Avatar :user="c.user" size="md" />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="truncate text-subhead font-medium text-ink">{{ c.user?.username || '匿名共创者' }}</span>
              <span v-if="isProjectCreator(c.user)" class="comment-badge bg-pine-soft text-pine-deep">
                <AppIcon name="sprout" class="h-3 w-3" />发起人
              </span>
              <span v-else-if="isCurrentUser(c.user)" class="comment-badge bg-sand text-ink-mid">我</span>
              <span class="shrink-0 text-caption1 text-ink-dim">{{ relativeTime(c.createdAt) }}</span>
            </div>
            <div class="mt-1.5 whitespace-pre-wrap text-subhead leading-relaxed text-ink-mid"><CommentContent :content="c.content" :mention-names="mentionNames" /></div>

            <div class="mt-2 flex items-center gap-1">
              <LikeButton :liked="c.liked" :count="c.likeCount" :disabled="liking === c.id" @toggle="toggleLike(c)" />
              <button
                v-if="userStore.isLoggedIn"
                type="button"
                class="comment-action"
                data-test="comment-reply-btn"
                @click="toggleReply(c)"
              >
                <AppIcon name="message-circle" class="h-3.5 w-3.5" />
                回复
              </button>
              <button
                v-if="c.canDelete"
                type="button"
                class="comment-action comment-action--danger ml-auto"
                data-test="comment-delete"
                :disabled="removing === c.id"
                @click="handleDelete(c, null)"
              >
                <AppIcon name="trash-2" class="h-3.5 w-3.5" />
                {{ removing === c.id ? '删除中…' : '删除' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 回复线程：左侧竖线 + 卡片化回复；超过 3 条折叠 -->
        <div v-if="c.replies?.length" class="ml-[26px] mt-3 sm:ml-[38px]">
          <div class="comment-thread-list space-y-2 border-l border-line pl-4 sm:pl-6">
            <div
              v-for="r in visibleReplies(c)"
              :id="`comment-${r.id}`"
              :key="r.id"
              data-test="comment-reply"
              class="comment-reply scroll-mt-24"
              :class="{ 'comment-flash': flashId === r.id }"
            >
              <div class="flex gap-3">
                <Avatar :user="r.user" size="sm" />
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    <span class="truncate text-footnote font-medium text-ink">{{ r.user?.username || '匿名共创者' }}</span>
                    <span v-if="isProjectCreator(r.user)" class="comment-badge bg-pine-soft text-pine-deep">
                      <AppIcon name="sprout" class="h-3 w-3" />发起人
                    </span>
                    <span v-else-if="isCurrentUser(r.user)" class="comment-badge bg-sand text-ink-mid">我</span>
                    <span class="shrink-0 text-caption1 text-ink-dim">{{ relativeTime(r.createdAt) }}</span>
                  </div>
                  <div class="mt-1 whitespace-pre-wrap text-footnote leading-relaxed text-ink-mid"><CommentContent :content="r.content" :mention-names="mentionNames" /></div>

                  <div class="mt-1.5 flex items-center gap-1">
                    <LikeButton :liked="r.liked" :count="r.likeCount" :disabled="liking === r.id" @toggle="toggleLike(r)" />
                    <button
                      v-if="r.canDelete"
                      type="button"
                      class="comment-action comment-action--danger ml-auto"
                      data-test="comment-delete"
                      :disabled="removing === r.id"
                      @click="handleDelete(r, c)"
                    >
                      <AppIcon name="trash-2" class="h-3 w-3" />
                      {{ removing === r.id ? '删除中…' : '删除' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <button
            v-if="c.replies.length > REPLY_PREVIEW"
            type="button"
            class="mt-2 ml-4 inline-flex items-center gap-1 rounded-lg px-2 py-1 text-caption1 font-medium text-pine transition-colors hover:bg-pine-soft sm:ml-6"
            data-test="comment-replies-toggle"
            @click="toggleReplies(c)"
          >
            <AppIcon
              name="chevronDown"
              class="h-3.5 w-3.5 transition-transform duration-200"
              :class="isExpanded(c) ? 'rotate-180' : ''"
            />
            {{ isExpanded(c) ? '收起回复' : `展开其余 ${c.replies.length - REPLY_PREVIEW} 条回复` }}
          </button>
        </div>

        <!-- 回复输入：目标 chip + 独立纸面卡片，Esc 取消、Ctrl/⌘+Enter 发布 -->
        <div v-if="replyingTo === c.id" class="ml-[26px] mt-3 sm:ml-[38px]" data-test="comment-reply-composer">
          <div class="card p-3.5 sm:p-4">
            <div class="mb-2 flex items-center gap-2">
              <span class="shrink-0 text-caption1 text-ink-dim">回复</span>
              <span
                class="inline-flex min-w-0 items-center gap-1 rounded-full bg-pine-soft px-2 py-0.5 text-caption1 font-medium text-pine-deep"
              >
                <AppIcon name="user" class="h-3 w-3 shrink-0" />
                <span class="truncate">@{{ c.user?.username || '匿名共创者' }}</span>
              </span>
              <button
                type="button"
                class="ml-auto shrink-0 rounded-full p-1 text-ink-dim transition-colors hover:bg-sand hover:text-ink"
                aria-label="取消回复"
                @click="cancelReply"
              >
                <AppIcon name="x" class="h-3.5 w-3.5" />
              </button>
            </div>
            <textarea
              :ref="setReplyInput"
              v-model="replyDraft"
              rows="2"
              maxlength="500"
              aria-label="回复内容"
              :placeholder="`回复 @${c.user?.username || '匿名共创者'}…`"
              class="comment-textarea w-full resize-none rounded-lg border border-line bg-cream px-3 py-2 text-footnote leading-relaxed text-ink placeholder:text-ink-dim/70 focus:border-pine/50 focus:outline-none"
              @input="autosizeReply"
              @keydown="onReplyKeydown($event, c)"
              @keydown.esc.prevent="cancelReply"
            ></textarea>
            <div class="mt-2 flex items-center justify-between gap-3">
              <span class="text-caption1 tabular-nums text-ink-dim">{{ replyDraft.length }}/500</span>
              <div class="flex items-center gap-1.5">
                <button type="button" class="btn-ghost !px-3 !py-1 text-caption1" @click="cancelReply">取消</button>
                <button
                  type="button"
                  class="btn-primary !px-4 !py-1.5 text-footnote"
                  :disabled="!replyDraft || submitting"
                  @click="submitReply(c)"
                >
                  {{ submitting ? '发布中…' : '回复' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ul>

    <!-- 空状态：虚线纸面 + 首条评论引导 -->
    <div v-else class="mt-8 rounded-xl2 border border-dashed border-line px-6 py-10 text-center">
      <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-pine-soft/70 text-pine-deep">
        <AppIcon name="message-circle" class="h-5 w-5" :stroke-width="1.6" />
      </span>
      <p class="mt-3 text-subhead font-medium text-ink">还没有评论</p>
      <p class="mt-1 text-footnote text-ink-dim">来写下第一条想法，与共创者交流。</p>
      <button
        v-if="userStore.isLoggedIn"
        type="button"
        class="btn-secondary mt-4 !px-4 !py-2 text-footnote"
        data-test="comment-empty-cta"
        @click="focusComposer"
      >
        写下第一条评论
      </button>
    </div>

    <!-- 加载更多 -->
    <div v-if="!loading && hasMore" class="mt-2 flex justify-center">
      <button class="btn-ghost text-footnote text-pine" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? '加载中…' : '显示更多评论' }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, h, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as commentApi from '@/api/comment'
import { useUserStore } from '@/store/user'
import { hasEmoji, stripEmoji } from '@/utils/text'
import { relativeTime } from '@/utils/time'
import { toast } from '@/composables/useToast'
import { confirm } from '@/composables/useConfirm'
import AppIcon from '@/components/AppIcon.vue'
import CommentContent from '@/components/CommentContent.vue'
import { useMentionHint } from '@/composables/useMentionHint'

// 头像：与全站一致的字母回退（函数式组件，避免嵌套列表重复模板）
const Avatar = (props) => {
  const size = props.size === 'sm' ? 'h-8 w-8 text-caption1' : 'h-10 w-10 text-footnote'
  return h(
    'span',
    { class: `flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft font-bold text-pine-deep ${size}` },
    props.user?.avatar
      ? [h('img', { src: props.user.avatar, alt: '', class: 'h-full w-full object-cover' })]
      : [(props.user?.username || '友').slice(0, 1).toUpperCase()]
  )
}
Avatar.props = { user: { type: Object, default: null }, size: { type: String, default: 'md' } }

// 点赞按钮：心形 + 计数，点赞态填充苹果红
const LikeButton = (props, { emit }) =>
  h(
    'button',
    {
      class: `relative inline-flex items-center gap-1 rounded-full px-2 py-1 text-caption1 transition-colors after:absolute after:inset-x-0 after:-inset-y-2.5 after:content-[''] ${
        props.liked ? 'text-clay' : 'text-ink-dim hover:bg-clay/10 hover:text-clay'
      }`,
      type: 'button',
      'data-test': 'comment-like',
      'aria-pressed': String(props.liked),
      'aria-label': props.liked ? '取消点赞' : '点赞',
      disabled: props.disabled,
      onClick: () => emit('toggle')
    },
    [
      h('svg', { class: 'h-3.5 w-3.5', viewBox: '0 0 24 24', fill: props.liked ? 'currentColor' : 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
        h('path', { d: 'M20.4 12.6 12 21l-8.4-8.4a5.3 5.3 0 1 1 7.5-7.5l.9.9.9-.9a5.3 5.3 0 1 1 7.5 7.5z' })
      ]),
      props.count > 0 ? String(props.count) : null
    ]
  )
LikeButton.props = { liked: Boolean, count: { type: Number, default: 0 }, disabled: Boolean }
LikeButton.emits = ['toggle']

const props = defineProps({
  projectId: { type: [Number, String], required: true },
  creatorId: { type: [Number, String], default: null }
})

// 总数变化上报（详情页玻璃操作条展示实时评论数）
const emit = defineEmits(['change'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const comments = ref([])
const total = ref(0)
// 本页真实存在的 @ 用户名（后端 listComments 顶层字段，高亮唯一口径）
const mentionNames = ref([])
const page = ref(1)
const PAGE_SIZE = 10
const loading = ref(true)
const loadingMore = ref(false)
const submitting = ref(false)
const removing = ref(null)
const liking = ref(null)
const draft = ref('')

// 输入框引用：自动增高 + 「写下第一条评论」聚焦
const composerInput = ref(null)
const replyInputEl = ref(null)
const setReplyInput = (el) => {
  replyInputEl.value = el
}

// 回复状态：replyingTo 为根评论 id，replyDraft 为回复内容
const replyingTo = ref(null)
const replyDraft = ref('')

// 长回复线程默认只展示前 3 条，其余收起
const REPLY_PREVIEW = 3
const expandedReplies = ref(new Set())
const isExpanded = (c) => expandedReplies.value.has(c.id)
const visibleReplies = (c) => {
  const list = c.replies || []
  return isExpanded(c) || list.length <= REPLY_PREVIEW ? list : list.slice(0, REPLY_PREVIEW)
}
const toggleReplies = (c) => {
  if (isExpanded(c)) expandedReplies.value.delete(c.id)
  else expandedReplies.value.add(c.id)
}

// 正在高亮的评论 id（深链命中时短暂点亮）
const flashId = ref(null)

// rootTotal = 根评论数（分页只翻根评论）；total 含回复，只给「N 条」展示用。
// 拿 total 判断 hasMore 的话，有回复的项目会出现一个永远点不完的假「显示更多」按钮
const rootTotal = ref(0)
const hasMore = computed(() => comments.value.length < rootTotal.value)

// 展示用身份：自己的头像走 store，避免再取一次接口
const selfUser = computed(() => ({ username: userStore.username, avatar: userStore.avatar }))
const isProjectCreator = (user) => props.creatorId != null && Number(user?.id) === Number(props.creatorId)
const isCurrentUser = (user) => userStore.userId != null && Number(user?.id) === Number(userStore.userId)

// 输入框随内容增高：先归零再量 scrollHeight，超过上限才出现滚动条
const autosize = (el, max = 220) => {
  if (!el) return
  el.style.height = 'auto'
  const next = Math.min(el.scrollHeight, max)
  el.style.height = `${next}px`
  el.style.overflowY = el.scrollHeight > max ? 'auto' : 'hidden'
}
const autosizeComposer = () => autosize(composerInput.value)
const autosizeReply = () => autosize(replyInputEl.value, 180)

const focusComposer = () => {
  const el = composerInput.value
  if (!el) return
  el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  el.focus({ preventScroll: true })
}

// ---------- @ 提及补全 ----------
// 行尾 @ 触发候选（textarea 无 caret 检测的轻量近似；句中 @ 打全名仍会被后端识别）
const { token: mentionToken } = useMentionHint(draft)
// 候选：本页评论的作者去重（真实说过话的人优先），排除自己
const mentionCandidates = computed(() => {
  const seen = new Set()
  const list = []
  for (const c of comments.value) {
    for (const u of [c.user, ...(c.replies || []).map((r) => r.user)]) {
      if (u?.username && !seen.has(u.username)) {
        seen.add(u.username)
        list.push(u)
      }
    }
  }
  return list.filter((u) => u.id !== userStore.userId)
})
const rootCandidates = computed(() =>
  mentionToken.value == null
    ? []
    : mentionCandidates.value
        .filter((u) => u.username.toLowerCase().includes(mentionToken.value.toLowerCase()))
        .slice(0, 6)
)
const pickMention = (username) => {
  draft.value = String(draft.value || '').replace(
    /@([^\s@，。！？；、：,.;:!?"'（）【】《》<>{}()]{0,20})$/,
    `@${username} `
  )
  mentionToken.value = null
  nextTick(autosizeComposer)
}

// 提交前净化：与后端同一套规则，全站仅允许矢量图标
const sanitize = (text) => {
  if (!hasEmoji(text)) return { content: text, hadEmoji: false }
  const cleaned = stripEmoji(text)
  return { content: cleaned, hadEmoji: true }
}

const applyRes = (res) => {
  comments.value.push(...res.data.comments)
  total.value = res.data.total
  rootTotal.value = res.data.rootTotal ?? res.data.total
  mentionNames.value = res.data.mentionNames || []
  emit('change', total.value)
}

const fetchFirst = async () => {
  loading.value = true
  try {
    const res = await commentApi.getComments(props.projectId, { page: 1, pageSize: PAGE_SIZE })
    comments.value = []
    page.value = 1
    applyRes(res)
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  loadingMore.value = true
  try {
    page.value += 1
    applyRes(await commentApi.getComments(props.projectId, { page: page.value, pageSize: PAGE_SIZE }))
  } finally {
    loadingMore.value = false
  }
}

const handleSubmit = async () => {
  const raw = draft.value.trim()
  if (!raw || submitting.value) return
  const { content, hadEmoji } = sanitize(raw)
  if (!content) {
    toast('评论不能只有表情符号', 'info')
    return
  }

  submitting.value = true
  try {
    const res = await commentApi.createComment(props.projectId, { content })
    comments.value.unshift(res.data.comment)
    // 刚发布评论里被识别的 @ 用户名并入高亮口径（createComment 响应 mentions，
    // 与列表口径同源），不用重拉整页列表就能即时高亮
    for (const m of res.data.mentions || []) {
      if (!mentionNames.value.includes(m.username)) mentionNames.value.push(m.username)
    }
    total.value = res.data.commentCount
    emit('change', total.value)
    draft.value = ''
    nextTick(autosizeComposer)
    toast(hadEmoji ? '评论已发布，表情符号已自动移除' : '评论已发布')
  } catch (e) {
    toast(e.response?.data?.message || '发布失败，请稍后再试', 'error')
  } finally {
    submitting.value = false
  }
}

const onComposerKeydown = (event) => {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    handleSubmit()
  }
}

const toggleReply = (c) => {
  if (replyingTo.value === c.id) {
    cancelReply()
    return
  }
  replyingTo.value = c.id
  replyDraft.value = ''
  nextTick(() => {
    replyInputEl.value?.focus()
    autosizeReply()
  })
}

const cancelReply = () => {
  replyingTo.value = null
  replyDraft.value = ''
}

const submitReply = async (root) => {
  const raw = replyDraft.value.trim()
  if (!raw || submitting.value) return
  const { content, hadEmoji } = sanitize(raw)
  if (!content) {
    toast('回复不能只有表情符号', 'info')
    return
  }

  submitting.value = true
  try {
    const res = await commentApi.createComment(props.projectId, { content, parentId: root.id })
    root.replies = root.replies || []
    root.replies.push(res.data.comment)
    root.replyCount = (root.replyCount || 0) + 1
    // 新回复追加在线程末尾，折叠状态下也得让它露出来
    expandedReplies.value.add(root.id)
    total.value = res.data.commentCount
    emit('change', total.value)
    cancelReply()
    toast(hadEmoji ? '回复已发布，表情符号已自动移除' : '回复已发布')
  } catch (e) {
    toast(e.response?.data?.message || '发布失败，请稍后再试', 'error')
  } finally {
    submitting.value = false
  }
}

const onReplyKeydown = (event, root) => {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    submitReply(root)
  }
}

const toggleLike = async (c) => {
  if (!userStore.isLoggedIn) {
    toast('请先登录', 'info')
    router.push({ name: 'Login', query: { redirect: route.fullPath } })
    return
  }
  if (liking.value === c.id) return
  liking.value = c.id
  try {
    if (c.liked) {
      const res = await commentApi.unlikeComment(props.projectId, c.id)
      c.likeCount = res.data.likeCount
      c.liked = false
    } else {
      const res = await commentApi.likeComment(props.projectId, c.id)
      c.likeCount = res.data.likeCount
      c.liked = true
    }
  } catch (e) {
    const msg = e.response?.data?.message || ''
    // 本地状态与服务端不一致时纠正（如换设备后重复点赞）
    if (msg.includes('已点赞')) {
      c.liked = true
    } else if (msg.includes('尚未点赞')) {
      c.liked = false
    } else {
      toast(msg || '操作失败，请稍后再试', 'error')
    }
  } finally {
    liking.value = null
  }
}

const handleDelete = async (c, root) => {
  const isRoot = c.parentId == null
  const withReplies = isRoot && c.replyCount > 0
  const ok = await confirm({
    title: isRoot ? '删除这条评论？' : '删除这条回复？',
    message: withReplies
      ? `这条评论下的 ${c.replyCount} 条回复也会一并删除，此操作不可恢复。`
      : '删除后无法恢复，确定继续吗？',
    confirmLabel: '删除',
    destructive: true
  })
  if (!ok) return

  removing.value = c.id
  try {
    const res = await commentApi.deleteComment(props.projectId, c.id)
    if (root) {
      root.replies = (root.replies || []).filter((item) => item.id !== c.id)
      root.replyCount = Math.max(0, root.replyCount - 1)
    } else {
      comments.value = comments.value.filter((item) => item.id !== c.id)
      expandedReplies.value.delete(c.id)
      rootTotal.value = Math.max(0, rootTotal.value - 1)
    }
    total.value = res.data.commentCount
    emit('change', total.value)
    toast('评论已删除', 'info')
  } catch (e) {
    toast(e.response?.data?.message || '删除失败，请稍后再试', 'error')
  } finally {
    removing.value = null
  }
}

// 深链：URL 带 ?comment=<id>（通知 / 「我参与的讨论」跳过来）时，
// 先问后端这条评论在第几页，把「加载更多」连续点到那一页，再滚过去高亮。
// 不做定位的话深链只能命中第一页，评论一多就是个静默失效的假链接
const focusComment = async (rawId) => {
  const commentId = Number(rawId)
  if (!commentId) return
  try {
    const { data } = await commentApi.locateComment(props.projectId, commentId, PAGE_SIZE)
    // 回复可能藏在折叠线程里：先把父级线程展开，元素才会存在
    if (data.parentId != null) expandedReplies.value.add(Number(data.parentId))
    // 列表是追加式分页：逐页补齐到目标页（hasMore 为假时自然退出，不会死循环）
    let guard = 0
    while (page.value < data.page && hasMore.value && guard < 20) {
      await loadMore()
      guard += 1
    }
    await nextTick()
    const el = document.getElementById(`comment-${commentId}`)
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    flashId.value = commentId
    setTimeout(() => {
      if (flashId.value === commentId) flashId.value = null
    }, 2400)
  } catch (e) {
    // 评论被删 / 不属于本项目：退化成普通列表，提示一句就够，不要挡住页面。
    // 服务端那句「评论不存在」是接口口径，对拿着旧链接点进来的人来说太生硬
    const status = e.response?.status
    toast(status === 404 ? '这条评论已经不在了' : e.response?.data?.message || '定位失败', 'info')
  }
}

onMounted(async () => {
  await fetchFirst()
  autosizeComposer()
  if (route.query.comment) await focusComment(route.query.comment)
})
</script>

<style scoped>
/* 输入卡：聚焦时用松针色描边点亮，让「正在写」有明确归属 */
.comment-composer {
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.comment-composer:focus-within {
  border-color: rgb(var(--c-pine) / 0.5);
  box-shadow: 3px 4px 0 rgb(var(--c-pine) / 0.14);
}

/* 两个输入框都靠 JS 定高，最低留一行半的呼吸空间 */
.comment-textarea {
  min-height: 3rem;
  overflow-y: hidden;
}

/* 身份徽标：发起人 / 我，和用户名同一行但视觉上退后半步 */
.comment-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  border-radius: 9999px;
  padding: 0.0625rem 0.375rem;
  font-size: 0.6875rem;
  line-height: 0.875rem;
  font-weight: 600;
}

/* 评论操作：12px 文字 + 4px 上下内边距 = 24px 视觉高，靠 ::after 扩到 44px 热区
   （verify_mobile_touch.py 会从盒边外 7px 做真实命中探测，别收窄） */
.comment-action {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 9999px;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  line-height: 1rem;
  color: rgb(var(--c-ink-dim));
  transition: color 0.15s ease, background-color 0.15s ease;
}
.comment-action::after {
  content: '';
  position: absolute;
  inset: -10px 0;
}
.comment-action:hover:not(:disabled) {
  background-color: rgb(var(--c-pine-soft));
  color: rgb(var(--c-pine-deep));
}
.comment-action--danger:hover:not(:disabled) {
  background-color: rgb(var(--c-clay) / 0.1);
  color: rgb(var(--c-clay));
}
.comment-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.comment-action:focus-visible {
  outline: 2px solid rgb(var(--c-pine) / 0.55);
  outline-offset: 2px;
}

/* 回复项做成浅纸卡片，叠在竖线旁边，长线程也能一眼分条 */
.comment-reply {
  border-radius: 12px;
  background-color: rgb(var(--c-sand) / 0.28);
  padding: 0.625rem 0.75rem;
  transition: background-color 0.15s ease;
}
.comment-reply:hover {
  background-color: rgb(var(--c-sand) / 0.45);
}
</style>

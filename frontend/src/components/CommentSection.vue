<template>
  <section id="comments" class="mt-14 scroll-mt-24">
    <!-- 分区标题：App Store「评分与评论」式大标题 + 发丝线分隔 -->
    <div class="flex items-end justify-between gap-4">
      <h2 class="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">评论</h2>
      <span class="pb-1 text-sm tabular-nums text-ink-dim">{{ total ? `${total} 条` : '' }}</span>
    </div>
    <div class="mt-4 h-px bg-line"></div>

    <!-- 输入区（已登录） -->
    <div v-if="userStore.isLoggedIn" class="card mt-6 p-5 sm:p-6">
      <div class="flex gap-3.5">
        <span
          class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-sm font-bold text-pine-deep"
        >
          <img v-if="userStore.avatar" :src="userStore.avatar" alt="" class="h-full w-full object-cover" />
          <template v-else>{{ (userStore.username || '友').slice(0, 1).toUpperCase() }}</template>
        </span>
        <div class="min-w-0 flex-1">
          <textarea
            v-model.trim="draft"
            rows="3"
            maxlength="500"
            data-test="comment-input"
            placeholder="分享你的想法与建议…"
            class="w-full resize-none rounded-lg border-0 bg-transparent p-0 text-[15px] leading-relaxed text-ink placeholder:text-ink-dim/70 focus:outline-none"
          ></textarea>
          <div class="mt-3 flex items-center justify-between border-t border-line pt-3">
            <span class="text-xs tabular-nums text-ink-dim" data-test="comment-counter">{{ draft.length }}/500</span>
            <button
              class="btn-primary !px-5 !py-1.5 text-sm"
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
      <p class="text-sm text-ink-mid" data-test="comment-login-hint">登录后即可参与讨论</p>
      <router-link :to="{ name: 'Login', query: { redirect: route.fullPath } }" class="btn-secondary !py-1.5 text-sm">
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
        <!-- 根评论 -->
        <div class="flex gap-3.5">
          <Avatar :user="c.user" size="md" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-[15px] font-medium text-ink">{{ c.user?.username || '匿名共创者' }}</span>
              <span class="shrink-0 text-xs text-ink-dim">{{ relativeTime(c.createdAt) }}</span>
              <div class="ml-auto flex shrink-0 items-center gap-0.5">
                <LikeButton :liked="c.liked" :count="c.likeCount" :disabled="liking === c.id" @toggle="toggleLike(c)" />
                <button
                  v-if="userStore.isLoggedIn"
                  class="rounded-full px-2 py-1 text-xs text-ink-dim transition-colors hover:bg-pine-soft hover:text-pine-deep"
                  @click="toggleReply(c)"
                >
                  回复
                </button>
                <button
                  v-if="c.canDelete"
                  class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs text-ink-dim transition-colors hover:bg-clay/10 hover:text-clay"
                  data-test="comment-delete"
                  :disabled="removing === c.id"
                  @click="handleDelete(c, null)"
                >
                  <AppIcon name="trash-2" class="h-3.5 w-3.5" />
                  删除
                </button>
              </div>
            </div>
            <p class="mt-1.5 whitespace-pre-wrap text-[15px] leading-relaxed text-ink-mid">{{ c.content }}</p>
          </div>
        </div>

        <!-- 回复列表（缩进，小一号） -->
        <div v-if="c.replies?.length" class="ml-[26px] mt-4 space-y-4 border-l border-line pl-6 sm:ml-[38px] sm:pl-7">
          <div
            v-for="r in c.replies"
            :id="`comment-${r.id}`"
            :key="r.id"
            data-test="comment-reply"
            class="scroll-mt-24 flex gap-3"
            :class="{ 'comment-flash': flashId === r.id }"
          >
            <Avatar :user="r.user" size="sm" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="truncate text-sm font-medium text-ink">{{ r.user?.username || '匿名共创者' }}</span>
                <span class="shrink-0 text-xs text-ink-dim">{{ relativeTime(r.createdAt) }}</span>
                <div class="ml-auto flex shrink-0 items-center gap-0.5">
                  <LikeButton :liked="r.liked" :count="r.likeCount" :disabled="liking === r.id" @toggle="toggleLike(r)" />
                  <button
                    v-if="r.canDelete"
                    class="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs text-ink-dim transition-colors hover:bg-clay/10 hover:text-clay"
                    :disabled="removing === r.id"
                    @click="handleDelete(r, c)"
                  >
                    <AppIcon name="trash-2" class="h-3 w-3" />
                    删除
                  </button>
                </div>
              </div>
              <p class="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink-mid">{{ r.content }}</p>
            </div>
          </div>
        </div>

        <!-- 回复输入（内联展开） -->
        <div v-if="replyingTo === c.id" class="ml-[26px] mt-4 sm:ml-[38px]">
          <div class="flex gap-3 rounded-xl bg-cream p-3.5">
            <div class="min-w-0 flex-1">
              <textarea
                v-model.trim="replyDraft"
                rows="2"
                maxlength="500"
                :placeholder="`回复 @${c.user?.username || '匿名共创者'}…`"
                class="w-full resize-none border-0 bg-transparent p-0 text-sm leading-relaxed text-ink placeholder:text-ink-dim/70 focus:outline-none"
              ></textarea>
              <div class="mt-2 flex items-center justify-between border-t border-line pt-2">
                <span class="text-xs tabular-nums text-ink-dim">{{ replyDraft.length }}/500</span>
                <div class="flex items-center gap-1">
                  <button class="btn-ghost !px-3 !py-1 text-xs" @click="cancelReply">取消</button>
                  <button
                    class="btn-primary !px-4 !py-1 text-xs"
                    :disabled="!replyDraft || submitting"
                    @click="submitReply(c)"
                  >
                    {{ submitting ? '发布中…' : '回复' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ul>

    <!-- 空状态 -->
    <div v-else class="mt-10 flex flex-col items-center gap-2 pb-4 text-center">
      <AppIcon name="message-circle" class="h-8 w-8 text-ink-dim/50" :stroke-width="1.5" />
      <p class="text-[15px] text-ink-mid">还没有评论</p>
      <p class="text-sm text-ink-dim">来写下第一条想法，与共创者交流。</p>
    </div>

    <!-- 加载更多 -->
    <div v-if="!loading && hasMore" class="mt-2 flex justify-center">
      <button class="btn-ghost text-sm text-pine" :disabled="loadingMore" @click="loadMore">
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
import AppIcon from '@/components/AppIcon.vue'

// 头像：与全站一致的字母回退（函数式组件，避免嵌套列表重复模板）
const Avatar = (props) => {
  const size = props.size === 'sm' ? 'h-8 w-8 text-xs' : 'h-10 w-10 text-sm'
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
      class: `inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors ${
        props.liked ? 'text-[#FF3B30]' : 'text-ink-dim hover:bg-clay/10 hover:text-clay'
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
  projectId: { type: [Number, String], required: true }
})

// 总数变化上报（详情页玻璃操作条展示实时评论数）
const emit = defineEmits(['change'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const comments = ref([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 10
const loading = ref(true)
const loadingMore = ref(false)
const submitting = ref(false)
const removing = ref(null)
const liking = ref(null)
const draft = ref('')

// 回复状态：replyingTo 为根评论 id，replyDraft 为回复内容
const replyingTo = ref(null)
const replyDraft = ref('')

// 正在高亮的评论 id（深链命中时短暂点亮）
const flashId = ref(null)

// rootTotal = 根评论数（分页只翻根评论）；total 含回复，只给「N 条」展示用。
// 拿 total 判断 hasMore 的话，有回复的项目会出现一个永远点不完的假「显示更多」按钮
const rootTotal = ref(0)
const hasMore = computed(() => comments.value.length < rootTotal.value)

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
  if (!draft.value || submitting.value) return
  const { content, hadEmoji } = sanitize(draft.value)
  if (!content) {
    toast('评论不能只有表情符号', 'info')
    return
  }

  submitting.value = true
  try {
    const res = await commentApi.createComment(props.projectId, { content })
    comments.value.unshift(res.data.comment)
    total.value = res.data.commentCount
    emit('change', total.value)
    draft.value = ''
    toast(hadEmoji ? '评论已发布，表情符号已自动移除' : '评论已发布')
  } catch (e) {
    toast(e.response?.data?.message || '发布失败，请稍后再试', 'error')
  } finally {
    submitting.value = false
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
    const inputs = document.querySelectorAll('textarea')
    inputs[inputs.length - 1]?.focus()
  })
}

const cancelReply = () => {
  replyingTo.value = null
  replyDraft.value = ''
}

const submitReply = async (root) => {
  if (!replyDraft.value || submitting.value) return
  const { content, hadEmoji } = sanitize(replyDraft.value)
  if (!content) {
    toast('回复不能只有表情符号', 'info')
    return
  }

  submitting.value = true
  try {
    const res = await commentApi.createComment(props.projectId, { content, parentId: root.id })
    root.replies.push(res.data.comment)
    root.replyCount += 1
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
  const tip = c.parentId === null && c.replyCount > 0 ? `删除这条评论将同时删除其下 ${c.replyCount} 条回复。` : '确定删除这条评论吗？'
  if (!window.confirm(`${tip}\n此操作不可恢复。`)) return
  removing.value = c.id
  try {
    const res = await commentApi.deleteComment(props.projectId, c.id)
    if (root) {
      root.replies = root.replies.filter((item) => item.id !== c.id)
      root.replyCount = Math.max(0, root.replyCount - 1)
    } else {
      comments.value = comments.value.filter((item) => item.id !== c.id)
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
  if (route.query.comment) await focusComment(route.query.comment)
})
</script>

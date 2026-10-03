<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <!-- 页头：苹果式大标题 -->
    <div>
      <h1 class="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">账号安全</h1>
      <p data-test="security-subtitle" class="mt-2 text-sm text-ink-mid">{{ subtitle }}</p>
    </div>

    <!-- 分段控件：安全提醒 / 我的操作 / 登录密码 -->
    <div class="mt-6 inline-flex rounded-full bg-sand p-1" role="tablist" aria-label="账号安全视图">
      <button
        v-for="opt in TAB_OPTIONS"
        :key="opt.value"
        role="tab"
        :aria-selected="tab === opt.value"
        :data-test="`security-tab-${opt.value}`"
        class="rounded-full px-4 py-1.5 text-sm transition-all duration-200"
        :class="tab === opt.value ? 'bg-cream font-medium text-ink shadow-sm' : 'text-ink-mid hover:text-ink'"
        @click="switchTab(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- ===================== 安全提醒 ===================== -->
    <section v-if="tab === 'security'" data-test="security-panel" class="mt-6">
      <!-- 总览条：**只在真有事件时出现**。没有事件就不摆一个「0 条」的横幅吓唬人。 -->
      <div
        v-if="!security.loading && security.total > 0"
        data-test="security-summary"
        class="card flex items-start gap-3 p-4 sm:p-5"
      >
        <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-clay/10 text-clay">
          <AppIcon name="triangle-alert" class="h-[18px] w-[18px]" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-ink">这里记录了 {{ security.total }} 条针对你账号的失败尝试</p>
          <p class="mt-1 text-[13px] leading-relaxed text-ink-mid">
            失败的尝试不会影响你的账号，也不代表密码已经被猜到。如果下面的来源你都认不出来，建议换一个更长的密码，并避免在别处复用。
          </p>
        </div>
      </div>

      <!-- 类型筛选（只列真能筛出结果的类型，见 utils/audit.js 的说明） -->
      <div class="mt-5 flex flex-wrap gap-1.5">
        <button
          v-for="opt in EVENT_FILTERS"
          :key="opt.value"
          data-test="security-filter"
          class="chip-link"
          :class="security.filter === opt.value ? '!bg-pine-soft !text-pine-deep' : ''"
          @click="applyFilter(security, SECURITY_CFG, opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>

      <!-- 骨架 -->
      <div v-if="security.loading" class="card mt-4 divide-y divide-line overflow-hidden !p-0">
        <div v-for="i in 3" :key="i" class="flex items-start gap-3 px-5 py-4">
          <div class="h-9 w-9 shrink-0 animate-pulse rounded-full bg-sand"></div>
          <div class="min-w-0 flex-1 space-y-2 py-1">
            <div class="h-3.5 w-2/5 animate-pulse rounded bg-sand"></div>
            <div class="h-3 w-3/5 animate-pulse rounded bg-sand"></div>
          </div>
        </div>
      </div>

      <template v-else-if="!security.items.length">
        <EmptyState
          icon="shield"
          :title="security.filter ? '没有这类尝试' : '没有发现异常尝试'"
          :description="
            security.filter
              ? '这个类型下暂时没有记录，换个类型看看。'
              : '有人在尝试登录、或拿你的用户名注册时，这里会留下一行记录。目前一切正常。'
          "
        >
          <button v-if="security.filter" class="btn-secondary text-sm" @click="applyFilter(security, SECURITY_CFG, '')">
            查看全部类型
          </button>
        </EmptyState>
      </template>

      <div v-else data-test="security-list" class="card mt-4 divide-y divide-line overflow-hidden !p-0">
        <article
          v-for="(e, i) in security.items"
          :key="e.id"
          v-reveal="Math.min(i, 8) * 40"
          data-test="security-row"
          :data-event="e.event"
          class="flex items-start gap-3 px-5 py-4"
        >
          <span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-clay/10 text-clay">
            <AppIcon name="triangle-alert" class="h-[18px] w-[18px]" />
          </span>

          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span data-test="security-event-label" class="chip">{{ eventLabel(e.event) }}</span>
              <!-- 被聚合过的行：把「反复失败」这个信号提到最显眼处，它才是真正值得动作的信息 -->
              <span v-if="e.occurrences > 1" data-test="security-occurrences" class="chip !bg-clay/10 !text-clay">
                同一来源 {{ e.occurrences }} 次
              </span>
            </div>

            <p class="mt-2 text-[15px] leading-snug text-ink">{{ eventHint(e.event) }}</p>

            <p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-dim">
              <span>
                被尝试的账号
                <span data-test="security-account" class="font-medium text-ink-mid">{{ e.account || '未识别' }}</span>
              </span>
              <span v-if="e.ip" data-test="security-ip">来源 {{ e.ip }}</span>
              <span>{{ e.occurrences > 1 ? '最近' : '' }}{{ relativeTime(e.lastSeenAt) }}</span>
              <span v-if="e.occurrences > 1">首次 {{ relativeTime(e.firstSeenAt) }}</span>
            </p>
          </div>
        </article>
      </div>

      <div v-if="security.items.length && security.items.length < security.total" class="mt-6 text-center">
        <button class="btn-ghost" :disabled="security.loadingMore" @click="loadMore(security, SECURITY_CFG)">
          {{ security.loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </section>

    <!-- ===================== 我的操作 ===================== -->
    <section v-else-if="tab === 'activity'" data-test="activity-panel" class="mt-6">
      <!-- 类型筛选。列表行不重复动作名：后端 summary 本来就以动词开头。 -->
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="opt in ACTION_FILTERS"
          :key="opt.value"
          data-test="activity-filter"
          class="chip-link"
          :class="activity.filter === opt.value ? '!bg-pine-soft !text-pine-deep' : ''"
          @click="applyFilter(activity, ACTIVITY_CFG, opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>

      <!-- 口径说明：把「什么不记」也讲清楚，免得用户以为日志漏记了 -->
      <p class="mt-3 text-xs leading-relaxed text-ink-dim">
        只记录会留下内容或改变状态的操作。点赞、收藏、参与这类可反复切换的高频动作刻意不记，否则时间线会被噪音淹没。
      </p>

      <div v-if="activity.loading" class="card mt-4 divide-y divide-line overflow-hidden !p-0">
        <div v-for="i in 3" :key="i" class="flex items-start gap-3 px-5 py-4">
          <div class="h-9 w-9 shrink-0 animate-pulse rounded-full bg-sand"></div>
          <div class="min-w-0 flex-1 space-y-2 py-1">
            <div class="h-3.5 w-3/5 animate-pulse rounded bg-sand"></div>
            <div class="h-3 w-2/5 animate-pulse rounded bg-sand"></div>
          </div>
        </div>
      </div>

      <template v-else-if="!activity.items.length">
        <EmptyState
          icon="history"
          :title="activity.filter ? '没有这类操作' : '还没有操作记录'"
          :description="
            activity.filter
              ? '这个类型下暂时没有记录，换个类型看看。'
              : '你发布项目、编辑内容、发表评论、修改资料时，这里会留下一条记录。'
          "
        >
          <button v-if="activity.filter" class="btn-secondary text-sm" @click="applyFilter(activity, ACTIVITY_CFG, '')">
            查看全部类型
          </button>
        </EmptyState>
      </template>

      <div v-else data-test="activity-list" class="card mt-4 divide-y divide-line overflow-hidden !p-0">
        <article
          v-for="(l, i) in activity.items"
          :key="l.id"
          v-reveal="Math.min(i, 8) * 40"
          data-test="log-row"
          :data-action="l.action"
          class="flex items-start gap-3 px-5 py-4"
        >
          <span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-pine-soft text-pine-deep">
            <AppIcon :name="actionIcon(l.action)" class="h-[18px] w-[18px]" />
          </span>

          <div class="min-w-0 flex-1">
            <p data-test="log-summary" class="break-words text-[15px] leading-snug text-ink">{{ l.summary }}</p>
            <p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-dim">
              <span>{{ relativeTime(l.createdAt) }}</span>
              <span v-if="l.ip">来源 {{ l.ip }}</span>
            </p>
          </div>
        </article>
      </div>

      <div v-if="activity.items.length && activity.items.length < activity.total" class="mt-6 text-center">
        <button class="btn-ghost" :disabled="activity.loadingMore" @click="loadMore(activity, ACTIVITY_CFG)">
          {{ activity.loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </section>

    <!-- ===================== 登录密码 ===================== -->
    <!-- 这一栏是纯表单，没有列表要拉 —— 所以 ensureLoaded / configOf 都刻意跳过它 -->
    <section v-else data-test="password-panel" class="mt-6">
      <form class="card max-w-xl p-6 sm:p-8" @submit.prevent="submitPassword">
        <div class="flex items-start gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-pine-soft text-pine-deep">
            <AppIcon name="lock" class="h-[18px] w-[18px]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base font-medium text-ink">修改登录密码</h2>
            <p class="mt-1 text-[13px] leading-relaxed text-ink-mid">
              修改后，其他设备上的登录会立即失效，需要重新登录；当前设备不受影响。
            </p>
          </div>
        </div>

        <div class="mt-6 space-y-5">
          <div>
            <label class="form-label" for="pw-old">当前密码</label>
            <input
              id="pw-old"
              data-test="pw-old"
              v-model="pwForm.old"
              type="password"
              class="input"
              placeholder="请输入当前登录密码"
              autocomplete="current-password"
            />
            <p v-if="pwErrors.old" data-test="pw-error-old" class="form-error">{{ pwErrors.old }}</p>
          </div>

          <div>
            <label class="form-label" for="pw-next">新密码</label>
            <input
              id="pw-next"
              data-test="pw-next"
              v-model="pwForm.next"
              type="password"
              class="input"
              :placeholder="`至少 ${PASSWORD_MIN_LENGTH} 位`"
              autocomplete="new-password"
              :maxlength="PASSWORD_MAX_LENGTH"
            />
            <!-- 强度条：与注册页同一份口径（utils/password.js） -->
            <div v-if="pwForm.next" class="mt-2 flex items-center gap-2">
              <div class="flex flex-1 gap-1">
                <span
                  v-for="i in 3"
                  :key="i"
                  class="h-1 flex-1 rounded-full transition-colors"
                  :class="i <= strength.level ? strength.color : 'bg-sand'"
                ></span>
              </div>
              <span class="text-xs" :class="strength.textColor">{{ strength.label }}</span>
            </div>
            <p v-if="pwErrors.next" data-test="pw-error-next" class="form-error">{{ pwErrors.next }}</p>
          </div>

          <div>
            <label class="form-label" for="pw-confirm">确认新密码</label>
            <input
              id="pw-confirm"
              data-test="pw-confirm"
              v-model="pwForm.confirm"
              type="password"
              class="input"
              placeholder="再次输入新密码"
              autocomplete="new-password"
              :maxlength="PASSWORD_MAX_LENGTH"
            />
            <p v-if="pwErrors.confirm" data-test="pw-error-confirm" class="form-error">{{ pwErrors.confirm }}</p>
          </div>
        </div>

        <!-- 后端 4xx 的业务文案落在这里（就地红字，不弹全局提示）。
             刻意不猜「这条错误该挂在哪个输入框上」—— 按文案猜字段是脆弱做法。 -->
        <p v-if="pwErrors.form" data-test="pw-error-form" class="form-error mt-4">{{ pwErrors.form }}</p>

        <div class="mt-6 flex justify-end">
          <button type="submit" data-test="pw-submit" class="btn-primary" :disabled="pwSaving">
            {{ pwSaving ? '保存中…' : '保存新密码' }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMyLogs, getMySecurityEvents } from '@/api/log'
import { updatePassword } from '@/api/user'
import { useUserStore } from '@/store/user'
import { toast } from '@/composables/useToast'
import { relativeTime } from '@/utils/time'
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, passwordStrength } from '@/utils/password'
import {
  ACTION_FILTERS,
  EVENT_FILTERS,
  actionIcon,
  eventHint,
  eventLabel,
  pickFilter
} from '@/utils/audit'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const PAGE_SIZE = 15

const TAB_OPTIONS = [
  { value: 'security', label: '安全提醒' },
  { value: 'activity', label: '我的操作' },
  { value: 'password', label: '登录密码' }
]
const TAB_VALUES = TAB_OPTIONS.map((o) => o.value)

// 两个视图的列表机制完全相同（分页 / 追加 / 筛选 / 空状态），所以共用下面一组函数、
// 各自持一份状态 —— 免得同一套「加载更多」写两遍，然后慢慢漂移成两个行为。
//
// 用 reactive 的**普通字段**而不是 ref：模板里 `security.items` 直接就是数组。
// （ref 嵌在普通对象里不会自动解包，写成 `security.items.length` 会静默拿到 undefined，
// 症状是整块列表渲染成空、还报 `Cannot read properties of undefined (reading 'length')`。）
const newListState = () =>
  reactive({ items: [], total: 0, page: 1, loading: true, loadingMore: false, filter: '', loaded: false })

const security = newListState()
const activity = newListState()

// 两条接口的响应字段名不同（events / logs），配置里显式写出来，不在读取处硬编码
const SECURITY_CFG = { fetcher: getMySecurityEvents, itemsKey: 'events', filterKey: 'event' }
const ACTIVITY_CFG = { fetcher: getMyLogs, itemsKey: 'logs', filterKey: 'action' }

const buildParams = (state, cfg, target) => {
  const params = { page: target, pageSize: PAGE_SIZE }
  // 空字符串表示「全部」：不能把 '' 当筛选值发给后端（那是无效枚举，会拿到 400）
  if (state.filter) params[cfg.filterKey] = state.filter
  return params
}

const loadFirst = async (state, cfg) => {
  state.loading = true
  try {
    const res = await cfg.fetcher(buildParams(state, cfg, 1))
    state.items = res.data[cfg.itemsKey] || []
    state.total = res.data.total || 0
    state.page = res.data.page || 1
  } catch {
    // 错误已由 axios 拦截器统一提示；这里只负责把列表落回空态
    state.items = []
    state.total = 0
  } finally {
    state.loading = false
    // 无论成败都记「拉过了」：切换标签回来时不必重拉（失败时用户也能靠重进页面再试）
    state.loaded = true
  }
}

const loadMore = async (state, cfg) => {
  if (state.loadingMore) return
  state.loadingMore = true
  try {
    const res = await cfg.fetcher(buildParams(state, cfg, state.page + 1))
    state.items.push(...(res.data[cfg.itemsKey] || []))
    state.total = res.data.total || 0
    state.page = res.data.page || state.page + 1
  } catch {
    // 同上
  } finally {
    state.loadingMore = false
  }
}

// 标签页与筛选都写进 URL：可分享、可后退。只带**当前视图**那一个参数 ——
// 免得另一侧的旧筛选在 URL 里阴魂不散，也免得复制的链接落到别的视图上。
const tab = ref(TAB_VALUES.includes(route.query.tab) ? route.query.tab : 'security')
security.filter = pickFilter(route.query.event, EVENT_FILTERS)
activity.filter = pickFilter(route.query.action, ACTION_FILTERS)

const syncRoute = () => {
  const query = {}
  if (tab.value !== 'security') query.tab = tab.value
  if (tab.value === 'security' && security.filter) query.event = security.filter
  if (tab.value === 'activity' && activity.filter) query.action = activity.filter
  router.replace({ query })
}

const configOf = (value) => (value === 'security' ? SECURITY_CFG : ACTIVITY_CFG)
const stateOf = (value) => (value === 'security' ? security : activity)

const ensureLoaded = (value) => {
  // 「登录密码」是纯表单，没有列表要拉 —— 让它落进 configOf/stateOf 会拿到 activity 的配置
  if (value === 'password') return
  const state = stateOf(value)
  if (!state.loaded) loadFirst(state, configOf(value))
}

const switchTab = (value) => {
  if (tab.value === value) return
  tab.value = value
  syncRoute()
  ensureLoaded(value)
}

const applyFilter = (state, cfg, value) => {
  if (state.filter === value) return
  state.filter = value
  syncRoute()
  loadFirst(state, cfg)
}

// ---- 登录密码 ----
const pwForm = reactive({ old: '', next: '', confirm: '' })
const pwErrors = reactive({ old: '', next: '', confirm: '', form: '' })
const pwSaving = ref(false)
const strength = computed(() => passwordStrength(pwForm.next))

const clearPasswordErrors = () => {
  pwErrors.old = ''
  pwErrors.next = ''
  pwErrors.confirm = ''
  pwErrors.form = ''
}

const submitPassword = async () => {
  if (pwSaving.value) return

  // 只做「本地能判定」的校验；「当前密码对不对」只有服务端知道，不在这里猜
  const local = {
    old: pwForm.old ? '' : '请输入当前密码',
    next: pwForm.next.length >= PASSWORD_MIN_LENGTH ? '' : `密码至少 ${PASSWORD_MIN_LENGTH} 位`,
    confirm: pwForm.confirm === pwForm.next ? '' : '两次输入的密码不一致'
  }
  clearPasswordErrors()
  Object.assign(pwErrors, local)
  if (local.old || local.next || local.confirm) return

  pwSaving.value = true
  try {
    const res = await updatePassword({ oldPassword: pwForm.old, newPassword: pwForm.next })
    // 🔥 服务端已经把此前签发的所有令牌作废并换发了一张新的，必须立刻落回本地：
    // 否则当前页面下一次请求（顶栏每 60 秒的未读轮询）就会 401
    userStore.updateToken(res.data.token)
    toast('密码已更新，其他设备需要重新登录')
    pwForm.old = ''
    pwForm.next = ''
    pwForm.confirm = ''
  } catch (e) {
    // 4xx 是后端写好的普通话，就地红字；5xx / 网络错误交给拦截器统一提示（不再弹一次）
    const status = e.response?.status
    if (status && status < 500) {
      clearPasswordErrors()
      pwErrors.form = e.response?.data?.message || '修改失败，请稍后重试'
    }
  } finally {
    pwSaving.value = false
  }
}

const subtitle = computed(() => {
  if (tab.value === 'password') return '定期更换密码，并避免在别的网站复用同一个密码'
  if (tab.value === 'activity') {
    // 条数用服务端的 total，不用本页条数 —— 分页时「共 N 条」才不会骗人
    return activity.loading || activity.total === 0
      ? '你发布、编辑、评论与修改资料时，这里会留下记录'
      : `共 ${activity.total} 条记录`
  }
  if (security.loading) return '这里记录针对你账号的失败尝试'
  if (security.total > 0) return `有 ${security.total} 条针对你账号的失败尝试`
  return '目前没有发现针对你账号的异常尝试'
})

// 支持直接落地 /security?tab=activity&action=…，以及浏览器前进后退。
// 比较路由字符串而不是 query 对象引用：replace 每次都换新对象，引用比较会漏。
watch(
  () => JSON.stringify(route.query),
  () => {
    const q = route.query
    const nextTab = TAB_VALUES.includes(q.tab) ? q.tab : 'security'
    if (nextTab !== tab.value) {
      tab.value = nextTab
      ensureLoaded(nextTab)
    }
    // URL 是筛选的唯一事实来源：回退一步就把筛选同步回来
    const nextEvent = pickFilter(q.event, EVENT_FILTERS)
    if (nextEvent !== security.filter) {
      security.filter = nextEvent
      loadFirst(security, SECURITY_CFG)
    }
    const nextAction = pickFilter(q.action, ACTION_FILTERS)
    if (nextAction !== activity.filter) {
      activity.filter = nextAction
      loadFirst(activity, ACTIVITY_CFG)
    }
  }
)

onMounted(() => ensureLoaded(tab.value))
</script>

<template>
  <div class="card p-5">
    <div class="mb-3 flex items-center justify-between">
      <p class="text-xs font-medium tracking-wide text-ink-dim">共创伙伴</p>
      <span v-if="count" data-test="participants-count" class="text-xs tabular-nums text-ink-dim">
        {{ count }} 位
      </span>
    </div>

    <!-- 头像堆叠 -->
    <div v-if="stack.length" class="flex items-center">
      <div class="flex -space-x-2.5" data-test="participant-stack">
        <span
          v-for="p in stack"
          :key="p.id"
          data-test="participant-avatar"
          class="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-sm font-bold text-pine-deep ring-2 ring-cream"
          :title="p.username"
        >
          <img v-if="p.avatar" :src="p.avatar" alt="" class="h-full w-full object-cover" />
          <template v-else>{{ initial(p.username) }}</template>
        </span>
        <span
          v-if="overflow"
          data-test="participant-overflow"
          class="flex h-9 w-9 items-center justify-center rounded-full bg-sand text-xs font-semibold tabular-nums text-ink-mid ring-2 ring-cream"
        >
          +{{ overflow }}
        </span>
      </div>
    </div>
    <p v-else class="text-sm leading-relaxed text-ink-mid">
      还没有人加入，来成为第一位共创伙伴吧。
    </p>

    <button
      v-if="count"
      data-test="open-participants"
      class="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-sand px-3 py-2 text-sm font-medium text-ink transition-colors hover:bg-line"
      @click="openModal"
    >
      <AppIcon name="users" class="h-3.5 w-3.5" />
      查看全部共创伙伴
    </button>
  </div>

  <!-- 全部共创伙伴弹层 -->
  <Teleport to="body">
    <transition name="modal">
      <div
        v-if="opened"
        data-test="participants-modal"
        class="fixed inset-0 z-[90] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
        role="dialog"
        aria-modal="true"
        aria-label="全部共创伙伴"
        @click.self="closeModal"
      >
        <div class="card flex max-h-[80vh] w-full max-w-md flex-col p-6 shadow-pop">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="font-display text-xl font-bold text-ink">共创伙伴</h3>
              <p class="mt-1 text-sm text-ink-dim" data-test="participants-total">
                共 {{ total || count }} 位伙伴参与了这个项目
              </p>
            </div>
            <button
              data-test="close-participants"
              class="btn-ghost -mr-1 !p-1.5"
              aria-label="关闭"
              @click="closeModal"
            >
              <AppIcon name="x" class="h-4 w-4" />
            </button>
          </div>

          <!-- 加载中 -->
          <div v-if="loading" class="mt-5 space-y-2">
            <div v-for="i in 4" :key="i" class="flex items-center gap-3">
              <div class="skeleton h-9 w-9 !rounded-full"></div>
              <div class="flex-1 space-y-1.5">
                <div class="skeleton h-3.5 w-1/3"></div>
                <div class="skeleton h-3 w-1/4"></div>
              </div>
            </div>
          </div>

          <!-- 名单 -->
          <ul v-else class="-mx-1 mt-3 min-h-0 flex-1 space-y-0.5 overflow-y-auto px-1">
            <li
              v-for="p in list"
              :key="p.id"
              data-test="participant-row"
              class="flex items-center gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-sand/60"
            >
              <span
                class="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-sm font-bold text-pine-deep"
              >
                <img v-if="p.avatar" :src="p.avatar" alt="" class="h-full w-full object-cover" />
                <template v-else>{{ initial(p.username) }}</template>
              </span>
              <div class="min-w-0 flex-1">
                <router-link
                  :to="`/user/${p.id}`"
                  data-test="participant-name"
                  class="block truncate text-sm font-medium text-ink transition-colors hover:text-pine"
                >
                  {{ p.username }}
                </router-link>
                <p class="truncate text-xs text-ink-dim">
                  {{ roleLabel(p.role) }}<template v-if="p.joinedAt"> · {{ relativeTime(p.joinedAt) }}加入</template>
                </p>
              </div>
              <span
                v-if="p.role === 'creator'"
                class="shrink-0 rounded-full bg-pine-soft px-2 py-0.5 text-xs font-medium text-pine-deep"
              >
                发起人
              </span>
            </li>
          </ul>

          <button
            v-if="!loading && list.length < total"
            data-test="load-more-participants"
            class="btn-secondary mt-4 w-full !py-2.5 text-sm"
            :disabled="loadingMore"
            @click="loadMore"
          >
            {{ loadingMore ? '加载中…' : '加载更多' }}
          </button>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as projectApi from '@/api/project'
import { relativeTime } from '@/utils/time'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  projectId: { type: [Number, String], required: true },
  // 详情页下发的预览名单（最多 8 位，发起人置顶）
  participants: { type: Array, default: () => [] },
  count: { type: Number, default: 0 }
})

const PAGE_SIZE = 30
const STACK_MAX = 6

// 头像堆叠最多展示 6 位，其余折算成 +N
const stack = computed(() => props.participants.slice(0, STACK_MAX))
const overflow = computed(() => Math.max(0, props.count - stack.value.length))

const opened = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)

const initial = (name) => (name || '友').slice(0, 1).toUpperCase()
const roleLabel = (role) =>
  role === 'creator' ? '项目发起人' : role === 'observer' ? '观察者' : '共创伙伴'

let scrollLocked = false
const lockScroll = (on) => {
  if (on === scrollLocked) return
  document.body.style.overflow = on ? 'hidden' : ''
  scrollLocked = on
}

const fetchPage = async (p) => {
  const first = p === 1
  if (first) loading.value = true
  else loadingMore.value = true
  try {
    const res = await projectApi.getProjectParticipants(props.projectId, { page: p, pageSize: PAGE_SIZE })
    const items = res.data.participants || []
    list.value = first ? items : list.value.concat(items)
    total.value = res.data.total || 0
    page.value = res.data.page || p
  } catch {
    // 错误已由请求拦截器统一 toast
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

// 每次打开都拉第一页：期间他人可能已加入，缓存无意义
const openModal = () => {
  opened.value = true
  lockScroll(true)
  fetchPage(1)
}

const closeModal = () => {
  opened.value = false
  lockScroll(false)
}

const loadMore = () => {
  if (loadingMore.value) return
  fetchPage(page.value + 1)
}

const onKeydown = (e) => {
  if (e.key === 'Escape' && opened.value) closeModal()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  lockScroll(false)
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.22s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .card,
.modal-leave-active .card {
  transition: transform 0.22s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.modal-enter-from .card,
.modal-leave-to .card {
  transform: scale(0.96);
}

@media (prefers-reduced-motion: reduce) {
  .modal-enter-active,
  .modal-leave-active,
  .modal-enter-active .card,
  .modal-leave-active .card {
    transition: none;
  }
  .modal-enter-from .card,
  .modal-leave-to .card {
    transform: none;
  }
}
</style>

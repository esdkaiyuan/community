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

      <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <ProjectCard
          v-for="(p, i) in myProjects"
          :key="p.id"
          v-reveal="Math.min(i, 5) * 60"
          :project="p"
        />
      </div>
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
import { updateProfile } from '@/api/user'
import { toast } from '@/composables/useToast'
import ProjectCard from '@/components/ProjectCard.vue'
import ProjectCardSkeleton from '@/components/ProjectCardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore = useUserStore()
const user = computed(() => userStore.userInfo)

const myProjects = ref([])
const loadingProjects = ref(true)

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

onMounted(async () => {
  // 确保 userId 可用后再过滤
  if (!user.value) await userStore.fetchMe().catch(() => {})
  fetchMyProjects()
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

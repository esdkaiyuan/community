<template>
  <!-- 加密项目 / 加密仓库的统一解锁入口：密码只在本组件内流转，不写进 URL -->
  <section
    class="unlock-card"
    :class="{ 'unlock-card--repo': mode === 'repo' }"
    data-test="unlock-card"
  >
    <div class="flex items-start gap-3.5">
      <span class="unlock-card__icon" aria-hidden="true">
        <AppIcon name="lock" class="h-5 w-5" />
      </span>
      <div class="min-w-0 flex-1">
        <p class="mono-label">
          ENCRYPTED / {{ mode === 'repo' ? 'REPOSITORY' : 'PROJECT' }}
        </p>
        <h2 class="mt-1.5 font-brand text-title2 font-bold text-ink">
          {{ mode === 'repo' ? '仓库地址已加密' : '这是一个加密项目' }}
        </h2>
        <p class="mt-1.5 max-w-xl text-footnote leading-relaxed text-ink-mid">
          {{
            mode === 'repo'
              ? '项目内容可以公开浏览，但仓库地址需要输入发起人设置的密码才能查看。'
              : '项目介绍、标签、仓库地址与共创伙伴需要输入发起人设置的密码才能查看。'
          }}
        </p>
      </div>
    </div>

    <form class="mt-5 flex flex-col gap-2 sm:flex-row sm:items-start" @submit.prevent="submit">
      <div class="min-w-0 flex-1">
        <label class="sr-only" :for="inputId">访问密码</label>
        <input
          :id="inputId"
          v-model="password"
          type="password"
          class="input"
          :placeholder="mode === 'repo' ? '输入仓库访问密码' : '输入项目访问密码'"
          maxlength="64"
          autocomplete="off"
          data-test="unlock-password"
          @input="error = ''"
        />
      </div>
      <button
        type="submit"
        class="btn-primary shrink-0 !px-5 !py-2.5"
        :disabled="acting"
        data-test="unlock-submit"
      >
        <svg v-if="acting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
          <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        </svg>
        <AppIcon v-else name="lock" class="h-4 w-4" />
        {{ acting ? '验证中…' : '解锁查看' }}
      </button>
    </form>

    <p v-if="error" class="form-error mt-2" data-test="unlock-error">{{ error }}</p>
    <p v-else class="mt-2.5 text-caption1 leading-relaxed text-ink-dim">
      密码由项目发起人设置。不知道密码？可以在发起人主页找到 TA，直接联系获取。
    </p>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { unlockProject } from '@/api/project'
import { toast } from '@/composables/useToast'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  projectId: { type: [Number, String], required: true },
  mode: { type: String, default: 'project' } // project | repo
})

const emit = defineEmits(['unlocked'])

const password = ref('')
const error = ref('')
const acting = ref(false)
const inputId = computed(() => `unlock-password-${props.mode}-${props.projectId}`)

const submit = async () => {
  if (acting.value) return
  error.value = ''
  if (!password.value) {
    error.value = '请输入访问密码'
    return
  }

  acting.value = true
  try {
    const res = await unlockProject(props.projectId, password.value)
    password.value = ''
    toast(props.mode === 'repo' ? '仓库地址已解锁' : '项目已解锁')
    emit('unlocked', res.data)
  } catch (e) {
    const status = e.response?.status
    const message = e.response?.data?.message || ''
    if (status === 403) error.value = '密码不正确，请重试'
    else if (status === 429) error.value = '尝试次数过多，请 15 分钟后再试'
    else error.value = message || '解锁失败，请稍后重试'
  } finally {
    acting.value = false
  }
}
</script>

<style scoped>
.unlock-card {
  @apply bg-cream p-6 sm:p-8;
  border: 1.5px solid rgb(var(--c-ink) / 0.18);
  border-radius: 18px 24px 16px 26px / 24px 16px 26px 18px;
  box-shadow: 5px 6px 0 rgb(var(--c-ink) / 0.06);
}

/* 仓库加密是页面内的次要操作，视觉上轻一档 */
.unlock-card--repo {
  @apply p-5;
  border-style: dashed;
  box-shadow: 3px 4px 0 rgb(var(--c-ink) / 0.04);
}

.unlock-card__icon {
  @apply flex h-11 w-11 shrink-0 items-center justify-center rounded-full;
  color: rgb(var(--c-clay));
  border: 1.5px solid rgb(var(--c-clay) / 0.35);
  background: rgb(var(--c-clay) / 0.08);
}
</style>

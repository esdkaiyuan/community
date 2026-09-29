<template>
  <div class="mx-auto flex max-w-5xl items-center px-4 py-12 sm:px-6 sm:py-16">
    <div class="card grid w-full overflow-hidden md:grid-cols-2">
      <!-- 品牌面板 -->
      <div class="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-b from-pine to-pine-deep p-10 text-white md:flex">
        <div class="relative">
          <span class="text-xs tracking-[0.3em] opacity-70">CO-CREATION COMMUNITY</span>
          <h2 class="mt-4 font-display text-3xl font-semibold leading-snug tracking-tight">
            加入共创社区，<br />让想法遇见同行者
          </h2>
        </div>
        <ul class="relative space-y-3 text-sm opacity-85">
          <li class="flex items-center gap-2.5"><AppIcon name="lightbulb" class="h-4 w-4 shrink-0" />发布项目，寻找志同道合的伙伴</li>
          <li class="flex items-center gap-2.5"><AppIcon name="users" class="h-4 w-4 shrink-0" />参与感兴趣的项目，贡献力量</li>
          <li class="flex items-center gap-2.5"><AppIcon name="sprout" class="h-4 w-4 shrink-0" />见证创意从萌芽到落地</li>
        </ul>
      </div>

      <!-- 表单 -->
      <div class="p-8 sm:p-10">
        <h1 class="font-display text-3xl font-semibold tracking-tight text-ink">创建账号</h1>
        <p class="mt-1.5 text-sm text-ink-mid">
          已有账号？
          <router-link to="/login" class="font-medium text-pine hover:underline">直接登录</router-link>
        </p>

        <form class="mt-8 space-y-5" @submit.prevent="handleSubmit">
          <div>
            <label class="form-label" for="username">用户名</label>
            <input
              id="username"
              v-model.trim="form.username"
              type="text"
              class="input"
              placeholder="2-20 个字符"
              autocomplete="username"
              maxlength="20"
            />
            <p v-if="errors.username" class="form-error">{{ errors.username }}</p>
          </div>

          <div>
            <label class="form-label" for="email">邮箱</label>
            <input
              id="email"
              v-model.trim="form.email"
              type="email"
              class="input"
              placeholder="you@example.com"
              autocomplete="email"
            />
            <p v-if="errors.email" class="form-error">{{ errors.email }}</p>
          </div>

          <div>
            <label class="form-label" for="password">密码</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              class="input"
              placeholder="至少 6 位"
              autocomplete="new-password"
            />
            <!-- 密码强度 -->
            <div v-if="form.password" class="mt-2 flex items-center gap-2">
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
            <p v-if="errors.password" class="form-error">{{ errors.password }}</p>
          </div>

          <div>
            <label class="form-label" for="confirm">确认密码</label>
            <input
              id="confirm"
              v-model="form.confirm"
              type="password"
              class="input"
              placeholder="再次输入密码"
              autocomplete="new-password"
            />
            <p v-if="errors.confirm" class="form-error">{{ errors.confirm }}</p>
          </div>

          <button type="submit" class="btn-primary w-full !py-3" :disabled="submitting">
            <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
            </svg>
            {{ submitting ? '注册中…' : '注册并加入' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { toast } from '@/composables/useToast'
import { stripEmoji } from '@/utils/text'
import AppIcon from '@/components/AppIcon.vue'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({ username: '', email: '', password: '', confirm: '' })
const errors = reactive({ username: '', email: '', password: '', confirm: '' })
const submitting = ref(false)

// 密码强度：长度 + 字符种类
const strength = computed(() => {
  const p = form.password
  let score = 0
  if (p.length >= 6) score++
  if (p.length >= 10) score++
  if (/[a-zA-Z]/.test(p) && /\d/.test(p)) score++
  if (/[^a-zA-Z0-9]/.test(p)) score++

  if (score <= 1) return { level: 1, label: '较弱', color: 'bg-clay', textColor: 'text-clay' }
  if (score <= 2) return { level: 2, label: '中等', color: 'bg-amber-warm', textColor: 'text-amber-warm' }
  return { level: 3, label: '强', color: 'bg-pine', textColor: 'text-pine' }
})

const validate = () => {
  errors.username = form.username.length >= 2 && form.username.length <= 20 ? '' : '用户名需 2-20 个字符'
  errors.email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? '' : '请输入有效的邮箱地址'
  errors.password = form.password.length >= 6 ? '' : '密码至少 6 位'
  errors.confirm = form.confirm === form.password ? '' : '两次输入的密码不一致'
  return !errors.username && !errors.email && !errors.password && !errors.confirm
}

const handleSubmit = async () => {
  // 全站仅允许矢量图标：提交前移除用户名里的 emoji（与 ProjectForm 同一约定）。
  // 服务端会做同样的归一化，这里先做一次是为了让用户**在表单里就看见**自己被改成了什么，
  // 而不是提交成功后悄悄换掉一个名字。
  form.username = stripEmoji(form.username)
  if (!validate() || submitting.value) return
  submitting.value = true
  try {
    await userStore.register({
      username: form.username,
      email: form.email,
      password: form.password
    })
    toast(`欢迎加入共创社区，${userStore.username}！`)
    router.push('/')
  } catch {
    // 具体错误已由拦截器 toast
  } finally {
    submitting.value = false
  }
}
</script>


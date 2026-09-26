<template>
  <div class="mx-auto flex max-w-5xl items-center px-4 py-12 sm:px-6 sm:py-16">
    <div class="card grid w-full overflow-hidden md:grid-cols-2">
      <!-- 品牌面板 -->
      <div class="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-b from-pine to-pine-deep p-10 text-white md:flex">
        <div class="relative">
          <span class="text-xs tracking-[0.3em] opacity-70">CO-CREATION COMMUNITY</span>
          <h2 class="mt-4 font-display text-3xl font-bold leading-snug">
            欢迎回来，<br />继续你的共创之旅
          </h2>
        </div>
        <p class="relative text-sm leading-relaxed opacity-80">
          "好的想法从不孤单。<br />在这里，总有人愿意和你一起把它做出来。"
        </p>
      </div>

      <!-- 表单 -->
      <div class="p-8 sm:p-10">
        <h1 class="font-display text-2xl font-bold text-ink">登录</h1>
        <p class="mt-1.5 text-sm text-ink-mid">
          还没有账号？
          <router-link to="/register" class="font-medium text-pine hover:underline">立即注册</router-link>
        </p>

        <form class="mt-8 space-y-5" @submit.prevent="handleSubmit">
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
            <div class="relative">
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="input pr-11"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-ink-dim transition-colors hover:text-ink"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" class="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else class="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M3 3l18 18M10.6 5.1A9.8 9.8 0 0 1 12 5c6.5 0 10 7 10 7a17.5 17.5 0 0 1-2.5 3.4M6.6 6.6C3.8 8.4 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.3-1" />
                </svg>
              </button>
            </div>
            <p v-if="errors.password" class="form-error">{{ errors.password }}</p>
          </div>

          <button type="submit" class="btn-primary w-full !py-3" :disabled="submitting">
            <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
            </svg>
            {{ submitting ? '登录中…' : '登 录' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { toast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const submitting = ref(false)
const showPassword = ref(false)

const validate = () => {
  errors.email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? '' : '请输入有效的邮箱地址'
  errors.password = form.password.length >= 6 ? '' : '密码至少 6 位'
  return !errors.email && !errors.password
}

const handleSubmit = async () => {
  if (!validate() || submitting.value) return
  submitting.value = true
  try {
    await userStore.login({ email: form.email, password: form.password })
    toast(`欢迎回来，${userStore.username}！`)
    router.push(route.query.redirect || '/')
  } catch {
    // 具体错误已由拦截器 toast
  } finally {
    submitting.value = false
  }
}
</script>


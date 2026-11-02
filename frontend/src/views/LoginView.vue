<template>
  <div class="w-full px-4 py-8 sm:px-6 sm:py-10">
    <div class="auth-card mx-auto grid w-full max-w-5xl overflow-hidden md:grid-cols-[1.02fr_0.98fr]">
      <!-- 左：手绘共创面板（创意 → 互助 → 合作） -->
      <AuthBrandPanel
        title="欢迎回来，"
        accent="继续你的共创之旅"
        quote="好的想法从不孤单。在这里，总有人愿意搭把手，和你一起把它做出来。"
      />

      <!-- 右：表单；移动端顶部自带品牌带，无需页头页脚 -->
      <div class="flex flex-col justify-center p-6 sm:p-9 lg:px-11">
        <p class="eyebrow">Account</p>
        <h1 class="mt-3 font-brand text-[clamp(1.9rem,2.4vw,2.4rem)] font-bold tracking-normal text-ink">登录</h1>
        <p class="mt-2 text-footnote text-ink-mid">
          还没有账号？
          <router-link to="/register" class="font-medium text-pine hover:underline">立即注册</router-link>
        </p>

        <!-- 密码登录 / 邮箱验证码登录：两个平级入口，用分段控件切换 -->
        <AppSegmented
          :model-value="mode"
          :options="MODES"
          aria-label="选择登录方式"
          class="mt-6"
          @update:model-value="switchMode"
        />

        <form class="mt-5" @submit.prevent="handleSubmit">
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
            <p v-else class="mt-1.5 text-caption1 text-ink-dim">验证码与站内通知都会发到这个邮箱。</p>
          </div>

          <!-- 模式区固定最小高度：切换登录方式时卡片高度不变 -->
          <div class="mt-5 min-h-[96px]">
            <div v-if="mode === 'password'">
              <div class="flex items-center justify-between">
                <label class="form-label" for="password">密码</label>
                <router-link to="/forgot-password" class="text-caption1 text-pine hover:underline">
                  忘记密码？
                </router-link>
              </div>
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
                  <!-- ⚠️ h-4.5 不是合法的 Tailwind 尺寸类（默认 spacing 只有 0.5/1.5/2.5/3.5），
                       写了会静默不生成 CSS，svg 失去尺寸约束被撑成巨图 -->
                  <svg v-if="showPassword" class="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg v-else class="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <path d="M3 3l18 18M10.6 5.1A9.8 9.8 0 0 1 12 5c6.5 0 10 7 10 7a17.5 17.5 0 0 1-2.5 3.4M6.6 6.6C3.8 8.4 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.3-1" />
                  </svg>
                </button>
              </div>
              <p v-if="errors.password" class="form-error">{{ errors.password }}</p>
              <p v-else class="mt-1.5 text-caption1 text-ink-dim">用注册时设置的密码登录。</p>
            </div>

            <div v-else>
              <label class="form-label" for="code">邮箱验证码</label>
              <div class="flex gap-2">
                <input
                  id="code"
                  v-model.trim="form.code"
                  type="text"
                  class="input"
                  placeholder="6 位数字验证码"
                  inputmode="numeric"
                  maxlength="6"
                  autocomplete="one-time-code"
                />
                <button
                  type="button"
                  class="btn-secondary shrink-0 whitespace-nowrap !px-3 !py-2.5 text-footnote"
                  :disabled="!canSend"
                  @click="handleSendCode"
                >
                  {{ buttonLabel }}
                </button>
              </div>
              <p v-if="errors.code" class="form-error">{{ errors.code }}</p>
              <p v-else class="mt-1.5 text-caption1 text-ink-dim">验证码 5 分钟内有效；未收到请检查垃圾箱。</p>
            </div>
          </div>

          <button type="submit" class="btn-primary mt-5 w-full !py-3" :disabled="submitting || sending">
            <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
            </svg>
            {{ submitting ? '登录中…' : mode === 'password' ? '登 录' : '验证码登录' }}
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
import { useEmailCode } from '@/composables/useEmailCode'
import { isValidEmail } from '@/utils/email'
import { PASSWORD_MIN_LENGTH } from '@/utils/password'
import AppSegmented from '@/components/AppSegmented.vue'
import AuthBrandPanel from '@/components/AuthBrandPanel.vue'

const MODES = [
  { label: '密码登录', value: 'password' },
  { label: '验证码登录', value: 'code' }
]

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const mode = ref('password')
const form = reactive({ email: '', password: '', code: '' })
const errors = reactive({ email: '', password: '', code: '' })
const submitting = ref(false)
const showPassword = ref(false)
const { sending, canSend, buttonLabel, send } = useEmailCode()

const switchMode = (value) => {
  mode.value = value
  errors.password = ''
  errors.code = ''
}

const validate = () => {
  errors.email = isValidEmail(form.email) ? '' : '请输入有效的邮箱地址'
  if (mode.value === 'password') {
    errors.password = form.password.length >= PASSWORD_MIN_LENGTH ? '' : `密码至少 ${PASSWORD_MIN_LENGTH} 位`
  } else {
    errors.code = /^\d{6}$/.test(form.code) ? '' : '请输入 6 位邮箱验证码'
  }
  return !errors.email && !errors.password && !errors.code
}

const handleSendCode = async () => {
  errors.email = ''
  try {
    await send(form.email)
  } catch (error) {
    errors.email = error.response?.data?.message || error.message || '验证码发送失败，请稍后重试'
  }
}

const handleSubmit = async () => {
  if (!validate() || submitting.value || sending.value) return
  submitting.value = true
  try {
    if (mode.value === 'password') {
      await userStore.login({ email: form.email, password: form.password })
    } else {
      await userStore.loginWithEmailCode({ email: form.email, code: form.code })
    }
    toast(`欢迎回来，${userStore.username}！`)
    router.push(route.query.redirect || '/')
  } catch (error) {
    // 登录失败就该就地红字（拦截器对「没带 token 的 401」不弹全局提示），
    // 否则点了登录页面毫无反应，用户只会以为是按钮坏了
    const message = error.response?.data?.message || '登录失败，请稍后重试'
    if (mode.value === 'password') errors.password = message
    else errors.code = message
  } finally {
    submitting.value = false
  }
}
</script>

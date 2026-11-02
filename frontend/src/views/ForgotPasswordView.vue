<template>
  <div class="mx-auto flex max-w-5xl items-center px-4 py-12 sm:px-6 sm:py-16">
    <div class="card grid w-full overflow-hidden md:grid-cols-2">
      <!-- 品牌面板 -->
      <div class="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-b from-pine to-pine-deep p-10 text-white md:flex">
        <div class="relative">
          <span class="text-caption1 tracking-[0.3em] opacity-70">CO-CREATION COMMUNITY</span>
          <h2 class="mt-4 font-display text-title1 font-semibold leading-snug tracking-tight">
            忘记密码？<br />用邮箱验证码安全找回
          </h2>
        </div>
        <p class="relative text-footnote leading-relaxed opacity-80">
          验证码会发送到你的注册邮箱。<br />重置成功后，其他设备上的登录会立即失效。
        </p>
      </div>

      <!-- 表单 -->
      <div class="p-8 sm:p-10">
        <h1 class="font-display text-title1 font-semibold tracking-tight text-ink">找回密码</h1>
        <p class="mt-1.5 text-footnote text-ink-mid">
          想起来了？
          <router-link to="/login" class="font-medium text-pine hover:underline">返回登录</router-link>
        </p>

        <form class="mt-8 space-y-5" @submit.prevent="handleSubmit">
          <div>
            <label class="form-label" for="email">注册邮箱</label>
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

          <div>
            <label class="form-label" for="password">新密码</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              class="input"
              placeholder="至少 6 位"
              autocomplete="new-password"
              :maxlength="PASSWORD_MAX_LENGTH"
            />
            <div v-if="form.password" class="mt-2 flex items-center gap-2">
              <div class="flex flex-1 gap-1">
                <span
                  v-for="i in 3"
                  :key="i"
                  class="h-1 flex-1 rounded-full transition-colors"
                  :class="i <= strength.level ? strength.color : 'bg-sand'"
                ></span>
              </div>
              <span class="text-caption1" :class="strength.textColor">{{ strength.label }}</span>
            </div>
            <p v-if="errors.password" class="form-error">{{ errors.password }}</p>
          </div>

          <div>
            <label class="form-label" for="confirm">确认新密码</label>
            <input
              id="confirm"
              v-model="form.confirm"
              type="password"
              class="input"
              placeholder="再次输入新密码"
              autocomplete="new-password"
              :maxlength="PASSWORD_MAX_LENGTH"
            />
            <p v-if="errors.confirm" class="form-error">{{ errors.confirm }}</p>
          </div>

          <p v-if="errors.general" class="form-error">{{ errors.general }}</p>

          <button type="submit" class="btn-primary w-full !py-3" :disabled="submitting || sending">
            <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
            </svg>
            {{ submitting ? '重置中…' : '重置密码' }}
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
import { useEmailCode } from '@/composables/useEmailCode'
import { isValidEmail } from '@/utils/email'
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, passwordStrength } from '@/utils/password'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({ email: '', code: '', password: '', confirm: '' })
const errors = reactive({ email: '', code: '', password: '', confirm: '', general: '' })
const submitting = ref(false)
const { sending, canSend, buttonLabel, send } = useEmailCode()
const strength = computed(() => passwordStrength(form.password))

const validate = () => {
  errors.email = isValidEmail(form.email) ? '' : '请输入有效的邮箱地址'
  errors.code = /^\d{6}$/.test(form.code) ? '' : '请输入 6 位邮箱验证码'
  errors.password = form.password.length >= PASSWORD_MIN_LENGTH ? '' : `密码至少 ${PASSWORD_MIN_LENGTH} 位`
  errors.confirm = form.confirm === form.password ? '' : '两次输入的密码不一致'
  return !errors.email && !errors.code && !errors.password && !errors.confirm
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
  errors.general = ''
  try {
    await userStore.resetPasswordWithEmailCode({
      email: form.email,
      code: form.code,
      password: form.password,
      confirmPassword: form.confirm
    })
    toast('密码已重置，请使用新密码登录')
    router.push('/login')
  } catch (error) {
    const message = error.response?.data?.message || '密码重置失败，请稍后重试'
    if (message.includes('验证码')) errors.code = message
    else if (message.includes('密码')) errors.password = message
    else errors.general = message
  } finally {
    submitting.value = false
  }
}
</script>
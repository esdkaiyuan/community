<template>
  <div class="w-full px-4 py-8 sm:px-6 sm:py-10">
    <div class="auth-card mx-auto grid w-full max-w-5xl overflow-hidden md:grid-cols-[1.02fr_0.98fr]">
      <!-- 左：手绘共创面板（创意 → 互助 → 合作） -->
      <AuthBrandPanel
        title="把想法画出来，"
        accent="和同伴一起做成。"
        quote="第一笔画下创意，第二笔有人搭把手，第三笔就是我们一起把它建成。"
      />

      <!-- 右：表单；移动端顶部自带品牌带，无需页头页脚 -->
      <div class="flex flex-col justify-center p-6 sm:p-9 lg:px-11">
        <p class="eyebrow">Account</p>
        <h1 class="mt-3 font-brand text-[clamp(1.9rem,2.4vw,2.4rem)] font-bold tracking-normal text-ink">创建账号</h1>
        <p class="mt-2 text-footnote text-ink-mid">
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
            <label class="form-label" for="password">密码</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              class="input"
              placeholder="至少 6 位"
              autocomplete="new-password"
              :maxlength="PASSWORD_MAX_LENGTH"
            />
            <!-- 强度条位置常驻，输入第一个字符时表单不跳动 -->
            <div class="mt-2 min-h-[16px]">
              <div v-if="form.password" class="flex items-center gap-2">
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
              :maxlength="PASSWORD_MAX_LENGTH"
            />
            <p v-if="errors.confirm" class="form-error">{{ errors.confirm }}</p>
          </div>

          <button type="submit" class="btn-primary w-full !py-3" :disabled="submitting || sending">
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
import { useEmailCode } from '@/composables/useEmailCode'
import { isValidEmail } from '@/utils/email'
import { stripEmoji } from '@/utils/text'
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, passwordStrength } from '@/utils/password'
import AuthBrandPanel from '@/components/AuthBrandPanel.vue'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({ username: '', email: '', code: '', password: '', confirm: '' })
const errors = reactive({ username: '', email: '', code: '', password: '', confirm: '' })
const submitting = ref(false)
const { sending, canSend, buttonLabel, send } = useEmailCode()

// 密码强度与上下界都来自 utils/password.js —— 与「账号安全 → 登录密码」共用一份口径，
// 免得两处各写一套慢慢漂移（一处改成 8 位、另一处还写着 6 位）
const strength = computed(() => passwordStrength(form.password))

const validate = () => {
  errors.username = form.username.length >= 2 && form.username.length <= 20 ? '' : '用户名需 2-20 个字符'
  errors.email = isValidEmail(form.email) ? '' : '请输入有效的邮箱地址'
  errors.code = /^\d{6}$/.test(form.code) ? '' : '请输入 6 位邮箱验证码'
  errors.password = form.password.length >= PASSWORD_MIN_LENGTH ? '' : `密码至少 ${PASSWORD_MIN_LENGTH} 位`
  errors.confirm = form.confirm === form.password ? '' : '两次输入的密码不一致'
  return !errors.username && !errors.email && !errors.code && !errors.password && !errors.confirm
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
  // 全站仅允许矢量图标：提交前移除用户名里的 emoji（与 ProjectForm 同一约定）。
  // 服务端会做同样的归一化，这里先做一次是为了让用户**在表单里就看见**自己被改成了什么，
  // 而不是提交成功后悄悄换掉一个名字。
  form.username = stripEmoji(form.username)
  if (!validate() || submitting.value || sending.value) return
  submitting.value = true
  try {
    await userStore.registerWithEmailCode({
      username: form.username,
      email: form.email,
      code: form.code,
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

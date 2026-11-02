import { computed, onBeforeUnmount, ref } from 'vue'
import { sendEmailCode } from '@/api/user'
import { toast } from '@/composables/useToast'
import { isValidEmail } from '@/utils/email'

const COUNTDOWN_SECONDS = 60

// 邮箱验证码发送：三个页面（注册 / 验证码登录 / 找回密码）共用同一套倒计时与错误口径。
// 发送失败不弹全局提示，交给页面把红字放在邮箱输入框下面。
export const useEmailCode = () => {
  const sending = ref(false)
  const countdown = ref(0)
  let timer = null

  const canSend = computed(() => countdown.value === 0 && !sending.value)
  const buttonLabel = computed(() => {
    if (sending.value) return '发送中…'
    if (countdown.value > 0) return `${countdown.value}s 后重发`
    return '获取验证码'
  })

  const startCountdown = () => {
    countdown.value = COUNTDOWN_SECONDS
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        clearInterval(timer)
        timer = null
      }
    }, 1000)
  }

  const send = async (email) => {
    if (!isValidEmail(email)) {
      throw new Error('请输入有效的邮箱地址')
    }
    if (!canSend.value) return
    sending.value = true
    try {
      await sendEmailCode({ email: String(email).trim() })
      startCountdown()
      toast('验证码已发送，请查收邮箱')
    } finally {
      sending.value = false
    }
  }

  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
  })

  return { sending, countdown, canSend, buttonLabel, send }
}
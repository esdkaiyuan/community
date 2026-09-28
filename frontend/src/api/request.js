import axios from 'axios'
import { toast } from '@/composables/useToast'
import { clearSession, getToken } from '@/utils/storage'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

// 请求拦截：附带 token
request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一解包 data，统一错误提示
//
// 分工原则（本轮重设计）：
// - 全局提示只负责「用户没法就地修复」的结果（网络断了、服务挂了、登录态失效）
// - 4xx 的业务文案照后端原样展示（「邮箱或密码错误」这类后端已经写成普通话）
// - 「没带 token 的 401」= 用户正在登录、或未登录点了受保护操作 → **不弹全局提示**，
//   交给页面就地显示（登录页红字 / 「请先登录」引导），否则一次失败会弹两层提示
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const serverMessage = error.response?.data?.message
    const hasToken = !!getToken()

    if (!error.response) {
      // 连不上 / 超时：别对用户说「服务器错误」，他能做的只有检查网络
      const timedOut = error.code === 'ECONNABORTED'
      toast(timedOut ? '请求超时了，请检查网络后重试' : '网络连接失败，请检查网络后重试', 'error')
    } else if (status === 401 && hasToken) {
      // 带着 token 还 401 = 登录态失效：清本地并回登录页（复用 router，避免整页刷新）
      clearSession()
      if (router.currentRoute.value.path !== '/login') {
        toast('登录已过期，请重新登录', 'error')
        router.push({
          name: 'Login',
          query: { redirect: router.currentRoute.value.fullPath }
        })
      }
    } else if (status >= 500) {
      // 5xx 的 message 是写给开发者看的，别甩给用户
      toast('服务暂时不可用，请稍后重试', 'error')
    } else if (!(status === 401 && !hasToken)) {
      toast(serverMessage || '操作失败，请稍后重试', 'error')
    }
    return Promise.reject(error)
  }
)

export default request

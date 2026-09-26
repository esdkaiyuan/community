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
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.message || '网络异常，请稍后重试'

    if (status === 401) {
      // token 失效：清除本地登录态并跳转登录页（复用 router，避免整页刷新）
      clearSession()
      if (router.currentRoute.value.path !== '/login') {
        toast(message === '未提供认证令牌' ? '请先登录' : '登录已过期，请重新登录', 'error')
        router.push({
          name: 'Login',
          query: { redirect: router.currentRoute.value.fullPath }
        })
      }
    } else {
      toast(message, 'error')
    }
    return Promise.reject(error)
  }
)

export default request

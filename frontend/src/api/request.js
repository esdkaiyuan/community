import axios from 'axios'
import { toast } from '@/composables/useToast'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

// 请求拦截：附带 token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
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
      // token 失效：清除本地登录态并跳转登录页
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      if (!location.pathname.startsWith('/login')) {
        toast(message === '未提供认证令牌' ? '请先登录' : '登录已过期，请重新登录', 'error')
        setTimeout(() => {
          location.href = `/login?redirect=${encodeURIComponent(location.pathname + location.search)}`
        }, 600)
      }
    } else {
      toast(message, 'error')
    }
    return Promise.reject(error)
  }
)

export default request

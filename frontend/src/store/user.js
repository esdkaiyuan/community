import { defineStore } from 'pinia'
import * as userApi from '@/api/user'

// 安全解析本地缓存的用户信息
const readCachedUser = () => {
  try {
    return JSON.parse(localStorage.getItem('userInfo')) || null
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: readCachedUser()
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.username || '',
    userId: (state) => state.userInfo?.id ?? null
  },

  actions: {
    setSession({ token, user }) {
      this.token = token
      this.userInfo = user
      localStorage.setItem('token', token)
      localStorage.setItem('userInfo', JSON.stringify(user))
    },

    async login(payload) {
      const res = await userApi.login(payload)
      this.setSession(res.data)
      return res
    },

    async register(payload) {
      const res = await userApi.register(payload)
      this.setSession(res.data)
      return res
    },

    // 刷新用户信息（打开站点时校验 token 是否仍有效）
    async fetchMe() {
      const res = await userApi.getMe()
      this.userInfo = res.data
      localStorage.setItem('userInfo', JSON.stringify(res.data))
      return res.data
    },

    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    }
  }
})

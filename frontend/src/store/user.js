import { defineStore } from 'pinia'
import * as userApi from '@/api/user'
import { getUserInfo, getToken, saveSession, setUserInfo, clearSession } from '@/utils/storage'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    userInfo: getUserInfo()
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
      saveSession({ token, user })
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
      setUserInfo(res.data)
      return res.data
    },

    logout() {
      this.token = ''
      this.userInfo = null
      clearSession()
    }
  }
})

import { defineStore } from 'pinia'
import * as userApi from '@/api/user'
import { getUserInfo, getToken, saveSession, setToken, setUserInfo, clearSession } from '@/utils/storage'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    userInfo: getUserInfo()
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.username || '',
    avatar: (state) => state.userInfo?.avatar || '',
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

    // 邮箱验证码注册：外部身份中心是权威来源，后端验证成功后会同时建本地镜像
    async registerWithEmailCode(payload) {
      const res = await userApi.registerWithEmailCode(payload)
      this.setSession(res.data)
      return res
    },

    // 邮箱验证码登录
    async loginWithEmailCode(payload) {
      const res = await userApi.loginWithEmailCode(payload)
      this.setSession(res.data)
      return res
    },

    sendEmailCode(payload) {
      return userApi.sendEmailCode(payload)
    },

    resetPasswordWithEmailCode(payload) {
      return userApi.resetPasswordWithEmailCode(payload)
    },

    // 刷新用户信息（打开站点时校验 token 是否仍有效）
    async fetchMe() {
      const res = await userApi.getMe()
      this.userInfo = res.data
      setUserInfo(res.data)
      return res.data
    },

    // 只换令牌、不动用户信息。改密成功后服务端会作废旧令牌并换发新的，
    // 必须立刻落回本地 —— 否则当前标签页的下一次请求就会 401，用户会被自己刚做的改动踢下线
    updateToken(token) {
      this.token = token
      setToken(token)
    },

    logout() {
      this.token = ''
      this.userInfo = null
      clearSession()
    }
  }
})

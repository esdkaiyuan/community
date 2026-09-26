// 本地存储统一封装：键名集中管理，杜绝各处裸读 localStorage
const KEYS = {
  token: 'token',
  userInfo: 'userInfo',
  userFlagPrefix: 'userflag:' // 格式 userflag:<like|join>:<userId>:<projectId>
}

export const getToken = () => localStorage.getItem(KEYS.token) || ''

export const setToken = (token) => localStorage.setItem(KEYS.token, token)

export const getUserInfo = () => {
  try {
    return JSON.parse(localStorage.getItem(KEYS.userInfo)) || null
  } catch {
    return null
  }
}

export const setUserInfo = (user) => localStorage.setItem(KEYS.userInfo, JSON.stringify(user))

// 登录态整体写入 / 清除
export const saveSession = ({ token, user }) => {
  setToken(token)
  setUserInfo(user)
}

export const clearSession = () => {
  localStorage.removeItem(KEYS.token)
  localStorage.removeItem(KEYS.userInfo)
}

/**
 * 按用户+项目维度的本地行为标记（点赞/参与），
 * 仅作辅助记忆，真实状态以服务端为准
 */
export const getUserFlag = (kind, userId, projectId) =>
  localStorage.getItem(`${KEYS.userFlagPrefix}${kind}:${userId}:${projectId}`) === '1'

export const setUserFlag = (kind, userId, projectId, value) => {
  const key = `${KEYS.userFlagPrefix}${kind}:${userId}:${projectId}`
  if (value) localStorage.setItem(key, '1')
  else localStorage.removeItem(key)
}

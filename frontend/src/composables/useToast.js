import { reactive } from 'vue'

let seed = 0

export const toasts = reactive([])

// 停留时长按类型分级：错误要读完（而且用户往往正想重试），成功一眼扫过就够
const DURATION = { error: 4500, info: 3200, success: 2600 }

// id -> { handle, remaining, startedAt }
const timers = new Map()

const clearTimer = (id) => {
  const t = timers.get(id)
  if (t?.handle) clearTimeout(t.handle)
  timers.delete(id)
}

const remove = (id) => {
  clearTimer(id)
  const index = toasts.findIndex((t) => t.id === id)
  if (index > -1) toasts.splice(index, 1)
}

const schedule = (id, ms) => {
  timers.set(id, { handle: setTimeout(() => remove(id), ms), remaining: ms, startedAt: Date.now() })
}

/**
 * 全局轻提示
 *
 * 同类型 + 同文案会**复用已有卡片并重置倒计时**，而不是再叠一张：
 * 登录态失效时页面常并发发出 4~5 个请求，全部 401 会瞬间刷出一排一模一样的提示。
 *
 * @param {string} message 文案
 * @param {'success'|'error'|'info'} type 类型
 * @returns {number} 提示 id（可用于提前 dismiss）
 */
export function toast(message, type = 'success') {
  const duration = DURATION[type] || DURATION.info

  const existing = toasts.find((t) => t.message === message && t.type === type)
  if (existing) {
    clearTimer(existing.id)
    schedule(existing.id, duration)
    return existing.id
  }

  const id = ++seed
  toasts.push({ id, message, type })
  schedule(id, duration)
  return id
}

/** 立即关闭某条提示（右上角的 ✕ 按钮） */
export function dismiss(id) {
  remove(id)
}

/** 鼠标停在提示上：暂停倒计时（错误文案长，用户常常还在读） */
export function pause(id) {
  const t = timers.get(id)
  if (!t || !t.handle) return
  clearTimeout(t.handle)
  t.remaining = Math.max(500, t.remaining - (Date.now() - t.startedAt))
  t.handle = null
}

/** 移开鼠标：用剩余时间继续倒计时，而不是重新计时 */
export function resume(id) {
  const t = timers.get(id)
  if (!t || t.handle) return
  schedule(id, t.remaining)
}

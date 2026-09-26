import { reactive } from 'vue'

let seed = 0

export const toasts = reactive([])

/**
 * 全局轻提示
 * @param {string} message 文案
 * @param {'success'|'error'|'info'} type 类型
 */
export function toast(message, type = 'success') {
  const id = ++seed
  toasts.push({ id, message, type })
  setTimeout(() => {
    const index = toasts.findIndex((t) => t.id === id)
    if (index > -1) toasts.splice(index, 1)
  }, 2800)
}

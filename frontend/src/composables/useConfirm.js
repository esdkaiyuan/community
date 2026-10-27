import { reactive } from 'vue'

/**
 * 全局确认对话框（替代 window.confirm）
 *
 * 为什么不用原生 confirm：它长着浏览器的脸，深浅色主题、字体、圆角全都不受控，
 * 在任何一处设计系统里都是一个突兀的异物；而且在 Playwright 里它属于原生对话框，
 * 默认会被自动 dismiss，端到端脚本根本测不到「点了删除会发生什么」。
 *
 * 用法（与 window.confirm 同形，await 出布尔值）：
 *   if (!(await confirm({ title: '删除项目？', message: '…', destructive: true }))) return
 *
 * 生命周期：状态是模块级单例，对话框由 AppConfirmHost 渲染（挂在 App.vue），
 * 页面上任意位置调用都能弹出来。
 */
const state = reactive({
  open: false,
  title: '',
  message: '',
  confirmLabel: '确认',
  cancelLabel: '取消',
  destructive: false,
  resolver: null
})

export function confirm(options = {}) {
  const {
    title = '',
    message = '',
    confirmLabel = '确认',
    cancelLabel = '取消',
    destructive = false
  } = options

  // 上一个还没关闭就又来一个：先把旧的按「取消」结掉，
  // 否则旧 promise 永远悬着，调用方的 await 卡死
  if (state.resolver) state.resolver(false)

  Object.assign(state, { open: true, title, message, confirmLabel, cancelLabel, destructive })

  return new Promise((resolve) => {
    state.resolver = resolve
  })
}

/** 供 AppConfirmHost 调用：结掉当前对话框 */
export function settleConfirm(value) {
  state.open = false
  const resolve = state.resolver
  state.resolver = null
  resolve?.(Boolean(value))
}

export function useConfirmState() {
  return state
}

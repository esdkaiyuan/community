import { onBeforeUnmount, ref } from 'vue'

/**
 * 收藏成功的一次性微动效（书签图标上挑回弹 + 中性光晕扩散）
 * 动画本体是全局 CSS（style.css 里的 .fav-pop），组件只负责在正确时机挂/摘类。
 *
 * @returns {{ favoritePulse: import('vue').Ref<boolean>, playFavoritePulse: () => void }}
 */
export function useFavoritePulse() {
  const favoritePulse = ref(false)
  let timer = null

  const playFavoritePulse = () => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    favoritePulse.value = false
    // 先落回基线再触发，保证连续操作也能重播动画
    requestAnimationFrame(() => {
      favoritePulse.value = true
      clearTimeout(timer)
      timer = setTimeout(() => (favoritePulse.value = false), 560)
    })
  }

  onBeforeUnmount(() => clearTimeout(timer))

  return { favoritePulse, playFavoritePulse }
}

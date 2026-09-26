// v-reveal — 苹果官网式滚动渐入
// 用法: v-reveal 或 v-reveal="延迟毫秒数"（用于列表交错入场）
// 元素进入视口时淡入并上浮，一次性触发后停止观察
let observer = null

if (typeof IntersectionObserver !== 'undefined') {
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-in')
          observer.unobserve(entry.target)
        }
      }
    },
    { threshold: 0.1, rootMargin: '0px 0px -32px 0px' }
  )
}

export default {
  mounted(el, binding) {
    // 无 IntersectionObserver（极老浏览器）时直接显示，保证功能不受影响
    if (!observer) return
    el.classList.add('reveal-init')
    const delay = Number(binding.value) || 0
    if (delay) el.style.transitionDelay = `${delay}ms`
    observer.observe(el)
  },
  unmounted(el) {
    if (observer) observer.unobserve(el)
  }
}

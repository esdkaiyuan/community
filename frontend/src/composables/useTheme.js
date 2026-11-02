import { computed, ref, watch } from 'vue'

// 全站外观状态：明暗模式（跟随系统 / 浅色 / 深色）+ 强调色（四套）。
// 模块级单例：页头、外观设置页、预览块共用同一份状态，切一处全站立即生效。
//
// 明暗的真正开关是 <html data-theme="light|dark">，强调色是 <html data-accent>。
// 「跟随系统」不写死结果，而是监听 matchMedia，系统换了外观页面即时跟着换。
// index.html 里有一段同样逻辑的内联脚本，在首屏绘制前先落一次属性，避免闪白/闪黑。

export const THEME_MODE_KEY = 'community-theme-mode'
export const THEME_ACCENT_KEY = 'community-theme-accent'

export const THEME_MODES = [
  { value: 'system', label: '跟随系统', icon: 'monitor', hint: '随系统浅色 / 深色自动切换' },
  { value: 'light', label: '浅色', icon: 'sun', hint: '始终使用暖纸面浅色' },
  { value: 'dark', label: '深色', icon: 'moon', hint: '始终使用深色工程纸' }
]

// color / dark 是设置页色块用的展示色（浅色 / 深色下各取一档），不是运行时取色来源；
// 运行时取色永远走 style.css 的 --c-pine 四件套。
export const THEME_ACCENTS = [
  { value: 'pine', label: '电光青', color: '#0B7285', dark: '#5BE0EB', hint: '默认 · 原站配色' },
  { value: 'azure', label: '静谧蓝', color: '#0A5BB5', dark: '#6CB6FF', hint: '偏冷、克制' },
  { value: 'moss', label: '苔原绿', color: '#0E7A4B', dark: '#4CD99A', hint: '自然、生长感' },
  { value: 'iris', label: '鸢尾紫', color: '#6B3FB8', dark: '#C4A6FF', hint: '偏创作、灵感' }
]

const MODE_VALUES = THEME_MODES.map((m) => m.value)
const ACCENT_VALUES = THEME_ACCENTS.map((a) => a.value)

function readStorage(key, allowed, fallback) {
  try {
    const value = localStorage.getItem(key)
    return allowed.includes(value) ? value : fallback
  } catch {
    // 隐私模式 / 禁用存储时 localStorage 会抛错，外观退回默认值即可，不该阻塞页面
    return fallback
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // 忽略：这次选择只在当前页面生效
  }
}

const media = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(prefers-color-scheme: dark)')
  : null
const systemDark = ref(Boolean(media && media.matches))

const mode = ref(readStorage(THEME_MODE_KEY, MODE_VALUES, 'system'))
const accent = ref(readStorage(THEME_ACCENT_KEY, ACCENT_VALUES, 'pine'))

const resolved = computed(() => {
  if (mode.value === 'light' || mode.value === 'dark') return mode.value
  return systemDark.value ? 'dark' : 'light'
})

const resolvedLabel = computed(() => (resolved.value === 'dark' ? '深色' : '浅色'))
const modeLabel = computed(() => {
  const current = THEME_MODES.find((m) => m.value === mode.value)
  return mode.value === 'system' ? `${resolvedLabel.value}（跟随系统）` : current.label
})
const accentOption = computed(() => THEME_ACCENTS.find((a) => a.value === accent.value) || THEME_ACCENTS[0])

function applyTheme() {
  const root = document.documentElement
  root.dataset.theme = resolved.value
  root.dataset.accent = accent.value

  // 移动端地址栏 / 状态栏取色：只有纸面底色，不跟着强调色走
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', resolved.value === 'dark' ? '#000000' : '#F4F1E9')
}

function setMode(value) {
  if (!MODE_VALUES.includes(value) || value === mode.value) return
  mode.value = value
  writeStorage(THEME_MODE_KEY, value)
}

function setAccent(value) {
  if (!ACCENT_VALUES.includes(value) || value === accent.value) return
  accent.value = value
  writeStorage(THEME_ACCENT_KEY, value)
}

function resetTheme() {
  setMode('system')
  setAccent('pine')
}

if (media) {
  media.addEventListener('change', (event) => {
    systemDark.value = event.matches
  })
}

watch([resolved, accent], applyTheme, { immediate: true })

export function useTheme() {
  return {
    mode,
    accent,
    resolved,
    resolvedLabel,
    modeLabel,
    accentOption,
    setMode,
    setAccent,
    resetTheme
  }
}

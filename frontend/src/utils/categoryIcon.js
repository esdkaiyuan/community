// 数据库 categories.icon 存的是 Element Plus 图标名（历史遗留），映射为 emoji 展示
const ICON_MAP = {
  Monitor: '💻',
  Brush: '🎨',
  ShoppingBag: '📈',
  VideoCamera: '🎬',
  Cpu: '🔌',
  Reading: '📚',
  Share: '🌐',
  Handbag: '💚'
}

export const categoryIcon = (icon) => ICON_MAP[icon] || '🌱'

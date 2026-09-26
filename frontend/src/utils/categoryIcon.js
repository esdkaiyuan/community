// 数据库 categories.icon 存的是 Element Plus 图标名（历史遗留），映射为 AppIcon 矢量图标名
const ICON_MAP = {
  Monitor: 'monitor',
  Brush: 'palette',
  ShoppingBag: 'trending-up',
  VideoCamera: 'film',
  Cpu: 'cpu',
  Reading: 'book-open',
  Share: 'globe',
  Handbag: 'heart'
}

export const categoryIcon = (icon) => ICON_MAP[icon] || 'sprout'

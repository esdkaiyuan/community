// 无封面时的占位配色：暖纸 + 墨色 + 电光青的低饱和组合，按 id 取一组稳定配色
// （卡片封面与相关推荐封面共用，改这里两边一起生效）
const PALETTES = [
  { bg: 'linear-gradient(135deg, #EFEBE2 0%, #DED7C7 100%)', fg: '#545A63' },
  { bg: 'linear-gradient(135deg, #E4F6F8 0%, #BFE7EC 100%)', fg: '#0B7285' },
  { bg: 'linear-gradient(135deg, #FDF0E0 0%, #F3D8B2 100%)', fg: '#AF5E00' },
  { bg: 'linear-gradient(135deg, #FBE9EA 0%, #F5D0D3 100%)', fg: '#C41E2A' },
  { bg: 'linear-gradient(135deg, #EDECE8 0%, #DAD6CB 100%)', fg: '#3A3F47' },
  { bg: 'linear-gradient(135deg, #E9F4EF 0%, #CBE6D9 100%)', fg: '#0F6B4F' }
]

export const coverPalette = (id) => PALETTES[(Number(id) || 0) % PALETTES.length]

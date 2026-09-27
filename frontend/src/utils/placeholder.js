// 无封面时的占位配色：Apple 中性色系，按 id 取一组稳定配色
// （卡片封面与相关推荐封面共用，改这里两边一起生效）
const PALETTES = [
  { bg: 'linear-gradient(135deg, #E8E8ED 0%, #D2D2D7 100%)', fg: '#6E6E73' },
  { bg: 'linear-gradient(135deg, #E8F1FD 0%, #C5DFFF 100%)', fg: '#0066CC' },
  { bg: 'linear-gradient(135deg, #FDF0E4 0%, #FFDDB8 100%)', fg: '#C93400' },
  { bg: 'linear-gradient(135deg, #FCE8E9 0%, #FFD1D4 100%)', fg: '#D70015' },
  { bg: 'linear-gradient(135deg, #F0F0F3 0%, #D8DAE5 100%)', fg: '#3A3A3C' },
  { bg: 'linear-gradient(135deg, #E8F5F4 0%, #C2E8E5 100%)', fg: '#00796B' }
]

export const coverPalette = (id) => PALETTES[(Number(id) || 0) % PALETTES.length]

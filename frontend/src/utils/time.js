// 相对时间：刚刚 / N 分钟前 / N 小时前 / N 天前 / 具体日期
export const relativeTime = (str) => {
  if (!str) return ''
  const diff = Date.now() - new Date(str).getTime()
  const min = 60_000
  if (diff < min) return '刚刚'
  if (diff < 60 * min) return `${Math.floor(diff / min)} 分钟前`
  if (diff < 24 * 60 * min) return `${Math.floor(diff / (60 * min))} 小时前`
  if (diff < 30 * 24 * 60 * min) return `${Math.floor(diff / (24 * 60 * min))} 天前`
  const d = new Date(str)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
}

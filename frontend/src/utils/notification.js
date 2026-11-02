// 通知类型 -> 动作文案。界面按「{actor} {动作}「{项目标题}」」拼接，此处只给动作部分。
// system（平台公告）没有 actor / project，文案由调用方单独渲染，这里留空。
const TEXT_MAP = {
  comment: '评论了你的项目',
  reply: '回复了你在',
  like: '赞了你在',
  participate: '参与了你的项目',
  mention: '在评论中提及了你',
  system: ''
}

export const notificationText = (type) => TEXT_MAP[type] || '与你互动于'

// 平台公告是站内广播：点进去就留在通知页（那里本来就是它的完整正文），
// 不做原地跳转，避免「点一下又回到同一页」的空动作。
export const notificationTarget = (n) => {
  if (n.type === 'system' || !n.project?.id) return { path: '/notifications' }
  const path = `/project/${n.project.id}`
  if (n.type === 'participate') return { path }
  if (n.commentId) return { path, query: { comment: n.commentId } }
  return { path, hash: '#comments' }
}

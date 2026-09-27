// 通知类型 -> 动作文案。界面按「{actor} {动作}「{项目标题}」」拼接，此处只给动作部分
const TEXT_MAP = {
  comment: '评论了你的项目',
  reply: '回复了你在',
  like: '赞了你在',
  participate: '参与了你的项目'
}

export const notificationText = (type) => TEXT_MAP[type] || '与你互动于'

// 参与类通知落到项目详情页；评论 / 回复 / 点赞是围绕讨论的，落到评论区锚点
export const notificationTarget = (n) => {
  const path = `/project/${n.project?.id}`
  return n.type === 'participate' ? { path } : { path, hash: '#comments' }
}

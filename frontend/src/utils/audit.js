// 审计类界面的词表（操作日志 + 安全事件），供 /security 页消费。
//
// 枚举值由**后端白名单**定义，映射表必须与后端逐字一致：
//   操作日志 → backend/src/services/activityLog.service.js 的 ACTIONS
//   安全事件 → backend/src/services/securityEvent.service.js 的 EVENTS
//
// ⚠️ 值写错**不会报错**，只会静默落到兜底文案（「异常尝试」/ 默认图标），于是整类
// 事件显示错都不会有人发现。所以约定两条，并让 verify_security_page.py 断言它们：
//   1. 兜底文案必须存在且在语义上说得通 —— 后端将来加类型时页面不炸、也不说谎；
//   2. 筛选 chip 只列「真能筛出结果」的键 —— 不放永远筛出空列表的假入口（见下方 EVENT_FILTERS）。

// ============ 操作日志 ============

// 行首图标。名字必须与 AppIcon 的 ICONS 表对得上：写错会静默回退成 sprout，
// 页面不报错、只是每行都长成同一棵小苗 —— 所以这套名字要和图标表一起改。
export const ACTION_ICONS = {
  'project.create': 'lightbulb',
  'project.update': 'pencil',
  'project.delete': 'trash-2',
  'comment.create': 'message-circle',
  'comment.delete': 'trash-2',
  'user.register': 'user',
  'user.profile.update': 'user',
  'user.password.update': 'lock'
}

export const actionIcon = (action) => ACTION_ICONS[action] || 'info'

// 筛选 chip。value 直接就是接口参数（不用再做一层 code → 参数映射）。
//
// 列表行**刻意不显示动作名**：后端的 summary 本来就以动词开头（「发布项目「X」」
// 「评论了项目「X」：…」），再摆一个「发布项目」的 chip 等于在同一行里说两遍。
// 所以动作名只在这里出现，列表行靠图标 + 句子表达。
//
// 选项不覆盖全部 ACTIONS：删除类操作没有独立入口（列表里也极少出现），
// 但它们仍然会正常渲染（图标 + summary），只是不能单独筛。
export const ACTION_FILTERS = [
  { value: '', label: '全部' },
  { value: 'project.create', label: '发布' },
  { value: 'project.update', label: '编辑' },
  { value: 'comment.create', label: '评论' },
  { value: 'user.profile.update', label: '资料' }
]

// ============ 安全事件 ============

export const EVENT_LABELS = {
  'auth.login.rejected': '登录尝试',
  'auth.register.rejected': '注册尝试',
  'auth.token.rejected': '令牌校验',
  'auth.password.rejected': '改密尝试'
}

// 一句话解释「这类事件意味着什么」。写给非技术用户看：不要出现 token / JWT / 签名 这类词。
export const EVENT_HINTS = {
  'auth.login.rejected': '有人用你的邮箱尝试登录，但密码不对',
  'auth.register.rejected': '有人想用你的用户名或邮箱注册新账号',
  'auth.token.rejected': '有人带着伪造或篡改过的登录凭证访问了接口',
  'auth.password.rejected': '有人在已登录的状态下试图修改你的登录密码，但当前密码不对'
}

export const eventLabel = (event) => EVENT_LABELS[event] || '异常尝试'
export const eventHint = (event) => EVENT_HINTS[event] || '一次没有成功的异常访问'

// 筛选 chip：**只列「能落到我头上」的事件类型**。
//
// 这里有个反直觉但重要的事实：`auth.token.rejected`（伪造 / 篡改令牌）会入库，
// 却**永远不会出现在这一页**。因为 auth 中间件在签名验不过时拿不到可信身份，
// 写事件时 target_user_id 是 NULL —— 而 listMine 按 `target_user_id = 我` 过滤，
// 永远查不到它。也就是说「令牌被拒」是**全站性质**的探测，不对应任何具体账号，
// 只对运维有意义。给它放一个筛选项 = 一个永远筛出空列表的假入口，所以不放。
// （标签仍保留在 EVENT_LABELS 里：将来后端若能归属到具体账号，列表会照常渲染。）
//
// 能出现在这一页的有三类，各自的可归属性来自：
//   登录尝试 → 邮箱存在，user.id 已知
//   注册尝试 → 撞上了已存在的用户名 / 邮箱，existing.id 已知
//   改密尝试 → 发生在已登录会话里，被瞄准的就是当前这个账号
export const EVENT_FILTERS = [
  { value: '', label: '全部' },
  { value: 'auth.login.rejected', label: '登录' },
  { value: 'auth.register.rejected', label: '注册' },
  { value: 'auth.password.rejected', label: '改密' }
]

// 只接受词表里出现过的筛选值。URL 上的 query 是用户可控的（也可能是手改的 / 旧的），
// 直接透传给接口会拿到 400 —— 页面变成「空列表 + 一条报错」，看着像功能坏了。
// 认不出来就退回「全部」，这才是筛选参数该有的容错。
export const pickFilter = (value, options) =>
  typeof value === 'string' && options.some((o) => o.value === value) ? value : ''

// 操作日志服务：唯一的写入入口，也是唯一允许决定「日志里能出现什么键」的地方。
//
// 三条约束，全部在这里强制：
//   1. **动作白名单**：只认 ACTIONS 里的取值。写错一个字符串不会静默入库
//      （否则等有人查日志才会发现「某类操作一条都没有」）。
//   2. **detail 键白名单**：每个动作允许哪些键在这里写死，且 sanitizeDetail 是
//      「按白名单取」而不是「按传入对象遍历」—— 任意键（含 `__proto__`）天然进不来。
//   3. **异常不外抛**：日志写失败绝不能把用户的发布/评论带崩。这里吞掉异常，
//      但必须打 error 日志留痕 —— 静默失败等于审计缺口。
const { ActivityLog, User } = require('../models')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const ApiError = require('../utils/ApiError')
const createLogger = require('../utils/logger')
const { sanitizeLogText, sanitizeDetail, sanitizeIp, sanitizeUserAgent } = require('../utils/logSanitize')

const log = createLogger('activity')

const ACTIONS = Object.freeze({
  PROJECT_CREATE: 'project.create',
  PROJECT_UPDATE: 'project.update',
  PROJECT_DELETE: 'project.delete',
  COMMENT_CREATE: 'comment.create',
  COMMENT_DELETE: 'comment.delete',
  USER_REGISTER: 'user.register',
  USER_PROFILE_UPDATE: 'user.profile.update'
})
const ACTION_VALUES = Object.freeze(Object.values(ACTIONS))

// 有意**不记**的动作，以及理由（免得后来者以为是漏了）：
//   - 点赞 / 取消点赞、收藏 / 取消收藏、参与 / 退出：高频、可反复切换、且不产生内容。
//     记进来只会让日志被噪音淹没（刷一次首页就能造出几十行），真正的取证价值接近零。
//   - 通知已读：既非内容也非状态变更，只是读游标。
// 如果哪天要做「异常行为检测」，正确的做法是单独一张行为流水表 + 聚合，而不是往审计
// 日志里灌明细 —— 审计日志要「每条都值得人读一遍」。
const TARGET_TYPES = Object.freeze(['project', 'comment', 'user'])

// 每个动作允许出现在 detail 里的键（未列出的键一律丢弃）
const DETAIL_KEYS = Object.freeze({
  [ACTIONS.PROJECT_CREATE]: ['title', 'categoryId', 'tags'],
  [ACTIONS.PROJECT_UPDATE]: ['title', 'changed'],
  [ACTIONS.PROJECT_DELETE]: ['title'],
  [ACTIONS.COMMENT_CREATE]: ['projectTitle', 'preview', 'isReply'],
  [ACTIONS.COMMENT_DELETE]: ['projectTitle', 'preview'],
  [ACTIONS.USER_REGISTER]: ['username'],
  [ACTIONS.USER_PROFILE_UPDATE]: ['changed', 'usernameFrom', 'usernameTo']
})

const SUMMARY_MAX = 255
const USERNAME_MAX = 50
const PREVIEW_LEN = 60

// 摘要里只放「短预览」，不整段抄正文：日志是留痕，不是内容备份。
// 既可读，也让单行摘要天然不会过长。
//
// ⚠️ detail 里的预览**必须走同一个 preview()**，不要直接塞原文：
// 直接塞会被 sanitizeDetail 的通用上限（120 字）接住，于是「摘要里 60 字、
// detail 里 120 字」同一份内容两个口径 —— 实测就是这样被验证脚本抓到的。
// 统一口径后，一条日志里任何用户内容最多只留 60 字。
const preview = (text) => sanitizeLogText(text, PREVIEW_LEN)

// 只接受正整数 ID，其余（字符串注入、负数、NaN、超长）一律归为 null
const toId = (value) => {
  const n = Number(value)
  return Number.isInteger(n) && n > 0 ? n : null
}

const resolveTargetType = (value) => {
  const text = sanitizeLogText(value, 20)
  return TARGET_TYPES.includes(text) ? text : 'unknown'
}

// username 快照：调用方没带就回查一次。日志写入频率很低（发布/编辑/评论），
// 一次主键查询换来「用户改名或注销后日志仍可追溯」，很划算。
//
// 🔥 **回查出来的值同样要过净化** —— 这里曾经是整条净化链的旁路：其余 8 个可写列
// 都过了 sanitize*，唯独 username 是「从库里读出来直接落库」。而 username 恰好是
// 唯一由用户直接控制的身份字段，实测注册 `"a\r\nFAKE"` 能通过（只看长度 2~20），
// 于是 activity_logs.username 里真的躺进了 CRLF（HEX 610D0A46414B45）—— 下游按行
// 解析的日志系统会凭空多出一条伪造记录。**日志列的完整性不能依赖「上游字段干净」**，
// 所以两条路径（调用方自带 / 这里回查）统一走 sanitizeLogText。
const resolveUsername = async (userId) => {
  if (!userId) return null
  const user = await User.findByPk(userId, { attributes: ['username'] })
  return user ? sanitizeLogText(user.username, USERNAME_MAX) || null : null
}

/**
 * 落一条操作日志。**永不抛异常**。
 *
 * @returns {Promise<ActivityLog|null>} 失败或被拒时返回 null
 */
const record = async ({ action, targetType, targetId, projectId, userId, username, summary, detail, req }) => {
  try {
    if (!ACTION_VALUES.includes(action)) {
      log.warn(`拒绝写入未知动作的操作日志: ${sanitizeLogText(action, 32) || '(空)'}`)
      return null
    }

    const actorId = toId(userId)
    const actorName = username ? sanitizeLogText(username, USERNAME_MAX) : await resolveUsername(actorId)

    return await ActivityLog.create({
      user_id: actorId,
      username: actorName || null,
      action,
      target_type: resolveTargetType(targetType),
      target_id: toId(targetId),
      project_id: toId(projectId),
      // 摘要兜底文案：净化后为空说明原文全是控制字符/emoji，不能写空串（列 NOT NULL）
      summary: sanitizeLogText(summary, SUMMARY_MAX) || '(无摘要)',
      detail: sanitizeDetail(detail, DETAIL_KEYS[action] || []),
      // req 是可选的：定时任务、脚本等非 HTTP 场景传 undefined，这两个字段就留空
      ip: sanitizeIp(req && req.ip),
      user_agent: sanitizeUserAgent(req && req.headers && req.headers['user-agent'])
    })
  } catch (error) {
    log.error('写入操作日志失败:', error.message)
    return null
  }
}

// ---- 对外只暴露「意图命名」的方法，调用方不必知道 action 字符串与摘要格式 ----

exports.logProjectCreated = ({ creatorId, project, req }) =>
  record({
    action: ACTIONS.PROJECT_CREATE,
    targetType: 'project',
    targetId: project.id,
    projectId: project.id,
    userId: creatorId,
    summary: `发布项目「${preview(project.title)}」`,
    detail: { title: project.title, categoryId: project.category_id, tags: project.tags },
    req
  })

exports.logProjectUpdated = ({ userId, project, changedFields = [], req }) =>
  record({
    action: ACTIONS.PROJECT_UPDATE,
    targetType: 'project',
    targetId: project.id,
    projectId: project.id,
    userId,
    summary: `编辑项目「${preview(project.title)}」（改动了 ${changedFields.join('、') || '无'}）`,
    detail: { title: project.title, changed: changedFields },
    req
  })

exports.logProjectDeleted = ({ userId, project, req }) =>
  record({
    action: ACTIONS.PROJECT_DELETE,
    targetType: 'project',
    targetId: project.id,
    projectId: project.id,
    userId,
    summary: `删除项目「${preview(project.title)}」`,
    detail: { title: project.title },
    req
  })

exports.logCommentCreated = ({ userId, comment, project, isReply = false, req }) =>
  record({
    action: ACTIONS.COMMENT_CREATE,
    targetType: 'comment',
    targetId: comment.id,
    projectId: project.id,
    userId,
    summary: `${isReply ? '回复' : '评论'}了项目「${preview(project.title)}」：${preview(comment.content)}`,
    detail: { projectTitle: project.title, preview: preview(comment.content), isReply },
    req
  })

exports.logCommentDeleted = ({ userId, comment, project, req }) =>
  record({
    action: ACTIONS.COMMENT_DELETE,
    targetType: 'comment',
    targetId: comment.id,
    projectId: project.id,
    userId,
    summary: `删除评论（项目「${preview(project.title)}」）：${preview(comment.content)}`,
    detail: { projectTitle: project.title, preview: preview(comment.content) },
    req
  })

// 注册是审计的「第一行」：后面所有日志靠 user_id 串成一条时间线，起点就是它。
// 刻意**不记 email**：审计只需 user_id 就能把同一个人的行为串起来，而日志留存 365 天，
// 多存一份邮箱等于平白扩大 PII 面。要联系人，users 表里有。
exports.logUserRegistered = ({ userId, user, req }) =>
  record({
    action: ACTIONS.USER_REGISTER,
    targetType: 'user',
    targetId: userId,
    userId,
    summary: `注册账号「${preview(user.username)}」`,
    detail: { username: user.username },
    req
  })

exports.logUserProfileUpdated = ({ userId, changedFields = [], usernameFrom, usernameTo, req }) =>
  record({
    action: ACTIONS.USER_PROFILE_UPDATE,
    targetType: 'user',
    targetId: userId,
    userId,
    summary:
      `更新个人资料（改动了 ${changedFields.join('、') || '无'}）` +
      // 改名单独拎出来说——它是这一行日志存在的核心理由
      (usernameFrom ? `：用户名「${preview(usernameFrom)}」→「${preview(usernameTo)}」` : ''),
    // 🔥 用户名是**唯一被日志自己快照的字段**（activity_logs.username）。改了它，此前所有
    // 日志行里记的都还是旧名字；没有 from → to，事后就再也解释不清「同一个 user_id 为什么
    // 有两个名字」。bio / avatar 只记「改没改」，不存值：日志是留痕不是内容备份。
    detail: { changed: changedFields, usernameFrom, usernameTo },
    req
  })

// ---- 读取：只允许查自己的日志 ----

const toClientLog = (row) => ({
  id: row.id,
  action: row.action,
  targetType: row.target_type,
  targetId: row.target_id,
  projectId: row.project_id,
  summary: row.summary,
  detail: row.detail || null,
  ip: row.ip,
  userAgent: row.user_agent,
  createdAt: row.created_at
})

exports.listMine = async ({ userId, page = 1, pageSize = 20, action, projectId }) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 20 })

  const where = { user_id: userId }

  if (action !== undefined && action !== null && action !== '') {
    // 无效筛选值直接报错，而不是静默忽略 —— 否则调用方会拿到一份「以为筛过了」的
    // 完整列表，比报错更难发现
    if (!ACTION_VALUES.includes(action)) throw ApiError.badRequest('不支持的操作类型')
    where.action = action
  }
  const pid = toId(projectId)
  if (pid) where.project_id = pid

  const { count, rows } = await ActivityLog.findAndCountAll({
    where,
    // 同秒多条时顺序必须稳定，否则翻页会串行
    order: [
      ['created_at', 'DESC'],
      ['id', 'DESC']
    ],
    limit,
    offset: (page - 1) * limit
  })

  return { logs: rows.map(toClientLog), total: count, page, pageSize: limit }
}

exports.ACTIONS = ACTIONS
exports.ACTION_VALUES = ACTION_VALUES
exports.DETAIL_KEYS = DETAIL_KEYS
exports.record = record

const bcrypt = require('bcryptjs')
const { Op } = require('sequelize')
const { User, Comment, Project, ProjectParticipant, ProjectFavorite, sequelize } = require('../models')
const { generateToken } = require('../utils/jwt')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const { stripEmoji, stripControlChars } = require('../utils/textSanitize')
const ApiError = require('../utils/ApiError')
const activityLogService = require('./activityLog.service')
const securityEventService = require('./securityEvent.service')

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// 资料字段上界。bio 与前端 textarea 的 maxlength 对齐（200 字符）；
// avatar 没有前端 maxlength —— 那是**有意**的：给 URL 输入框加 maxlength 会把
// 粘贴进来的长链接静默截断，变成一条坏链接，还不如让服务端明确报错。
// 这里的 255 是 users.avatar 列（VARCHAR(255)）的容量，属于「DB 存不下就必须拦」的那类校验。
const BIO_MAX_LENGTH = 200
const AVATAR_MAX_LENGTH = 255

// ---- 身份字段归一化：注册与改名**必须共用同一个函数**（与项目标签的 normalizeTags 同一约定）----
//
// 此前 register 与 updateProfile 各写一套：register 完全不 trim，updateProfile 会 trim。
// 于是 `"  ab  "` 走 API 注册能带着首尾空格入库，而同一个值走改名会被去掉 —— 一个字段
// 两套口径，迟早对不上。
//
// 🔥 为什么这里必须比「长度校验」做得多：username 是**唯一**既由用户直接控制、又会被
// 写进审计日志列（activity_logs.username）的身份字段。实测注册 `"a\r\nFAKE"`（长度 7，
// 落在 2~20 之内）能通过，日志行里就真的带上了 0D0A —— 下游按行解析的日志系统会凭空
// 多出一条伪造记录。所以用户名必须是**单行、无控制字符、无零宽与方向控制**的。
//
// 为什么连 emoji 也剥：本仓库的既定约定是「全站禁用 emoji，用户输入侧一律剥除」
// （评论 / 标题 / 简介 / 标签都剥了），用户名是当初漏掉的一处。不剥还有两个具体后果：
// 头像首字母取 `.slice(0, 1)`，emoji 开头的用户名会切出半个代理对、渲染成 `�`；
// 而日志的 username 快照本来就会剥 emoji，于是快照与真实用户名对不上，没法按名字查日志。
//
// 控制字符与零宽字符的正则**不在这里写**，走 utils/textSanitize.stripControlChars：
// 那类正则天然会触发 eslint 的 no-control-regex（规则方向在这里是反的），集中在
// textSanitize / logSanitize 两个模块里豁免并写明理由，比每个调用方各挂一次豁免清楚得多。
const SPACE_RE = /[ \t\u00A0\u3000]+/g

// 用户名：剥 emoji → 去控制字符（含 \r \n \t）、零宽与方向控制 → 折叠空白 → 收边。
// 控制字符是**删除**而不是替换成空格：用户名是标识不是文本，`a\r\nFAKE` 收敛成 `aFAKE`
// 比 `a FAKE` 更贴近「有人粘贴时夹带了不可见字符」这个事实。
// `adjusted`：净化确实改动了内容（供接口在响应里说明，不做静默修改）。
const normalizeUsername = (raw) => {
  const original = String(raw ?? '')
  const value = stripControlChars(stripEmoji(original))
    .replace(SPACE_RE, ' ')
    .trim()
  if (value.length < 2 || value.length > 20) throw ApiError.badRequest('用户名需 2-20 个字符')
  return { value, adjusted: value !== original.trim() }
}

// 简介：多行文本，所以**保留换行**（前端是 textarea，正文本来就可能分段），
// 只统一 CRLF、去掉其余控制字符与零宽/方向控制，并把三行以上空行压成一行。
const normalizeBio = (raw) => {
  const original = String(raw ?? '')
  const value = stripControlChars(stripEmoji(original).replace(/\r\n?/g, '\n'), { keepNewlines: true })
    .replace(SPACE_RE, ' ')
    .replace(/[ \t]*\n[ \t]*/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  if (value.length > BIO_MAX_LENGTH) {
    throw ApiError.badRequest(`个人简介最多 ${BIO_MAX_LENGTH} 个字符`)
  }
  return { value, adjusted: value !== original.trim() }
}

const toClientUser = (user) => ({
  id: user.id,
  username: user.username,
  email: user.email,
  avatar: user.avatar || '',
  bio: user.bio || ''
})

exports.register = async ({ username, email, password }, req) => {
  try {
    if (!username || !email || !password) {
      throw ApiError.badRequest('用户名、邮箱和密码为必填项')
    }
    // 归一化在长度校验之前：`"🎯🎯"` 这类「看着 2 个字符、剥完全没了」的名字要在这里被拒
    const { value: name, adjusted } = normalizeUsername(username)
    if (!EMAIL_RE.test(email)) {
      throw ApiError.badRequest('邮箱格式不正确')
    }
    if (password.length < 6) {
      throw ApiError.badRequest('密码至少 6 位')
    }

    const existing = await User.findOne({ where: { [Op.or]: [{ username: name }, { email }] } })
    if (existing) {
      const conflict = ApiError.conflict('用户名或邮箱已被注册')
      // 挂一个非响应字段：安全事件想知道「撞上的是哪个账号」（账号枚举的命中记录），
      // 但对外文案必须保持模糊（否则注册接口就成了查号器）。响应序列化只取
      // statusCode / message，多挂一个属性不会漏给用户。
      conflict.targetUserId = existing.id
      throw conflict
    }

    const passwordHash = await bcrypt.hash(password, 10)
    const user = await User.create({ username: name, email, password_hash: passwordHash })
    const token = generateToken(user.id)

    // 注册是审计时间线的起点（后面所有日志靠 user_id 串起来），必须留痕。
    // 写入失败只 warn，绝不把注册带崩 —— 见 activityLog.service 的约定。
    await activityLogService.logUserRegistered({ userId: user.id, user, req })

    return { user: toClientUser(user), token, adjusted }
  } catch (error) {
    // 走成功的路径在上面 return 掉了，能落到这里的都是「被拒」。
    // 被拒的注册同样要留痕：撞库、账号枚举、批量注册试探全靠这一条线索。
    // ⚠️ 只记 4xx：5xx 是我们自己的 bug，不是攻击信号，记进安全事件会误导取证。
    // ⚠️ 传进去的只有 username（脱敏后入库），**没有 password** —— 见本模块顶部的约定。
    if (error.statusCode >= 400 && error.statusCode < 500) {
      await securityEventService.logRegisterRejected({
        account: username,
        targetUserId: error.targetUserId,
        reason: error.message,
        req
      })
    }
    throw error
  }
}

exports.login = async ({ email, password }, req) => {
  if (!email || !password) {
    await securityEventService.logLoginRejected({ account: email, reason: '邮箱和密码为必填项', req })
    throw ApiError.badRequest('邮箱和密码为必填项')
  }

  const user = await User.findOne({ where: { email } })
  if (!user || !(await bcrypt.compare(password, user.password_hash))) {
    // 登录失败是本表最重要的信号：它才是「暴力破解 / 撞库」的直接证据。
    // 账号存在时记下 target_user_id（「有人在打这个账号」），不存在时只留脱敏标识。
    // 对外文案刻意不区分这两种情况（防账号枚举），日志里也保持同一口径。
    await securityEventService.logLoginRejected({
      account: email,
      targetUserId: user ? user.id : null,
      reason: '邮箱或密码错误',
      req
    })
    throw ApiError.unauthorized('邮箱或密码错误')
  }

  const token = generateToken(user.id)
  return { user: toClientUser(user), token }
}

exports.getProfile = async (userId) => {
  const user = await User.findByPk(userId, { attributes: { exclude: ['password_hash'] } })
  if (!user) throw ApiError.notFound('用户不存在')
  return user
}

exports.updateProfile = async (userId, { username, avatar, bio }, req) => {
  const user = await User.findByPk(userId)
  if (!user) throw ApiError.notFound('用户不存在')

  // 保存前的快照。日志要记「真正改了什么」，而不是「请求里带了哪些字段」——
  // 前端表单每次都会把三个字段全传一遍，按请求字段记会写出一堆假变更。
  const before = { username: user.username, avatar: user.avatar || '', bio: user.bio || '' }
  const changed = []
  let adjusted = false

  if (username !== undefined && username !== null && String(username).trim() !== '') {
    const { value: name, adjusted: nameAdjusted } = normalizeUsername(username)
    adjusted = adjusted || nameAdjusted
    if (name !== before.username) {
      const duplicated = await User.findOne({ where: { username: name, id: { [Op.ne]: userId } } })
      if (duplicated) throw ApiError.conflict('用户名已被占用')
    }
    user.username = name
    if (name !== before.username) changed.push('username')
  }
  if (avatar !== undefined) {
    const link = String(avatar ?? '').trim()
    if (link.length > AVATAR_MAX_LENGTH) {
      throw ApiError.badRequest(`头像链接最长 ${AVATAR_MAX_LENGTH} 个字符`)
    }
    user.avatar = link
    if (link !== before.avatar) changed.push('avatar')
  }
  if (bio !== undefined) {
    const { value: text, adjusted: bioAdjusted } = normalizeBio(bio)
    adjusted = adjusted || bioAdjusted
    user.bio = text
    if (text !== before.bio) changed.push('bio')
  }

  await user.save()

  // 什么都没改就不留痕：日志的价值在于「每条都值得人读一遍」，
  // 别让「打开编辑又原样保存」这类空提交把时间线灌满噪音。
  if (changed.length) {
    const renamed = changed.includes('username')
    await activityLogService.logUserProfileUpdated({
      userId,
      changedFields: changed,
      usernameFrom: renamed ? before.username : undefined,
      usernameTo: renamed ? user.username : undefined,
      req
    })
  }

  return { user: toClientUser(user), changedFields: changed, adjusted }
}

// 我发表的评论（含所属项目，供个人中心「我参与的讨论」）
exports.getMyComments = async (userId, { page = 1, pageSize = 10 } = {}) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 10 })
  const offset = (page - 1) * limit

  const { rows, count } = await Comment.findAndCountAll({
    where: { user_id: userId },
    include: [{ model: Project, as: 'project', attributes: ['id', 'title'] }],
    order: [['created_at', 'DESC']],
    limit,
    offset,
    distinct: true
  })

  return {
    comments: rows.map((r) => {
      const row = r.toJSON()
      return {
        id: row.id,
        parentId: row.parent_id || null,
        content: row.content,
        createdAt: row.created_at,
        likeCount: row.like_count || 0,
        project: row.project || null
      }
    }),
    total: count,
    page,
    pageSize: limit
  }
}

// 收到的点赞 = 别人给 TA 项目的点赞 + TA 评论收到的点赞
const countLikeReceived = async (userId) => {
  const [likeRows] = await sequelize.query(
    `SELECT
       (SELECT COUNT(*) FROM project_likes pl
          JOIN projects p ON p.id = pl.project_id
          WHERE p.creator_id = :userId AND p.deleted_at IS NULL) AS projectLikes,
       (SELECT COALESCE(SUM(pc.like_count), 0) FROM project_comments pc
          WHERE pc.user_id = :userId AND pc.status = 1) AS commentLikes`,
    { replacements: { userId }, type: sequelize.QueryTypes.SELECT }
  )
  return Number(likeRows.projectLikes || 0) + Number(likeRows.commentLikes || 0)
}

// 个人数据概览：发布数 / 评论数 / 收藏数 / 收到的点赞（项目点赞 + 评论点赞）
exports.getMyStats = async (userId) => {
  const [projectCount, commentCount, favoriteCount, likeReceived] = await Promise.all([
    Project.count({ where: { creator_id: userId } }),
    Comment.count({ where: { user_id: userId } }),
    ProjectFavorite.count({ where: { user_id: userId } }),
    countLikeReceived(userId)
  ])

  return {
    projectCount,
    commentCount,
    favoriteCount,
    likeReceived
  }
}

// 公开主页：任何人可看，所以**不返回 email**（toClientUser 带 email，只用于 /me）
exports.getPublicProfile = async (userId) => {
  const user = await User.findByPk(userId, {
    attributes: ['id', 'username', 'avatar', 'bio', 'created_at']
  })
  if (!user) throw ApiError.notFound('用户不存在')

  const [projectCount, joinedCount, likeReceived] = await Promise.all([
    Project.count({ where: { creator_id: userId } }),
    // 「参与共创」不含自己发起的：否则与上面的发布数重复计数
    ProjectParticipant.count({ where: { user_id: userId, role: { [Op.ne]: 'creator' } } }),
    countLikeReceived(userId)
  ])

  return {
    user: {
      id: user.id,
      username: user.username,
      avatar: user.avatar || '',
      bio: user.bio || '',
      joinedAt: user.created_at
    },
    stats: { projectCount, joinedCount, likeReceived }
  }
}

// 「TA 参与的共创」不在这里另造查询：直接复用 listProjects({ participantId })，
// 排序 / 分页 / 收藏标记都跟广场保持一致

exports.toClientUser = toClientUser

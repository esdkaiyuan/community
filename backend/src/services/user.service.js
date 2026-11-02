const crypto = require('node:crypto')
const bcrypt = require('bcryptjs')
const { Op } = require('sequelize')
const { User, Comment, Project, ProjectParticipant, sequelize } = require('../models')
const { generateToken } = require('../utils/jwt')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const { stripEmoji, stripControlChars } = require('../utils/textSanitize')
const ApiError = require('../utils/ApiError')
const createLogger = require('../utils/logger')
const activityLogService = require('./activityLog.service')
const securityEventService = require('./securityEvent.service')
const emailAuthService = require('./emailAuth.service')
// 收藏计数单独抽成不依赖 project.service 的模块，否则这里反向 require
// favorite.service 会形成 user ➜ favorite ➜ project ➜ user 的循环
const { countVisibleFavorites } = require('./favoriteCount.service')

const log = createLogger('user')

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const EMAIL_CODE_RE = /^\d{6}$/

// 密码边界。**注册与改密必须共用同一对常量与同一个断言函数** —— 分开写迟早漂移
// （本仓库在用户名上就吃过一次：register 不 trim、updateProfile 会 trim）。
//
// 上界为什么是 64：bcrypt 只使用前 **72 个字节**，再长的部分对哈希没有任何贡献，
// 用户却以为自己设了一段很长的密码。按字符数卡 64 之后，纯 ASCII 密码（64 < 72）
// 永远不会被静默截断；多字节密码（一个汉字 3 字节）理论上仍可能越过 72 字节，
// 这是已知且可接受的取舍 —— 24 个汉字以上的密码在「记不住」这条上已经先输了。
const PASSWORD_MIN_LENGTH = 6
const PASSWORD_MAX_LENGTH = 64

// 类型也一并收口：`password.length` 对数字 / 对象是 undefined，而 `undefined < 6`
// 是 false —— 于是 `{"password": 12345}` 这种请求会一路走到 bcrypt.hash 并抛 500。
// 非字符串一律按「太短」拒掉，不给它们任何走到 bcrypt 的机会。
const assertPassword = (password) => {
  if (typeof password !== 'string' || password.length < PASSWORD_MIN_LENGTH) {
    throw ApiError.badRequest(`密码至少 ${PASSWORD_MIN_LENGTH} 位`)
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    throw ApiError.badRequest(`密码最多 ${PASSWORD_MAX_LENGTH} 位`)
  }
  return password
}

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

const normalizeEmail = (raw) => {
  const email = String(raw ?? '').trim()
  if (!EMAIL_RE.test(email)) throw ApiError.badRequest('邮箱格式不正确')
  return email
}

const normalizeEmailCode = (raw) => {
  const code = String(raw ?? '').trim()
  if (!EMAIL_CODE_RE.test(code)) throw ApiError.badRequest('请输入 6 位邮箱验证码')
  return code
}

const pickUsername = (raw) => {
  try {
    return normalizeUsername(raw).value
  } catch {
    return ''
  }
}

// 外部身份中心只保证邮箱唯一，不保证昵称可用；本地 users.username 有唯一约束，
// 所以首次用验证码登录、而本地还没有镜像账号时，需要在这里生成一个可用用户名。
const buildUniqueUsername = async (email, nickname) => {
  const emailPrefix = String(email || '')
    .split('@')[0]
    .replace(/[^A-Za-z0-9_\u4e00-\u9fa5-]/g, '')
    .slice(0, 20)
  let base = pickUsername(nickname) || pickUsername(emailPrefix)
  if (!base) base = `user${crypto.randomBytes(2).toString('hex')}`
  if (base.length < 2) base = `user${base}`.slice(0, 20)
  if (base.length > 20) base = base.slice(0, 20)

  let candidate = base
  for (let i = 0; i < 20; i += 1) {
    const exists = await User.findOne({ where: { username: candidate }, attributes: ['id'] })
    if (!exists) return candidate
    const suffix = crypto.randomBytes(2).toString('hex')
    candidate = `${base.slice(0, 20 - suffix.length)}${suffix}`
  }
  throw ApiError.conflict('无法生成可用用户名，请在个人资料中修改后重试')
}

// 外部用户 -> 本地镜像。邮箱是两边唯一的稳定关联键；本地行只服务于项目 / 评论外键。
// 首次用验证码登录时自动建行，密码列写随机哈希（用户之后可以用「忘记密码」设置密码）。
const findOrCreateLocalUserFromExternal = async ({ email, nickname }, req) => {
  const cleanEmail = normalizeEmail(email)
  const existing = await User.findOne({ where: { email: cleanEmail } })
  if (existing) return { user: existing, created: false }

  const username = await buildUniqueUsername(cleanEmail, nickname)
  const passwordHash = await bcrypt.hash(crypto.randomBytes(24).toString('hex'), 10)
  try {
    const user = await User.create({ username, email: cleanEmail, password_hash: passwordHash })
    await activityLogService.logUserRegistered({ userId: user.id, user, req })
    return { user, created: true }
  } catch (error) {
    // 两个并发首登同时建行：唯一键兜底，输的那一方回头读赢家的行
    if (error.name === 'SequelizeUniqueConstraintError') {
      const raced = await User.findOne({ where: { email: cleanEmail } })
      if (raced) return { user: raced, created: false }
    }
    throw error
  }
}

const toClientUser = (user) => ({
  id: user.id,
  username: user.username,
  email: user.email,
  avatar: user.avatar || '',
  bio: user.bio || ''
})

// 原有账号密码注册的唯一实现；邮箱验证注册成功后也复用它，避免两套校验慢慢漂移。
const createLocalUser = async ({ username, email, password, req }) => {
  if (!username || !email || !password) {
    throw ApiError.badRequest('用户名、邮箱和密码为必填项')
  }
  const { value: name, adjusted } = normalizeUsername(username)
  const cleanEmail = normalizeEmail(email)
  assertPassword(password)

  const existing = await User.findOne({
    where: { [Op.or]: [{ username: name }, { email: cleanEmail }] }
  })
  if (existing) {
    const conflict = ApiError.conflict('用户名或邮箱已被注册')
    conflict.targetUserId = existing.id
    throw conflict
  }

  const passwordHash = await bcrypt.hash(password, 10)
  const user = await User.create({ username: name, email: cleanEmail, password_hash: passwordHash })
  const token = generateToken(user.id, user.token_version)
  await activityLogService.logUserRegistered({ userId: user.id, user, req })
  return { user: toClientUser(user), token, adjusted }
}

exports.register = async ({ username, email, password }, req) => {
  try {
    return await createLocalUser({ username, email, password, req })
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

  const cleanEmail = String(email).trim()
  const user = await User.findOne({ where: { email: cleanEmail } })

  // 1) 本地镜像先比一次：命中就直接放行。
  //    本地镜像的哈希在注册 / 重置 / 改密时都会与外部同步，所以这一步不是「第二套身份」，
  //    而是缓存 —— 既避免所有用户共用服务器 IP 撞外部登录限流，也保证外部服务抖动时能登录。
  if (user && (await bcrypt.compare(password, user.password_hash))) {
    return { user: toClientUser(user), token: generateToken(user.id, user.token_version) }
  }

  // 2) 本地没有 / 密码对不上，再问统一身份中心。
  //    典型场景：用户是在别的接入方改的密码，或本地还没有镜像账号。
  const external = await emailAuthService.passwordLogin({ email: cleanEmail, password })
  if (external.ok) {
    const { user: mirrored, created } = await findOrCreateLocalUserFromExternal(
      {
        email: external.user?.email || cleanEmail,
        nickname: external.user?.nickname
      },
      req
    )
    // 外部验证通过后把这次密码回写本地镜像，下次本地比较就能命中
    if (created || !(await bcrypt.compare(password, mirrored.password_hash))) {
      mirrored.password_hash = await bcrypt.hash(password, 10)
      await mirrored.save()
    }
    return { user: toClientUser(mirrored), token: generateToken(mirrored.id, mirrored.token_version) }
  }

  // 登录失败是本表最重要的信号：它才是「暴力破解 / 撞库」的直接证据。
  // 账号存在时记下 target_user_id（「有人在打这个账号」），不存在时只留脱敏标识。
  // 对外文案刻意不区分这两种情况（防账号枚举），日志里也保持同一口径。
  await securityEventService.logLoginRejected({
    account: cleanEmail,
    targetUserId: user ? user.id : null,
    reason: '邮箱或密码错误',
    req
  })
  // 对外统一 401：外部服务不可用时 passwordLogin 已经记了 warn 日志，运维能在服务端定位；
  // 不能把 503 抛给用户 —— 登录失败本来就该是 401，安全事件也要按 auth.login.rejected 归类。
  throw ApiError.unauthorized('邮箱或密码错误')
}

// 发送邮箱验证码（注册 / 验证码登录 / 找回密码共用）
exports.sendEmailCode = async ({ email }) => {
  const cleanEmail = normalizeEmail(email)
  await emailAuthService.sendCode(cleanEmail)
  return { sent: true }
}

// 邮箱验证码注册：先在外部身份中心完成「验证码 + 密码」注册，再建本地镜像。
exports.registerWithEmailCode = async ({ username, email, password, code }, req) => {
  const cleanEmail = normalizeEmail(email)
  const cleanCode = normalizeEmailCode(code)
  // 先做本地校验，避免把无效资料带到外部、白白消耗验证码
  const { value: name, adjusted } = normalizeUsername(username)
  assertPassword(password)

  const existing = await User.findOne({
    where: { [Op.or]: [{ username: name }, { email: cleanEmail }] }
  })
  if (existing) {
    const conflict = ApiError.conflict('用户名或邮箱已被注册')
    conflict.targetUserId = existing.id
    throw conflict
  }

  try {
    await emailAuthService.register({ email: cleanEmail, code: cleanCode, password, nickname: name })
  } catch (error) {
    // 外部已有同邮箱账号时允许幂等注册：用同一密码登录验证后，继续补本地镜像。
    const alreadyRegistered = /已注册|已存在|already/i.test(error.message || '')
    if (!alreadyRegistered) throw error
    const external = await emailAuthService.passwordLogin({ email: cleanEmail, password })
    if (!external.ok) {
      throw ApiError.conflict('该邮箱已在邮箱服务注册，请直接登录或使用验证码登录')
    }
  }

  try {
    const result = await createLocalUser({ username: name, email: cleanEmail, password, req })
    // createLocalUser 收到的已经是归一化后的名字，adjusted 会是 false；
    // 这里把「原始输入确实被改过」的事实补回去，前端才能提示用户。
    return { ...result, adjusted: result.adjusted || adjusted }
  } catch (error) {
    if (error.statusCode >= 400 && error.statusCode < 500) {
      await securityEventService.logRegisterRejected({
        account: name,
        targetUserId: error.targetUserId,
        reason: error.message,
        req
      })
    }
    throw error
  }
}

// 邮箱验证码登录：验证成功后若本地还没有镜像账号，自动建一行（密码列写随机哈希）。
exports.loginWithEmailCode = async ({ email, code }, req) => {
  const cleanEmail = normalizeEmail(email)
  const cleanCode = normalizeEmailCode(code)

  let verified
  try {
    verified = await emailAuthService.verifyCode({ email: cleanEmail, code: cleanCode })
  } catch (error) {
    if (error.statusCode === 400) {
      await securityEventService.logLoginRejected({
        account: cleanEmail,
        reason: '邮箱验证码无效',
        req
      })
    }
    throw error
  }

  const profile = verified.sessionToken
    ? await emailAuthService.getProfile(verified.sessionToken)
    : null
  const { user } = await findOrCreateLocalUserFromExternal(
    {
      email: verified.user?.email || profile?.email || cleanEmail,
      nickname: profile?.nickname || verified.user?.nickname
    },
    req
  )
  return { user: toClientUser(user), token: generateToken(user.id, user.token_version) }
}

// 忘记密码：外部身份中心重置密码并吊销其会话；本地镜像同步新哈希并 +1 会话版本，
// 这样本地签发的旧令牌也会立即失效。
exports.resetPasswordWithEmailCode = async ({ email, code, password, confirmPassword }, req) => {
  const cleanEmail = normalizeEmail(email)
  const cleanCode = normalizeEmailCode(code)
  const next = assertPassword(password)
  if (next !== confirmPassword) throw ApiError.badRequest('两次输入的密码不一致')

  await emailAuthService.resetPassword({ email: cleanEmail, code: cleanCode, password: next })

  const user = await User.findOne({ where: { email: cleanEmail } })
  if (user) {
    await User.update(
      {
        password_hash: await bcrypt.hash(next, 10),
        token_version: sequelize.literal('token_version + 1')
      },
      { where: { id: user.id } }
    )
    await activityLogService.logUserPasswordChanged({ userId: user.id, req })
  }
  return { reset: true }
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

// 修改登录密码。
//
// 三件事必须一起做，少一件这个功能就是半成品：
//   1. 校验当前密码 —— 否则任何拿到令牌的人都能把主人锁在门外；
//   2. 用新盐重算 bcrypt 哈希；
//   3. **把 token_version +1** —— 让此前签发的所有令牌立即失效（见 middleware/auth.js）。
// 最后返回一张新令牌，让「正在改密的这台设备」不被自己踢下线（其他设备会）。
exports.changePassword = async (userId, { oldPassword, newPassword }, req) => {
  const user = await User.findByPk(userId)
  if (!user) throw ApiError.notFound('用户不存在')

  // 两处都先收口成「一定是字符串」：非字符串（数字 / 数组 / 对象）不该有机会走到 bcrypt
  const current = typeof oldPassword === 'string' ? oldPassword : ''
  if (!current) throw ApiError.badRequest('请填写当前密码')
  const next = assertPassword(newPassword)
  if (next === current) throw ApiError.badRequest('新密码不能与当前密码相同')

  if (!(await bcrypt.compare(current, user.password_hash))) {
    // 「已经登录、却答不出当前密码」是个强信号：多半是别人的令牌到了手，想改密把主人
    // 锁在门外。与登录失败的区别在于它**有确定身份**（就是当前会话的账号），所以能归属
    // 到人，也就该出现在用户自己的安全提醒里 —— 这正是他必须知道的事。
    await securityEventService.logPasswordChangeRejected({
      account: user.email,
      targetUserId: user.id,
      reason: '当前密码不正确',
      req
    })
    throw ApiError.badRequest('当前密码不正确')
  }

  // 原子自增会话版本：读出来 +1 再写回会在并发改密时丢计数（与浏览量同一个坑）。
  // 与换哈希放在同一条 UPDATE 里，避免出现「哈希已换、版本没动」的中间态。
  await User.update(
    {
      password_hash: await bcrypt.hash(next, 10),
      token_version: sequelize.literal('token_version + 1')
    },
    { where: { id: userId } }
  )

  // 外部身份中心也改一次，避免两边密码分叉。
  // ⚠️ 失败只记日志，绝不回滚本地改密：外部服务抖动不该把用户锁在门外。
  // 历史账号可能还没进外部中心，passwordLogin 返回 invalid 属于正常情况。
  try {
    const sync = await emailAuthService.changePassword({
      email: user.email,
      oldPassword: current,
      newPassword: next
    })
    if (!sync.ok && sync.reason === 'failed') {
      log.warn('外部密码同步失败，本地改密已生效:', user.email)
    }
  } catch (error) {
    log.warn('外部密码同步异常，本地改密已生效:', error.message)
  }

  const fresh = await User.findByPk(userId, { attributes: ['id', 'token_version'] })

  // 审计留痕：只记「这个账号改过密码」，**任何形态的密码都不进日志**（明文 / 长度 / 哈希）。
  await activityLogService.logUserPasswordChanged({ userId, req })

  return { token: generateToken(userId, fresh ? fresh.token_version : 0) }
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
    countVisibleFavorites(userId),
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

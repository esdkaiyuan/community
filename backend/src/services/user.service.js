const bcrypt = require('bcryptjs')
const { Op } = require('sequelize')
const { User, Comment, Project, ProjectLike, ProjectFavorite, sequelize } = require('../models')
const { generateToken } = require('../utils/jwt')
const ApiError = require('../utils/ApiError')

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const toClientUser = (user) => ({
  id: user.id,
  username: user.username,
  email: user.email,
  avatar: user.avatar || '',
  bio: user.bio || ''
})

exports.register = async ({ username, email, password }) => {
  if (!username || !email || !password) {
    throw ApiError.badRequest('用户名、邮箱和密码为必填项')
  }
  if (username.length < 2 || username.length > 20) {
    throw ApiError.badRequest('用户名需 2-20 个字符')
  }
  if (!EMAIL_RE.test(email)) {
    throw ApiError.badRequest('邮箱格式不正确')
  }
  if (password.length < 6) {
    throw ApiError.badRequest('密码至少 6 位')
  }

  const existing = await User.findOne({ where: { [Op.or]: [{ username }, { email }] } })
  if (existing) {
    throw ApiError.conflict('用户名或邮箱已被注册')
  }

  const passwordHash = await bcrypt.hash(password, 10)
  const user = await User.create({ username, email, password_hash: passwordHash })
  const token = generateToken(user.id)

  return { user: toClientUser(user), token }
}

exports.login = async ({ email, password }) => {
  if (!email || !password) {
    throw ApiError.badRequest('邮箱和密码为必填项')
  }

  const user = await User.findOne({ where: { email } })
  if (!user || !(await bcrypt.compare(password, user.password_hash))) {
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

exports.updateProfile = async (userId, { username, avatar, bio }) => {
  const user = await User.findByPk(userId)
  if (!user) throw ApiError.notFound('用户不存在')

  if (username !== undefined && username !== null && String(username).trim() !== '') {
    const name = String(username).trim()
    if (name.length < 2 || name.length > 20) {
      throw ApiError.badRequest('用户名需 2-20 个字符')
    }
    if (name !== user.username) {
      const duplicated = await User.findOne({ where: { username: name, id: { [Op.ne]: userId } } })
      if (duplicated) throw ApiError.conflict('用户名已被占用')
    }
    user.username = name
  }
  if (avatar !== undefined) user.avatar = avatar
  if (bio !== undefined) user.bio = bio

  await user.save()
  return toClientUser(user)
}

// 我发表的评论（含所属项目，供个人中心「我参与的讨论」）
exports.getMyComments = async (userId, { page = 1, pageSize = 10 } = {}) => {
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize, 10) || 10))
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

// 个人数据概览：发布数 / 评论数 / 收藏数 / 收到的点赞（项目点赞 + 评论点赞）
exports.getMyStats = async (userId) => {
  const [projectCount, commentCount, favoriteCount] = await Promise.all([
    Project.count({ where: { creator_id: userId } }),
    Comment.count({ where: { user_id: userId } }),
    ProjectFavorite.count({ where: { user_id: userId } })
  ])

  const [likeRows] = await sequelize.query(
    `SELECT
       (SELECT COUNT(*) FROM project_likes pl
          JOIN projects p ON p.id = pl.project_id
          WHERE p.creator_id = :userId AND p.deleted_at IS NULL) AS projectLikes,
       (SELECT COALESCE(SUM(pc.like_count), 0) FROM project_comments pc
          WHERE pc.user_id = :userId AND pc.status = 1) AS commentLikes`,
    { replacements: { userId }, type: sequelize.QueryTypes.SELECT }
  )

  return {
    projectCount,
    commentCount,
    favoriteCount,
    likeReceived: Number(likeRows.projectLikes || 0) + Number(likeRows.commentLikes || 0)
  }
}

exports.toClientUser = toClientUser

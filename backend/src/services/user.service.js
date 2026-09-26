const bcrypt = require('bcryptjs')
const { Op } = require('sequelize')
const { User } = require('../models')
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

exports.toClientUser = toClientUser

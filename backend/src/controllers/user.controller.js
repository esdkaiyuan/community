const bcrypt = require('bcryptjs')
const { Op } = require('sequelize')
const { User } = require('../models')
const { generateToken } = require('../utils/jwt')

// 用户注册
exports.register = async (req, res) => {
  try {
    const { username, email, password } = req.body

    // 验证必填字段
    if (!username || !email || !password) {
      return res.status(400).json({
        success: false,
        message: '用户名、邮箱和密码为必填项'
      })
    }

    // 检查用户名和邮箱是否已存在
    const existingUser = await User.findOne({
      where: {
        [Op.or]: [{ username }, { email }]
      }
    })
    
    if (existingUser) {
      return res.status(400).json({ 
        success: false, 
        message: '用户名或邮箱已被注册' 
      })
    }
    
    // 密码加密
    const password_hash = await bcrypt.hash(password, 10)
    
    // 创建用户
    const user = await User.create({
      username,
      email,
      password_hash
    })
    
    // 生成 token
    const token = generateToken(user.id)
    
    res.status(201).json({
      code: 200,
      success: true,
      message: '注册成功',
      data: {
        user: {
          id: user.id,
          username: user.username,
          email: user.email
        },
        token
      }
    })
  } catch (error) {
    console.error('注册错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}

// 用户登录
exports.login = async (req, res) => {
  try {
    const { email, password } = req.body
    
    if (!email || !password) {
      return res.status(400).json({ 
        success: false, 
        message: '邮箱和密码为必填项' 
      })
    }
    
    // 查找用户
    const user = await User.findOne({ where: { email } })
    
    if (!user) {
      return res.status(401).json({ 
        success: false, 
        message: '邮箱或密码错误' 
      })
    }
    
    // 验证密码
    const isPasswordValid = await bcrypt.compare(password, user.password_hash)
    
    if (!isPasswordValid) {
      return res.status(401).json({ 
        success: false, 
        message: '邮箱或密码错误' 
      })
    }
    
    // 生成 token
    const token = generateToken(user.id)
    
    res.json({
      code: 200,
      success: true,
      message: '登录成功',
      data: {
        user: {
          id: user.id,
          username: user.username,
          email: user.email,
          avatar: user.avatar
        },
        token
      }
    })
  } catch (error) {
    console.error('登录错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}

// 获取用户信息
exports.getProfile = async (req, res) => {
  try {
    const user = await User.findByPk(req.user.userId, {
      attributes: { exclude: ['password_hash'] }
    })
    
    if (!user) {
      return res.status(404).json({ 
        success: false, 
        message: '用户不存在' 
      })
    }
    
    res.json({
      code: 200,
      success: true,
      data: user
    })
  } catch (error) {
    console.error('获取用户信息错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}

// 更新用户信息
exports.updateProfile = async (req, res) => {
  try {
    const { username, avatar, bio } = req.body
    const userId = req.user.userId
    
    const user = await User.findByPk(userId)
    
    if (!user) {
      return res.status(404).json({ 
        success: false, 
        message: '用户不存在' 
      })
    }
    
    // 更新字段
    if (username) user.username = username
    if (avatar) user.avatar = avatar
    if (bio) user.bio = bio
    
    await user.save()
    
    res.json({
      code: 200,
      success: true,
      message: '更新成功',
      data: {
        user: {
          id: user.id,
          username: user.username,
          email: user.email,
          avatar: user.avatar,
          bio: user.bio
        }
      }
    })
  } catch (error) {
    console.error('更新用户信息错误:', error)
    res.status(500).json({ 
      success: false, 
      message: '服务器错误' 
    })
  }
}

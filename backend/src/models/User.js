const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')

const User = sequelize.define('User', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  username: {
    type: DataTypes.STRING(50),
    allowNull: false,
    unique: true
  },
  email: {
    type: DataTypes.STRING(100),
    allowNull: false,
    unique: true
  },
  password_hash: {
    type: DataTypes.STRING(255),
    allowNull: false,
    field: 'password' // 实际数据库列名为 password
  },
  // 会话版本：改密时 +1，JWT 里带着签发时的 tv，auth 中间件比对不上即视为会话失效。
  // 无状态 JWT 没有「吊销」概念，这是最小代价的作废方案（见 middleware/auth.js）。
  token_version: {
    type: DataTypes.INTEGER.UNSIGNED,
    allowNull: false,
    defaultValue: 0
  },
  avatar: {
    type: DataTypes.STRING(255),
    allowNull: true
  },
  bio: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  // 账号状态：1 正常 / 0 停用（管理台停用后，登录与既有会话都会被拒绝）
  status: {
    type: DataTypes.TINYINT,
    allowNull: false,
    defaultValue: 1
  },
  // 管理员标记：唯一权限来源。auth 中间件每次请求都会回查这一列，
  // 因此撤权后既有 JWT 不需要换发也会立即失效（见 middleware/auth.js）
  is_admin: {
    type: DataTypes.TINYINT,
    allowNull: false,
    defaultValue: 0
  }
}, {
  tableName: 'users',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at'
})

module.exports = User

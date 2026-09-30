const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')

// 浏览去重表（project_id + user_id 复合主键：登录用户对同一项目终身只计 1 次浏览量；
// 游客无身份不落此表，照旧每次 +1。主键即唯一键，并发首访由数据库层兜底去重）
const ProjectView = sequelize.define(
  'ProjectView',
  {
    project_id: { type: DataTypes.INTEGER.UNSIGNED, primaryKey: true },
    user_id: { type: DataTypes.INTEGER.UNSIGNED, primaryKey: true }
  },
  {
    tableName: 'project_views',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false
  }
)

module.exports = ProjectView

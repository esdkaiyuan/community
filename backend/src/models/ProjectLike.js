const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')

// 点赞记录表（project_id + user_id 唯一，数据库层面防重复点赞）
const ProjectLike = sequelize.define(
  'ProjectLike',
  {
    project_id: { type: DataTypes.INTEGER, primaryKey: true },
    user_id: { type: DataTypes.INTEGER, primaryKey: true }
  },
  {
    tableName: 'project_likes',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
    indexes: [{ unique: true, fields: ['project_id', 'user_id'] }]
  }
)

module.exports = ProjectLike

const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')
const User = require('./User')
const Project = require('./Project')

// 项目评论（复用线上遗留的 project_comments 表：保留 parent_id/like_count/status 列但暂不启用，保持轻量平铺列表）
const Comment = sequelize.define(
  'Comment',
  {
    id: {
      type: DataTypes.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true
    },
    project_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: false
    },
    user_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: false
    },
    parent_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true,
      comment: '根评论ID（回复功能）；仅两级：回复一律展平挂到根评论'
    },
    like_count: {
      type: DataTypes.INTEGER,
      defaultValue: 0
    },
    content: {
      type: DataTypes.TEXT,
      allowNull: false
    }
  },
  {
    tableName: 'project_comments',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    defaultScope: {
      where: { status: 1 }
    },
    indexes: [{ fields: ['project_id', 'created_at'] }]
  }
)

Comment.belongsTo(User, { foreignKey: 'user_id', as: 'user' })
Comment.belongsTo(Project, { foreignKey: 'project_id', as: 'project' })
User.hasMany(Comment, { foreignKey: 'user_id' })
Project.hasMany(Comment, { foreignKey: 'project_id' })

module.exports = Comment

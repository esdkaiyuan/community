const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')

// 评论点赞记录表（comment_id + user_id 唯一，数据库层面防重复点赞）
const CommentLike = sequelize.define(
  'CommentLike',
  {
    comment_id: { type: DataTypes.INTEGER.UNSIGNED, primaryKey: true },
    user_id: { type: DataTypes.INTEGER.UNSIGNED, primaryKey: true }
  },
  {
    tableName: 'comment_likes',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
    indexes: [{ unique: true, fields: ['comment_id', 'user_id'] }]
  }
)

module.exports = CommentLike

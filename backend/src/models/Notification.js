const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')
const User = require('./User')
const Project = require('./Project')
const Comment = require('./Comment')

// 站内通知：评论/回复/点赞/参与触发（actor 与 user 相同时不产生）
const Notification = sequelize.define(
  'Notification',
  {
    id: {
      type: DataTypes.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true
    },
    user_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: false,
      comment: '接收人'
    },
    actor_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: false,
      comment: '触发者'
    },
    type: {
      // mention：评论内容里 @ 到了用户（见 comment.service 的 extractMentions）
      type: DataTypes.ENUM('comment', 'reply', 'like', 'participate', 'mention'),
      allowNull: false
    },
    project_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: false
    },
    comment_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true
    },
    is_read: {
      type: DataTypes.TINYINT,
      defaultValue: 0
    }
  },
  {
    tableName: 'notifications',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
    indexes: [{ fields: ['user_id', 'is_read'] }]
  }
)

Notification.belongsTo(User, { foreignKey: 'actor_id', as: 'actor' })
Notification.belongsTo(Project, { foreignKey: 'project_id', as: 'project' })
Notification.belongsTo(Comment, { foreignKey: 'comment_id', as: 'comment' })

module.exports = Notification

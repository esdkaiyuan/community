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
      // system：管理员从管理台发出的站内公告，没有关联项目（project_id 为空）
      type: DataTypes.ENUM('comment', 'reply', 'like', 'participate', 'mention', 'system'),
      allowNull: false
    },
    project_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true
    },
    comment_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true
    },
    // 系统公告正文。互动类通知的正文仍来自评论快照，此列只服务 type=system
    message: {
      type: DataTypes.STRING(255),
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

Notification.belongsTo(User, { foreignKey: 'user_id', as: 'recipient' })
Notification.belongsTo(User, { foreignKey: 'actor_id', as: 'actor' })
Notification.belongsTo(Project, { foreignKey: 'project_id', as: 'project' })
Notification.belongsTo(Comment, { foreignKey: 'comment_id', as: 'comment' })

module.exports = Notification

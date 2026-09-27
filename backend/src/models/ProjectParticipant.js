const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')
const Project = require('./Project')
const User = require('./User')

const ProjectParticipant = sequelize.define('ProjectParticipant', {
  project_id: {
    type: DataTypes.INTEGER,
    primaryKey: true
  },
  user_id: {
    type: DataTypes.INTEGER,
    primaryKey: true
  },
  role: {
    type: DataTypes.ENUM('creator', 'member', 'observer'),
    defaultValue: 'member'
  }
}, {
  tableName: 'project_participants',
  timestamps: true,
  createdAt: 'joined_at',
  updatedAt: false
})

// 定义关联关系
Project.belongsToMany(User, { through: ProjectParticipant, foreignKey: 'project_id', as: 'participants' })
User.belongsToMany(Project, { through: ProjectParticipant, foreignKey: 'user_id', as: 'joinedProjects' })

// 直接查中间表时带上用户信息（拿得到 role / joined_at）
ProjectParticipant.belongsTo(User, { foreignKey: 'user_id', as: 'user' })

module.exports = ProjectParticipant

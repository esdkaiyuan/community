const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')
const User = require('./User')
const Category = require('./Category')

const Project = sequelize.define('Project', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  title: {
    type: DataTypes.STRING(200),
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: false
  },
  cover_image: {
    type: DataTypes.STRING(255),
    allowNull: true
  },
  category_id: {
    type: DataTypes.INTEGER,
    allowNull: true
  },
  creator_id: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  status: {
    type: DataTypes.ENUM('draft', 'published', 'completed', 'archived'),
    defaultValue: 'published'
  },
  likes_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  comments_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  participants_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  }
}, {
  tableName: 'projects',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at'
})

// 定义关联关系
Project.belongsTo(Category, { foreignKey: 'category_id', as: 'category' })
Project.belongsTo(User, { foreignKey: 'creator_id', as: 'creator' })
Category.hasMany(Project, { foreignKey: 'category_id' })
User.hasMany(Project, { foreignKey: 'creator_id' })

module.exports = Project

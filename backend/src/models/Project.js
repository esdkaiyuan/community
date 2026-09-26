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
    type: DataTypes.TINYINT,
    defaultValue: 0
  },
  tags: {
    type: DataTypes.TEXT,
    allowNull: true,
    get() {
      const raw = this.getDataValue('tags')
      if (!raw) return []
      if (Array.isArray(raw)) return raw
      try {
        return JSON.parse(raw)
      } catch (e) {
        return []
      }
    },
    set(val) {
      this.setDataValue('tags', typeof val === 'string' ? val : JSON.stringify(val || []))
    }
  },
  is_recommend: {
    type: DataTypes.TINYINT,
    defaultValue: 0
  },
  is_hot: {
    type: DataTypes.TINYINT,
    defaultValue: 0
  },
  like_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  comment_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  participant_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  view_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  }
}, {
  tableName: 'projects',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at',
  deletedAt: 'deleted_at',
  paranoid: true
})

// 定义关联关系
Project.belongsTo(Category, { foreignKey: 'category_id', as: 'category' })
Project.belongsTo(User, { foreignKey: 'creator_id', as: 'creator' })
Category.hasMany(Project, { foreignKey: 'category_id' })
User.hasMany(Project, { foreignKey: 'creator_id' })

module.exports = Project

const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')
const Project = require('./Project')

// 项目收藏（复用线上遗留的 project_favorites 表：自增主键 + (project_id,user_id) 唯一键防重复收藏）
const ProjectFavorite = sequelize.define(
  'ProjectFavorite',
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
    }
  },
  {
    tableName: 'project_favorites',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
    indexes: [{ unique: true, fields: ['project_id', 'user_id'] }]
  }
)

// 关联：收藏 -> 项目（"我的收藏"列表按收藏时间倒序取项目）
ProjectFavorite.belongsTo(Project, { foreignKey: 'project_id', as: 'project' })

module.exports = ProjectFavorite

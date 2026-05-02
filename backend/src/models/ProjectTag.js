const { DataTypes } = require('sequelize')
const sequelize = require('../../config/database')
const Project = require('./Project')
const Tag = require('./Tag')

const ProjectTag = sequelize.define('ProjectTag', {
  project_id: {
    type: DataTypes.INTEGER,
    primaryKey: true
  },
  tag_id: {
    type: DataTypes.INTEGER,
    primaryKey: true
  }
}, {
  tableName: 'project_tags',
  timestamps: false
})

// 定义关联关系
Project.belongsToMany(Tag, { through: ProjectTag, foreignKey: 'project_id' })
Tag.belongsToMany(Project, { through: ProjectTag, foreignKey: 'tag_id' })

module.exports = ProjectTag

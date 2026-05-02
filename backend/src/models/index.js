const sequelize = require('../config/database')
const User = require('./User')
const Project = require('./Project')
const Category = require('./Category')
const Tag = require('./Tag')
const ProjectTag = require('./ProjectTag')
const ProjectParticipant = require('./ProjectParticipant')

module.exports = {
  sequelize,
  User,
  Project,
  Category,
  Tag,
  ProjectTag,
  ProjectParticipant
}

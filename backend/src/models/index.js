const sequelize = require('../config/database')
const User = require('./User')
const Project = require('./Project')
const Category = require('./Category')
const ProjectParticipant = require('./ProjectParticipant')
const ProjectLike = require('./ProjectLike')
const Comment = require('./Comment')
const CommentLike = require('./CommentLike')
const Notification = require('./Notification')
const ProjectFavorite = require('./ProjectFavorite')
const ProjectView = require('./ProjectView')
const ActivityLog = require('./ActivityLog')
const SecurityEvent = require('./SecurityEvent')

module.exports = {
  sequelize,
  User,
  Project,
  Category,
  ProjectParticipant,
  ProjectLike,
  Comment,
  CommentLike,
  Notification,
  ProjectFavorite,
  ProjectView,
  ActivityLog,
  SecurityEvent
}

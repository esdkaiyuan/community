const { Category, User, ProjectFavorite, Project } = require('../models')
const { toClientProject } = require('./project.service')

// 我的收藏：按收藏时间倒序（收藏关系分页，再取项目详情）
exports.listFavorites = async ({ userId, page = 1, pageSize = 12 }) => {
  page = Math.max(1, parseInt(page, 10) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize, 10) || 12))
  const offset = (page - 1) * limit

  const { rows, count } = await ProjectFavorite.findAndCountAll({
    where: { user_id: userId },
    include: [
      {
        model: Project,
        as: 'project',
        include: [
          { model: Category, as: 'category', attributes: ['id', 'name', 'icon'] },
          { model: User, as: 'creator', attributes: ['id', 'username', 'avatar'] }
        ]
      }
    ],
    order: [['created_at', 'DESC']],
    limit,
    offset,
    distinct: true
  })

  return {
    projects: rows
      .filter((row) => row.project) // 项目被软删除时关系仍存在，过滤掉
      .map((row) => toClientProject(row.project, { favorited: true, favoritedAt: row.created_at })),
    total: count,
    page,
    pageSize: limit
  }
}

// 收藏总数（个人中心概览用）
exports.countFavorites = (userId) => ProjectFavorite.count({ where: { user_id: userId } })

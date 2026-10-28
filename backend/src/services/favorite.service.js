const { Category, User, ProjectFavorite, Project } = require('../models')
const { clampInt, MAX_PAGE } = require('../utils/pagination')
const { toClientProject } = require('./project.service')
const { countVisibleFavorites } = require('./favoriteCount.service')

// 我的收藏：按收藏时间倒序（收藏关系分页，再取项目详情）
exports.listFavorites = async ({ userId, page = 1, pageSize = 12 }) => {
  page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
  const limit = clampInt(pageSize, { max: 50, fallback: 12 })
  const offset = (page - 1) * limit

  const { rows, count } = await ProjectFavorite.findAndCountAll({
    where: { user_id: userId },
    include: [
      {
        model: Project,
        as: 'project',
        // required: true —— 软删除的项目不参与分页，也不参与计数。
        // 用 LEFT JOIN 的话行还在、只是 row.project 为 null，于是 count 把软删项目
        // 算进 total、列表又把它过滤掉：同一个响应里 total 与条数对不上，
        // 「加载更多」也永远显示（length < total 恒成立）
        required: true,
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
      // required: true 之后 row.project 不会再是 null；这层过滤保留作防御 ——
      // 万一将来有人把 include 改回 LEFT JOIN，至少不会崩在 toClientProject 里
      .filter((row) => row.project)
      .map((row) => toClientProject(row.project, { favorited: true, favoritedAt: row.created_at })),
    // count 现在与 projects 同口径：INNER JOIN 已把软删项目排除在计数之外
    total: count,
    page,
    pageSize: limit
  }
}

// 收藏总数（个人中心概览用）。
// 此前是 `ProjectFavorite.count({ where: { user_id } })`，会把已软删项目算进去，
// 与列表口径分叉；口径统一收在 favoriteCount.service.js，此处只是旧名的转出
exports.countFavorites = countVisibleFavorites

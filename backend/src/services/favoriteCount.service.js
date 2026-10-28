const { ProjectFavorite, Project } = require('../models')

/**
 * 用户「可见收藏」数：排除已软删除的项目。
 *
 * 为什么不能直接 `ProjectFavorite.count({ where: { user_id } })`：
 * `projects` 是 paranoid 软删除（`deleted_at`），而 `project_favorites` 外键上的
 * `ON DELETE CASCADE` 只在**物理删除**时触发。项目软删后关系行仍留在表里，
 * 直接 count 会把它算进去 —— 于是「个人中心显示收藏 8 个」而「我的收藏」列表
 * 只有 6 条，且列表的「加载更多」永远显示（length < total 恒成立）。
 *
 * `required: true` 生成 INNER JOIN，paranoid 的 `deleted_at IS NULL` 会被自动带上，
 * 与 `favorite.service.listFavorites` 的取数口径严格一致。两处必须同源，
 * 否则就是同一个数字两套算法。
 *
 * 为什么独立成模块而不是放进 favorite.service.js：
 * 依赖链是 favorite.service ➜ project.service ➜ user.service。若 user.service
 * 反向 require favorite.service 就会成环，此时 project.service 拿到的
 * `toClientUser` 还是 undefined（user.service 尚未执行完 exports 赋值），
 * 一调用就 TypeError。这个模块只依赖 models，谁都可以安全引用。
 */
const countVisibleFavorites = (userId) =>
  ProjectFavorite.count({
    where: { user_id: userId },
    include: [{ model: Project, as: 'project', required: true, attributes: [] }],
    distinct: true
  })

module.exports = { countVisibleFavorites }

const { Op } = require('sequelize')
const { Project } = require('../models')
const { isManagedCover, deleteManagedFile } = require('../utils/coverFile')

/**
 * 回收一个「不再被任何项目引用」的站内上传封面。
 *
 * 只处理本站托管的路径：外链（https://... 或用户随便填的串）不是我们磁盘上的东西，
 * 碰不得。
 *
 * 删之前必须再查一次引用数 —— upload 接口返回的 URL 是公开可见的，理论上存在
 * 「A 项目把自己的封面写成 B 项目那张图」的情况（cover_image 走 req.body 直存，
 * 没有归属校验）。只认「自己这一个项目在引用」才删，避免连坐删掉别人的封面。
 *
 * @param {string} url            旧的 cover_image 值
 * @param {number} ignoreProjectId 刚改完封面、需要排除在外的项目 id（可省略）
 * @returns {Promise<boolean>}    是否真的删掉了文件
 */
exports.releaseCover = async (url, ignoreProjectId) => {
  if (!isManagedCover(url)) return false

  const where = { cover_image: url }
  if (ignoreProjectId != null) where.id = { [Op.ne]: ignoreProjectId }

  // paranoid: false —— 软删除的项目也算「还引用着」。
  // 删除项目是软删（可恢复），把它的封面文件提前删掉会让恢复变得残缺，
  // 所以这类文件交给人工决策，不在这里自动回收。
  const stillUsed = await Project.count({ where, paranoid: false })
  if (stillUsed > 0) return false

  return deleteManagedFile(url)
}

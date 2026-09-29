const fs = require('node:fs')
const path = require('node:path')

// 上传目录：与 middleware/upload.js 里的 COVER_DIR 同源。
// 这里不复用它的导出，是为了让 utils 层不反向依赖 middleware（否则以后换存储要连着改）。
const COVER_DIR = path.resolve(__dirname, '../../uploads/projects')

// 站内封面的 URL 前缀，与 upload.controller 返回的相对路径一致
const COVER_URL_PREFIX = '/uploads/projects/'

// 合法文件名：只允许字母数字与 . _ -，且不以点开头。
// 这条白名单一次挡掉路径分隔符、Windows 盘符冒号、\0、以及 "." / ".."
const SAFE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/

/**
 * 判断是不是「本服务托管的上传封面」路径。
 *
 * 用户的 cover_image 是不可信输入（走 req.body 直存），可能是站外 URL、
 * 也可能是 "/uploads/projects/../../package.json" 这类穿越串。只有满足
 * 「自家前缀 + 单层合法文件名」才认，其余一律当成外部资源、不碰磁盘。
 */
const isManagedCover = (url) => {
  if (typeof url !== 'string' || !url.startsWith(COVER_URL_PREFIX)) return false
  const name = url.slice(COVER_URL_PREFIX.length)
  return SAFE_NAME.test(name)
}

/**
 * 托管路径 -> 磁盘绝对路径；不是托管路径、或解析后跑出 COVER_DIR 之外，返回 null。
 * 第二道 relative 检查是冗余的（白名单已排除分隔符），保留它是为了将来放宽白名单时仍有兜底。
 */
const resolveManagedPath = (url) => {
  if (!isManagedCover(url)) return null
  const name = url.slice(COVER_URL_PREFIX.length)
  const abs = path.resolve(COVER_DIR, name)
  const rel = path.relative(COVER_DIR, abs)
  if (!rel || rel.startsWith('..') || path.isAbsolute(rel)) return null
  return abs
}

/**
 * 删除一个由本服务托管的封面文件。幂等：文件不存在视为「已经没有垃圾了」，返回 false。
 * 删除失败（权限、被占用）不抛异常 —— 调用方通常是「封面已经换好了」的收尾阶段，
 * 不该为了一个文件的回收失败把成功的编辑操作回滚掉，记日志交运维处理即可。
 */
const deleteManagedFile = (url) => {
  const abs = resolveManagedPath(url)
  if (!abs) return false
  try {
    fs.unlinkSync(abs)
    return true
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.warn('[coverFile] 删除封面文件失败:', abs, err.code || err.message)
    }
    return false
  }
}

module.exports = {
  COVER_DIR,
  COVER_URL_PREFIX,
  isManagedCover,
  resolveManagedPath,
  deleteManagedFile
}

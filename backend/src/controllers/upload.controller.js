const asyncHandler = require('../utils/asyncHandler')
const { ok } = require('../utils/response')
const ApiError = require('../utils/ApiError')
const { MAX_FILE_SIZE } = require('../middleware/upload')

// 上传封面：返回可持久化的**相对路径**而不是带 host 的完整 URL。
// 相对路径在开发（Vite 把 /uploads 代理到后端）与生产（Nginx 同域）下都成立，
// 换域名、加 CDN 都不用改库里已存的数据。
exports.uploadCover = asyncHandler(async (req, res) => {
  if (!req.file) throw ApiError.badRequest('请选择要上传的图片')

  ok(
    res,
    {
      url: `/uploads/projects/${req.file.filename}`,
      size: req.file.size,
      maxSize: MAX_FILE_SIZE
    },
    '封面上传成功'
  )
})

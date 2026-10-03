const fs = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')
const multer = require('multer')
const ApiError = require('../utils/ApiError')

// 上传根目录：backend/uploads —— 与 server.js 里挂的 /uploads 静态服务同源。
// 放在后端目录下（而不是 frontend/public）：源码目录不该被用户上传的内容污染，
// 且生产环境一般由 Nginx 直接指向这个目录。
const UPLOAD_ROOT = path.resolve(__dirname, '../../uploads')
const COVER_DIR = path.join(UPLOAD_ROOT, 'projects')

// 首次启动时目录还不存在：先建好，否则第一次上传直接 500
fs.mkdirSync(COVER_DIR, { recursive: true })

// 单文件上限 5MB。封面是 16:9 的展示图，5MB 足够且不至于把磁盘吃满
const MAX_FILE_SIZE = 5 * 1024 * 1024

// MIME -> 扩展名白名单。扩展名一律由服务端按 MIME 决定，
// 绝不采用用户传来的文件名（防路径穿越 + 防 .php/.js 之类的伪装扩展名）
const MIME_EXT = {
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
  'image/gif': '.gif'
}

// 文件头魔数：客户端声明的 MIME 是**可以伪造**的（把文本改名成 .png 即可通过 fileFilter），
// 只有读真正的字节才能判断它是不是图片。承诺「只支持图片」就得兑现到这一层。
const MAGIC = {
  'image/jpeg': (b) => b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff,
  'image/png': (b) => b.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])),
  'image/gif': (b) => b.subarray(0, 4).toString('latin1') === 'GIF8',
  'image/webp': (b) =>
    b.subarray(0, 4).toString('latin1') === 'RIFF' && b.subarray(8, 12).toString('latin1') === 'WEBP'
}

// 记住「本次请求正在写的那个文件」的**确切路径**。
//
// 为什么必须记路径、不能事后按目录差集去猜：
//   multer 的 diskStorage 是「先落盘、再判断」，超限时 req.file / err.file 都还没挂上，
//   拿不到路径。但 filename 回调**一定**已经被调用过（实测：超限前它就拿到了名字），
//   所以在这里把完整路径挂到 req 上，拒绝时就能精确删掉自己的那一个。
//
//   ⚠️ 曾经用「拍目录快照 → 差集删除」来兜底，**是错的**：两次上传相邻时，
//   后一个请求的快照早于前一个文件落盘，差集会把**别人的文件**一起删掉
//   （实测小图/GIF 上传成功后文件被误删，cover_compress 直接 8 条红）。
//   删除必须精确到自己的文件，绝不能靠猜。
const storage = multer.diskStorage({
  destination: (req, _file, cb) => cb(null, COVER_DIR),
  filename: (req, file, cb) => {
    // 时间戳 + 12 位随机 hex：防同名覆盖，且与用户文件名彻底无关
    const ext = MIME_EXT[file.mimetype] || '.img'
    const name = `${Date.now()}-${crypto.randomBytes(6).toString('hex')}${ext}`
    req._inflightPath = path.join(COVER_DIR, name)
    cb(null, name)
  }
})

const handler = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE, files: 1 },
  fileFilter: (_req, file, cb) => {
    if (!MIME_EXT[file.mimetype]) {
      cb(ApiError.badRequest('只支持 JPG / PNG / WebP / GIF 格式的图片'))
      return
    }
    cb(null, true)
  }
}).single('file')

// 删掉刚落盘的文件。**任何拒绝路径都必须走这里** ——
// multer 的 diskStorage 是「先落盘、再判断」：文件在 limits 触发时就已经在磁盘上了，
// 不显式删就是每被拒一次留一份垃圾（超大请求可以反复打，把磁盘吃满）。
// 删除失败不影响给用户的结论（已经要拒绝了），只留给运维/孤儿清扫兜底。
const discard = (file) => {
  if (!file?.path) return
  try {
    fs.unlinkSync(file.path)
  } catch {
    // 忽略：文件可能已被别处删掉
  }
}

// 删掉「本次请求写到一半的那个文件」。req._inflightPath 由 storage.filename 写入，
// 超限时 req.file 还没挂上，只能靠它。只删自己那一个，不碰目录里的其他文件。
const discardInflight = (req) => {
  if (!req._inflightPath) return
  discard({ path: req._inflightPath })
  req._inflightPath = null
}

// 读完头部 12 字节做魔数校验；不是真图片就把刚落盘的文件删掉，别在磁盘上留垃圾
const assertRealImage = (file) => {
  const HEAD = 12
  const head = Buffer.alloc(HEAD)
  const fd = fs.openSync(file.path, 'r')
  try {
    fs.readSync(fd, head, 0, HEAD, 0)
  } finally {
    fs.closeSync(fd)
  }
  if (MAGIC[file.mimetype]?.(head)) return
  discard(file)
  throw ApiError.badRequest('这个文件看起来不是真正的图片，请换一张试试')
}

// 包一层：把 multer 自己的错误码翻译成前端读得懂的 400。
// 直接暴露 MulterError 会落到 errorHandler 的 500 兜底，用户只看到「服务器错误」
const uploadCover = (req, res, next) => {
  handler(req, res, (err) => {
    if (err) {
      // 走到这里说明请求被拒（超限 / 字段名不对 / 数量超），但 multer 可能已经把
      // 文件写到磁盘上了 —— 拒之前先清掉，否则每次被拒都漏一份垃圾在磁盘上。
      // 超限时 req.file 还没挂上，靠 storage.filename 记下的路径精确清理。
      discard(req.file)
      discardInflight(req)
      if (err instanceof multer.MulterError) {
        if (err.code === 'LIMIT_FILE_SIZE') {
          return next(ApiError.badRequest('图片不能超过 5MB，请压缩后再上传'))
        }
        if (err.code === 'LIMIT_UNEXPECTED_FILE') {
          return next(ApiError.badRequest('上传字段名应为 file'))
        }
        return next(ApiError.badRequest(`图片上传失败：${err.message}`))
      }
      return next(err)
    }

    try {
      if (req.file) assertRealImage(req.file)
    } catch (e) {
      // 魔数不过：assertRealImage 已经删了 req.file，这里只把记账擦掉
      req._inflightPath = null
      return next(e)
    }
    // 走到这说明文件被接纳了，路径记账不再需要（留着会被后续误当成待清理的残留）
    req._inflightPath = null
    next()
  })
}

module.exports = { uploadCover, UPLOAD_ROOT, COVER_DIR, MAX_FILE_SIZE, MIME_EXT }

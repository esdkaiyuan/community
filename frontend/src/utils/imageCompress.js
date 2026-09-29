// 上传前的图片压缩（纯前端，canvas 重编码）。
//
// 为什么需要它：手机拍的原图动辄 6~10MB，而服务端上限是 5MB —— 旧流程会直接把用户
// 挡回去（「图片不能超过 5MB，请压缩后再上传」），等于让用户自己去找工具压一遍。
// 这一步替他们做掉：在本机把大图降采样 + 重新编码，用户无感。
//
// 三条设计约束（每一条都对应一个「不做会更糟」）：
//   1. **只降不升**：尺寸只缩不放，且原图本来就小就**原样上传**。
//      重编码不是免费的 —— 一张 30KB 的小图过一遍 canvas 往往变成 60KB 的 WebP，
//      无谓地把用户的图变模糊又变大。
//   2. **GIF 一律不动**：canvas 只能画第一帧，重编码会把动图压成一张静图，
//      比「超限被拒」糟得多（用户丢的是内容，不是一次操作）。
//   3. **失败就退回原图**：解不出来（冷门格式 / 损坏文件）时静默返回原文件，
//      交给原有的类型 / 体积校验去报错。压缩本身绝不能成为上传失败的原因。

// 长边上限。封面在卡片与详情页最大展示宽度远小于此，1920 已经有余量；
// 这个值同时被 scripts/verify_cover_compress.py 从源码里读出来做断言，
// 所以它是一处「口径」而不只是一个魔法数字。
export const COVER_MAX_DIMENSION = 1920

// WebP 质量：肉眼与 q=1 无差，体积常为原图的 1/5 ~ 1/10
export const COVER_QUALITY = 0.82

// 低于这个体积且尺寸也没超，就完全不碰它（见约束 1）
export const COVER_COMPRESS_MIN_BYTES = 1.5 * 1024 * 1024

/** 把字节数说成人话，用于「已自动压缩 9.4 MB → 1.2 MB」这类提示 */
export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  if (bytes < 1024) return `${Math.round(bytes)} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const closeSource = (source) => {
  if (typeof ImageBitmap !== 'undefined' && source instanceof ImageBitmap) source.close()
}

/** 解码成可画到 canvas 的东西。优先 createImageBitmap（不占 DOM、可在 worker 用），退回 <img> */
const decode = async (file) => {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file)
    } catch {
      // 落到 <img> 兜底：某些浏览器对个别格式 createImageBitmap 会失败但 <img> 能解
    }
  }
  return await new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片解码失败'))
    }
    img.src = url
  })
}

const encode = (canvas, type, quality) =>
  new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), type, quality)
  })

/**
 * 把一张图片压到「长边 ≤ maxDimension，且体积尽量小」。
 *
 * @returns {Promise<{file: File, compressed: boolean, reason?: string, originalBytes?: number}>}
 *   `compressed` 为 false 时 file 就是入参原样（调用方可以直接上传）。
 *   永不抛异常 —— 任何一步出问题都退回原图。
 */
export async function compressImage(file, options = {}) {
  const {
    maxDimension = COVER_MAX_DIMENSION,
    quality = COVER_QUALITY,
    minBytes = COVER_COMPRESS_MIN_BYTES
  } = options

  if (!file || !file.type || !file.type.startsWith('image/')) {
    return { file, compressed: false, reason: 'not-image' }
  }
  // 约束 2：动图不碰
  if (file.type === 'image/gif') {
    return { file, compressed: false, reason: 'gif' }
  }

  let source
  try {
    source = await decode(file)
  } catch {
    // 约束 3：解不出来就原样放行，让原校验去给结论
    return { file, compressed: false, reason: 'decode-failed' }
  }

  try {
    const width = source.width || source.naturalWidth || 0
    const height = source.height || source.naturalHeight || 0
    const longSide = Math.max(width, height)
    if (!width || !height) return { file, compressed: false, reason: 'no-size' }

    const scale = longSide > maxDimension ? maxDimension / longSide : 1

    // 约束 1：尺寸没超、体积也不大 → 原样上传
    if (scale === 1 && file.size <= minBytes) {
      return { file, compressed: false, reason: 'already-small' }
    }

    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(width * scale))
    canvas.height = Math.max(1, Math.round(height * scale))

    const ctx = canvas.getContext('2d')
    if (!ctx) return { file, compressed: false, reason: 'no-2d-context' }
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height)

    // WebP 优先：体积最小，且**保留透明通道**（PNG 带透明的封面转 JPEG 会把透明区域压成黑色）。
    // 浏览器不支持 canvas 导出 WebP 时退回 JPEG。
    let blob = await encode(canvas, 'image/webp', quality)
    let ext = 'webp'
    let mime = 'image/webp'
    if (!blob) {
      blob = await encode(canvas, 'image/jpeg', quality)
      ext = 'jpg'
      mime = 'image/jpeg'
    }
    // 压完反而更大（原图已经是精压过的）→ 保留原图，别把用户的东西越弄越差
    if (!blob || blob.size >= file.size) {
      return { file, compressed: false, reason: 'not-smaller' }
    }

    const baseName = (file.name || 'cover').replace(/\.[^./\\]+$/, '') || 'cover'
    return {
      file: new File([blob], `${baseName}.${ext}`, { type: mime }),
      compressed: true,
      originalBytes: file.size
    }
  } catch {
    return { file, compressed: false, reason: 'encode-failed' }
  } finally {
    closeSource(source)
  }
}

// 封面裁剪：把「16:9 的取景框里究竟留下哪一块」交给用户自己决定。
//
// 为什么需要它：封面在所有展示位都按 16:9 展示 —— 广场卡片（ProjectCard.vue）、
// 相关推荐（RelatedProjects.vue）、发布页实时预览、详情页头图（ProjectDetailView.vue），
// 全部是 object-cover，「填满容器、溢出裁掉」。一张竖版手机照在这种容器里会被 CSS
// 从正中间横切一刀，主体（人、作品、招牌）常常正好落在被切掉的那部分，
// 而用户此前没有任何办法干预。
//
// 取景框与所有展示位取同一个 16:9：用户在框里框定的画面，会原样出现在卡片和详情页
// 头图上，不存在「框内看着好、卡片上却被切掉两侧」的落差。
// 改这里的比例，必须同步改所有封面展示位与 scripts/verify_cover_crop.py 的断言。
//
// 本文件刻意**零依赖、纯函数**：几何部分不碰 DOM、不 import 任何东西，
// 因此 scripts/verify_cover_crop.py 可以把源码复制成 .mjs 直接交给 node 跑真函数做断言
// —— 断言与实现共用同一份公式，而不是测试里另写一份（那种测试在实现写错时照样绿）。

// 取景框比例 = 卡片展示位比例。被验证脚本从源码里读出来做断言，所以它是一处「口径」。
export const COVER_ASPECT = 16 / 9
// 给用户看的写法。必须与上面的数字一致 —— 不一致就是界面在骗人，
// 验证脚本会把这两个值对起来算一遍。
export const COVER_ASPECT_LABEL = '16:9'
// 放大上限：再大只是把像素拉糊，留不住更多信息
export const COVER_CROP_MAX_ZOOM = 3

/**
 * 让整张图「铺满」取景框所需的最小缩放（取两个方向的较大者）。
 * 这是 zoom = 1 的定义：此时图片恰好覆盖取景框，短边对齐、长边溢出。
 */
export function fitScale(srcW, srcH, frameW, frameH) {
  if (!srcW || !srcH || !frameW || !frameH) return 1
  return Math.max(frameW / srcW, frameH / srcH)
}

/**
 * 平移偏移的合法区间是 [frame - display, 0]：
 * 图片左上角不能跑到取景框右下角之内（否则露出空白），也不能跑到左上角之外（否则露白边）。
 * 当图片某一方向正好等于取景框时不产生偏移空间（min 与 max 都是 0）。
 */
export function clampPan(panX, panY, dispW, dispH, frameW, frameH) {
  const minX = Math.min(0, frameW - dispW)
  const minY = Math.min(0, frameH - dispH)
  const x = Math.max(minX, Math.min(0, Number.isFinite(panX) ? panX : 0))
  const y = Math.max(minY, Math.min(0, Number.isFinite(panY) ? panY : 0))
  return { x, y }
}

/** 居中 = object-cover 的默认行为。裁剪器一打开就是这个状态，所以预览与产物是同一个画面。 */
export function centeredPan(srcW, srcH, frameW, frameH, zoom = 1) {
  const scale = fitScale(srcW, srcH, frameW, frameH) * Math.max(1, zoom)
  const dispW = srcW * scale
  const dispH = srcH * scale
  return clampPan((frameW - dispW) / 2, (frameH - dispH) / 2, dispW, dispH, frameW, frameH)
}

/**
 * 取景框对应到**原图坐标系**的矩形 —— 这就是要交给 canvas 的裁剪区域。
 *
 * 入参的 frameW/frameH 是取景框的显示尺寸，panX/panY 是图片左上角相对取景框左上角的
 * 显示偏移（两者都是 CSS 像素）。注意区域尺寸与偏移只依赖 zoom 和「归一化后的平移」，
 * 与取景框的绝对像素大小无关 —— 换个视口打开，裁出来的还是同一块。
 */
export function cropRegion({ srcW, srcH, frameW, frameH, zoom = 1, panX = 0, panY = 0 }) {
  const scale = fitScale(srcW, srcH, frameW, frameH) * Math.max(1, zoom)
  const dispW = srcW * scale
  const dispH = srcH * scale
  const { x, y } = clampPan(panX, panY, dispW, dispH, frameW, frameH)

  // 取景框在原图坐标系下的尺寸；用 min 兜一道，避免浮点误差让它多出零点几个像素而采到界外
  const width = Math.min(srcW, frameW / scale)
  const height = Math.min(srcH, frameH / scale)

  return {
    x: Math.max(0, Math.min(srcW - width, -x / scale)),
    y: Math.max(0, Math.min(srcH - height, -y / scale)),
    width,
    height
  }
}

/**
 * 把原图上的某块区域画进新画布，输出一个可直接上传的 File。
 *
 * 用 WebP：与上传前的压缩保持一致（体积小且保留透明通道）。
 * 与压缩不同的地方是这里**必须**重编码 —— 裁剪本来就要产生新像素，无从「原样放行」。
 * 入参 source 可以是 <img> 元素（草图就是同一个 <img>，所以产物和用户看到的完全一致）。
 */
export async function cropToFile(source, region, baseName = 'cover') {
  const width = Math.max(1, Math.round(region.width))
  const height = Math.max(1, Math.round(region.height))

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height

  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('浏览器未提供 2d 画布')

  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(source, region.x, region.y, region.width, region.height, 0, 0, width, height)

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', 0.9))
  if (!blob) throw new Error('裁剪结果编码失败')

  const base = String(baseName || 'cover').replace(/\.[^./\\]+$/, '') || 'cover'
  return new File([blob], `${base}.webp`, { type: 'image/webp' })
}

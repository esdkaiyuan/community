import request from './request'

// 上传封面（multipart/form-data）。
// 注意：不要手动设置 Content-Type —— 浏览器需要自己补上带 boundary 的分隔符，
// 手写 `multipart/form-data` 会丢掉 boundary，后端解析出空文件。
export const uploadCover = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/uploads/cover', form)
}

// 与后端保持一致的上传约束，供表单做上传前的即时校验（避免白传 5MB 再被拒）
export const COVER_MAX_BYTES = 5 * 1024 * 1024
export const COVER_ACCEPT = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

// 统一响应格式：{ code, message, data? }，code 与 HTTP 状态码保持一致
exports.ok = (res, data = null, message = '操作成功') => {
  res.json({ code: 200, message, data })
}

exports.created = (res, data = null, message = '创建成功') => {
  res.status(201).json({ code: 201, message, data })
}

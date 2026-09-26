// 包装 async 控制器：异常自动交给全局错误处理中间件，控制器不再手写 try/catch
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next)
}

module.exports = asyncHandler

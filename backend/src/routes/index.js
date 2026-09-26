const express = require('express')
const router = express.Router()
const userRoutes = require('./user.routes')
const projectRoutes = require('./project.routes')
const categoryRoutes = require('./category.routes')

router.use('/users', userRoutes)
router.use('/projects', projectRoutes)
router.use('/categories', categoryRoutes)

// 健康检查
router.get('/health', (_req, res) => {
  res.json({ code: 200, message: 'ok', data: { status: 'up', time: new Date().toISOString() } })
})

module.exports = router

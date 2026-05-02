const express = require('express')
const router = express.Router()
const userRoutes = require('./user.routes')
const projectRoutes = require('./project.routes')
const categoryRoutes = require('./categoryRoutes')

router.use('/users', userRoutes)
router.use('/projects', projectRoutes)
router.use('/categories', categoryRoutes)

module.exports = router

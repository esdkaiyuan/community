const express = require('express')
const router = express.Router()
const uploadController = require('../controllers/upload.controller')
const { uploadCover } = require('../middleware/upload')
const { auth } = require('../middleware/auth')
const { uploadLimiter } = require('../middleware/rateLimiter')

// 上传必须登录：匿名上传等于给陌生人开了一个写磁盘的入口
router.use(auth)

router.post('/cover', uploadLimiter, uploadCover, uploadController.uploadCover)

module.exports = router

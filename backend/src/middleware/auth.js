const { verifyToken } = require('../utils/jwt')

const auth = (req, res, next) => {
  try {
    const authHeader = req.headers.authorization
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ 
        success: false, 
        message: '未提供认证令牌' 
      })
    }
    
    const token = authHeader.substring(7)
    const decoded = verifyToken(token)
    
    req.user = { userId: decoded.userId }
    next()
  } catch (error) {
    return res.status(401).json({ 
      success: false, 
      message: '认证令牌无效或已过期' 
    })
  }
}

module.exports = auth

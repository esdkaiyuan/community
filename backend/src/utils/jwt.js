const jwt = require('jsonwebtoken')
const env = require('../config/env')

const generateToken = (userId) =>
  jwt.sign({ userId }, env.jwt.secret, { expiresIn: env.jwt.expiresIn })

const verifyToken = (token) => jwt.verify(token, env.jwt.secret)

module.exports = { generateToken, verifyToken }

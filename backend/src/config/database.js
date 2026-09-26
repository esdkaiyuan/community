const { Sequelize } = require('sequelize')
const env = require('./env')

const sequelize = new Sequelize(env.db.name, env.db.user, env.db.password, {
  host: env.db.host,
  port: env.db.port,
  dialect: 'mysql',
  logging: env.nodeEnv === 'development' ? (msg) => console.debug('[sql]', msg) : false,
  pool: {
    max: 5,
    min: 0,
    acquire: 30000,
    idle: 10000
  }
})

module.exports = sequelize

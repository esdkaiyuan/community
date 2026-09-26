// 极简结构化日志：统一前缀与级别，后续可无缝替换为 pino/winston
const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 }
const currentLevel = LEVELS[process.env.LOG_LEVEL] || (process.env.NODE_ENV === 'production' ? LEVELS.info : LEVELS.debug)

const emit = (level, tag, args) => {
  if (LEVELS[level] < currentLevel) return
  const prefix = `[${level.toUpperCase()}][${tag}]`
  if (level === 'error') console.error(prefix, ...args)
  else if (level === 'warn') console.warn(prefix, ...args)
  else console.log(prefix, ...args)
}

const createLogger = (tag) => ({
  debug: (...args) => emit('debug', tag, args),
  info: (...args) => emit('info', tag, args),
  warn: (...args) => emit('warn', tag, args),
  error: (...args) => emit('error', tag, args)
})

module.exports = createLogger

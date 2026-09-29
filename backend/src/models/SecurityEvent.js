const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')

// 安全事件（被拒的尝试）：与「操作日志」（activity_logs）刻意分开两张表。
//
// 为什么不合到 activity_logs 里 —— 它们的语义恰好相反：
//
//   activity_logs  记「谁**做成了**什么」。有明确身份（user_id），每条都是一个事实，
//                  用户自己在 /logs/me 里就能看到，可以逐条读。
//   本表           记「有人**尝试但没成功**」。**常常没有身份**（未登录、密码错、
//                  令牌是伪造的）—— 恰恰是这一点决定了它不能塞进上面那张表：
//                  上面那张的所有查询都是按 user_id 走的，而这些事件大多压根没有
//                  user_id；硬塞进去会变成一堆「无主的行」，还会把用户自己能看到的
//                  时间线灌满攻击者的噪音。
//
// 三条硬约束，都体现在字段上：
//
//   1. **绝不记密码**。任何形式的密码（明文 / 长度 / 哈希）都不进这张表。写入接口
//      的入参是白名单取值的（见 securityEvent.service），所以调用方多传什么都进不来。
//   2. **账号只存脱敏形态**（`account` 列）。安全事件的价值在于「看得出同一来源在反复
//      尝试」，不在于「把别人输错的邮箱完整抄一份存 365 天」（PII 面）。账号确实存在时
//      另有 `target_user_id` 做精确身份。
//   3. **聚合**（`fingerprint` + `occurrences` + `last_seen_at`）。暴力破解的本质就是
//      「同一来源对同一目标反复失败」，一条一行会瞬间把表撑成噪音洪水；按
//      fingerprint + 时间窗口合并成「一条带次数的行」，既能读出强度，又不会被淹没。
//      activity_logs 没有这三个列，也正因如此它不该承载这类事件。
//
// 与 activity_logs 一致的约定：**不建外键**。删号 / 删项目都要能带走证据 —— 那恰恰是
// 最需要留痕的场景。孤儿行对安全审计是特性，不是缺陷。
const SecurityEvent = sequelize.define(
  'SecurityEvent',
  {
    id: {
      type: DataTypes.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true
    },
    event: {
      type: DataTypes.STRING(40),
      allowNull: false,
      comment: '事件标识，取值受服务层白名单约束（auth.login.rejected 等）'
    },
    reason: {
      type: DataTypes.STRING(120),
      allowNull: false,
      comment: '被拒的原因（系统自己的文案，已净化；不含用户输入的原文）'
    },
    target_user_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true,
      comment:
        '被尝试的目标账号ID（仅当该账号确实存在）。⚠️ 语义与 activity_logs.user_id（操作者）相反：这里是「被瞄准的人」'
    },
    account: {
      type: DataTypes.STRING(80),
      allowNull: true,
      comment: '被尝试的账号标识，**已脱敏**（z***@e***.com / a***），不存明文邮箱'
    },
    ip: {
      type: DataTypes.STRING(45),
      allowNull: true,
      comment: '来源IP（IPv4/IPv6 通用长度）'
    },
    user_agent: {
      type: DataTypes.STRING(255),
      allowNull: true,
      comment: '客户端标识（已净化与截断）'
    },
    path: {
      type: DataTypes.STRING(120),
      allowNull: true,
      comment: '被访问的接口路径（不含 query，避免把敏感参数抄进日志）'
    },
    method: {
      type: DataTypes.STRING(10),
      allowNull: true,
      comment: 'HTTP 方法'
    },
    fingerprint: {
      type: DataTypes.STRING(64),
      allowNull: false,
      comment: '聚合键 sha256(event|ip|account|path)：窗口内同键只更新不新增'
    },
    occurrences: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: false,
      defaultValue: 1,
      comment: '窗口内被合并的尝试次数（首次为 1）'
    },
    last_seen_at: {
      // ⚠️ 线上列类型是 **TIMESTAMP**（不是 Sequelize 默认映射的 DATETIME），schema.sql 里有
      // 详细理由：Sequelize 把连接会话时区固定为 +00:00，写 DATETIME 会落一个裸 UTC 值，
      // 而 created_at 是时区感知的 —— 于是在 mysql CLI 里同一行两列差 8 小时，
      // 连 SQL 里 last_seen_at >= created_at 都会比错。统一成 TIMESTAMP 后任何会话都自洽。
      type: DataTypes.DATE,
      allowNull: false,
      comment: '最近一次发生时间（聚合时刷新，窗口按它计算）'
    }
  },
  {
    tableName: 'security_events',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
    indexes: [
      // 聚合查询：按 fingerprint + 时间窗口找「上一条」
      { fields: ['fingerprint', 'last_seen_at'] },
      // 三条取证路径：看某类事件、看某个来源、看针对某账号的尝试
      { fields: ['event', 'created_at'] },
      { fields: ['ip', 'created_at'] },
      { fields: ['target_user_id', 'last_seen_at'] }
    ]
  }
)

module.exports = SecurityEvent

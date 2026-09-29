const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')

// 操作日志（审计留痕）：记录「谁在什么时候对哪条内容做了什么」。
//
// 两个刻意的设计，都写在字段上：
//
//   1. **不建外键**。日志是证据，必须比它描述的对象活得久。而本仓库的删除链路是
//      `users → projects → project_comments` 一路 ON DELETE CASCADE —— 只要这里挂上
//      外键，注销一个账号就能把整条证据链一起抹掉，恰恰是最需要留痕的场景丢得最干净。
//      所以只存 id + 名称快照，不做引用完整性约束。
//      代价是可能出现「孤儿日志」（目标已不存在）。对审计来说这是特性不是缺陷。
//   2. **冗余胜过 JOIN**。这条表只写不常读、且从不参与业务查询，所以把 username、
//      project_id 这些信息摊平存下来，读取时不必回表，也让快照能反映「当时」的状态
//      （用户后来改名了，日志里仍是他动手时的名字）。
const ActivityLog = sequelize.define(
  'ActivityLog',
  {
    id: {
      type: DataTypes.INTEGER.UNSIGNED,
      primaryKey: true,
      autoIncrement: true
    },
    user_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true,
      comment: '操作者ID（无外键：用户被删除后日志仍需保留）'
    },
    username: {
      type: DataTypes.STRING(50),
      allowNull: true,
      comment: '操作者名称快照'
    },
    action: {
      type: DataTypes.STRING(32),
      allowNull: false,
      comment: '动作标识，取值受服务层白名单约束（project.create 等）'
    },
    target_type: {
      type: DataTypes.STRING(20),
      allowNull: false,
      comment: '目标类型：project / comment'
    },
    target_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true,
      comment: '目标ID'
    },
    project_id: {
      type: DataTypes.INTEGER.UNSIGNED,
      allowNull: true,
      comment: '所属项目ID（评论类日志用它可按项目聚合）'
    },
    summary: {
      type: DataTypes.STRING(255),
      allowNull: false,
      comment: '单行摘要（已净化：无换行/控制字符、已截断）'
    },
    detail: {
      type: DataTypes.JSON,
      allowNull: true,
      comment: '结构化附加信息（键受白名单约束，见 logSanitize.sanitizeDetail）'
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
    }
  },
  {
    tableName: 'activity_logs',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
    indexes: [
      // 三条查询路径各配一个：按人翻、按项目翻、按动作筛查
      { fields: ['user_id', 'created_at'] },
      { fields: ['project_id', 'created_at'] },
      { fields: ['action', 'created_at'] }
    ]
  }
)

module.exports = ActivityLog

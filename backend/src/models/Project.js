const { DataTypes } = require('sequelize')
const sequelize = require('../config/database')
const User = require('./User')
const Category = require('./Category')

const Project = sequelize.define('Project', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  title: {
    type: DataTypes.STRING(200),
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: false
  },
  cover_image: {
    type: DataTypes.STRING(255),
    allowNull: true
  },
  category_id: {
    type: DataTypes.INTEGER,
    allowNull: true
  },
  creator_id: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  status: {
    type: DataTypes.TINYINT,
    defaultValue: 0
  },
  // 仓库地址：线上有 10 个项目填了真实地址，此前模型没声明所以接口取不到（死列）。
  // 现接成真功能 —— 详情页展示「查看仓库」入口，无值时不渲染。
  repository_url: {
    type: DataTypes.STRING(255),
    allowNull: true
  },
  // 截止日期：线上 10 个项目有值且全部已过期。详情页据此显示「已截止」标记。
  end_date: {
    type: DataTypes.DATEONLY,
    allowNull: true
  },
  // 访问加密：none-公开；repo-仅仓库地址需要密码；project-整个项目需要密码。
  // 密码只存 bcrypt 哈希，明文绝不入库。
  lock_level: {
    type: DataTypes.STRING(16),
    allowNull: false,
    defaultValue: 'none'
  },
  lock_password_hash: {
    type: DataTypes.STRING(255),
    allowNull: true
  },
  // 唯一槽位：加密项目创建时写入 creator_id，取消加密/删除时置 NULL。
  // 用数据库唯一索引兜住并发 —— 只靠 count 预检查的话，两个并发发布能同时通过。
  lock_slot_user_id: {
    type: DataTypes.INTEGER,
    allowNull: true,
    unique: true
  },
  tags: {
    type: DataTypes.TEXT,
    allowNull: true,
    get() {
      const raw = this.getDataValue('tags')
      if (!raw) return []
      if (Array.isArray(raw)) return raw
      try {
        return JSON.parse(raw)
      } catch {
        return []
      }
    },
    set(val) {
      this.setDataValue('tags', typeof val === 'string' ? val : JSON.stringify(val || []))
    }
  },
  is_recommend: {
    type: DataTypes.TINYINT,
    defaultValue: 0
  },
  is_hot: {
    type: DataTypes.TINYINT,
    defaultValue: 0
  },
  // 管理员下架标记（与历史遗留的 status 刻意分开）：
  // status 在旧数据里恒为 0，语义不可靠；下架是管理台独有的状态，必须能被精确查询。
  is_hidden: {
    type: DataTypes.TINYINT,
    allowNull: false,
    defaultValue: 0
  },
  like_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  comment_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  participant_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  view_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  }
}, {
  tableName: 'projects',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at',
  deletedAt: 'deleted_at',
  paranoid: true
})

// 定义关联关系
Project.belongsTo(Category, { foreignKey: 'category_id', as: 'category' })
Project.belongsTo(User, { foreignKey: 'creator_id', as: 'creator' })
Category.hasMany(Project, { foreignKey: 'category_id' })
User.hasMany(Project, { foreignKey: 'creator_id' })

module.exports = Project

# 共创社区平台 - 设计文档

## 项目概述

共创社区是一个面向项目协作的Web平台，用户可以发布项目、浏览他人项目、参与协作。平台采用现代化的设计风格，以卡片形式展示项目，提供清晰的分类导航和便捷的搜索功能。

## 技术栈

### 前端
- **框架**: Vue 3 (Composition API)
- **UI 组件库**: Element Plus
- **样式**: SCSS
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios

### 后端
- **运行环境**: Node.js
- **Web 框架**: Express
- **数据库**: MySQL
- **认证**: JWT (JSON Web Token)
- **ORM**: Sequelize 或 Knex.js

## 项目结构

```
community/
├── frontend/                    # Vue3 前端项目
│   ├── public/                  # 静态资源
│   ├── src/
│   │   ├── assets/              # 资源文件（图片、字体等）
│   │   ├── components/          # 公共组件
│   │   │   ├── Header/          # 顶部导航栏
│   │   │   ├── Sidebar/         # 左侧边栏
│   │   │   ├── ProjectCard/     # 项目卡片组件
│   │   │   ├── SearchBar/       # 搜索栏组件
│   │   │   ── ...
│   │   ├── views/               # 页面视图
│   │   │   ├── HomeView.vue     # 首页
│   │   │   ├── ProjectDetail.vue # 项目详情页
│   │   │   ├── PublishProject.vue # 发布项目页
│   │   │   ├── LoginView.vue    # 登录页
│   │   │   ├── RegisterView.vue # 注册页
│   │   │   └── ProfileView.vue  # 个人中心
│   │   ├── router/              # 路由配置
│   │   │   └── index.js
│   │   ├── store/               # Pinia 状态管理
│   │   │   ├── modules/
│   │   │   │   ├── user.js      # 用户状态
│   │   │   │   ├── project.js   # 项目状态
│   │   │   │   ── category.js  # 分类状态
│   │   │   └── index.js
│   │   ├── api/                 # API 接口封装
│   │   │   ├── request.js       # Axios 实例配置
│   │   │   ├── user.js          # 用户相关 API
│   │   │   ├── project.js       # 项目相关 API
│   │   │   └── category.js      # 分类相关 API
│   │   ├── styles/              # 全局样式
│   │   │   ├── variables.scss   # SCSS 变量
│   │   │   ├── global.scss      # 全局样式
│   │   │   └── mixins.scss      # SCSS mixins
│   │   ├── utils/               # 工具函数
│   │   ├── App.vue              # 根组件
│   │   └── main.js              # 入口文件
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── backend/                     # Node.js 后端项目
│   ├── src/
│   │   ├── config/              # 配置文件
│   │   │   ├── database.js      # 数据库配置
│   │   │   └── index.js         # 应用配置
│   │   ├── routes/              # 路由定义
│   │   │   ├── index.js         # 路由入口
│   │   │   ├── user.routes.js   # 用户路由
│   │   │   ├── project.routes.js # 项目路由
│   │   │   ── category.routes.js # 分类路由
│   │   ├── controllers/         # 控制器（业务逻辑）
│   │   │   ├── user.controller.js
│   │   │   ├── project.controller.js
│   │   │   └── category.controller.js
│   │   ├── models/              # 数据模型
│   │   │   ├── User.js
│   │   │   ├── Project.js
│   │   │   ├── Category.js
│   │   │   ├── Tag.js
│   │   │   └── Participant.js
│   │   ├── middleware/          # 中间件
│   │   │   ├── auth.js          # 认证中间件
│   │   │   ├── validate.js      # 验证中间件
│   │   │   └── errorHandler.js  # 错误处理
│   │   ├── services/            # 业务服务层
│   │   │   ├── user.service.js
│   │   │   ├── project.service.js
│   │   │   └── category.service.js
│   │   └── utils/               # 工具函数
│   ├── migrations/              # 数据库迁移脚本
│   ├── seeds/                   # 种子数据
│   ├── package.json
│   └── server.js                # 服务器入口
│
└── database/                    # 数据库相关
    ├── schema.sql               # 数据库表结构
    └── init.sql                 # 初始化数据
```

## 数据库设计

### users 表（用户表）
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar VARCHAR(255),
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### projects 表（项目表）
```sql
CREATE TABLE projects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    cover_image VARCHAR(255),
    category_id INT,
    creator_id INT,
    status ENUM('draft', 'published', 'completed', 'archived') DEFAULT 'published',
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    participants_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (creator_id) REFERENCES users(id)
);
```

### categories 表（分类表）
```sql
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(50),
    description TEXT,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### tags 表（标签表）
```sql
CREATE TABLE tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### project_tags 表（项目标签关联表）
```sql
CREATE TABLE project_tags (
    project_id INT,
    tag_id INT,
    PRIMARY KEY (project_id, tag_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

### project_participants 表（项目参与者表）
```sql
CREATE TABLE project_participants (
    project_id INT,
    user_id INT,
    role ENUM('creator', 'member', 'observer') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## 前端组件设计

### 1. Header 组件（顶部导航栏）
**位置**: 固定在页面顶部
**功能**:
- Logo 和品牌名称
- 搜索框（居中）
- 登录/注册按钮（右上角）
- 用户头像和下拉菜单（已登录状态）

**Props**:
- `searchQuery`: 当前搜索关键词
- `isLoggedIn`: 登录状态
- `userInfo`: 用户信息

**Events**:
- `@search`: 触发搜索
- `@login`: 打开登录弹窗
- `@logout`: 用户登出

### 2. Sidebar 组件（左侧边栏）
**位置**: 页面左侧固定
**功能**:
- 主导航菜单（首页、发现项目、热门项目等）
- 分类列表（技术开发、设计创意、产品/运营等）
- "发布你的项目" 区块
- "发布项目" 按钮

**Props**:
- `activeMenu`: 当前激活的菜单项
- `categories`: 分类列表

**Events**:
- `@menu-click`: 菜单项点击
- `@category-click`: 分类点击
- `@publish-click`: 发布项目按钮点击

### 3. ProjectCard 组件（项目卡片）
**位置**: 首页内容区，网格布局
**功能**:
- 项目封面图片
- 推荐/热门标签
- 项目标题和描述
- 标签列表
- 参与人数、点赞数、评论数

**Props**:
- `project`: 项目对象
  - `title`: 标题
  - `description`: 描述
  - `coverImage`: 封面图
  - `tags`: 标签数组
  - `participantsCount`: 参与人数
  - `likesCount`: 点赞数
  - `commentsCount`: 评论数
  - `badge`: 徽章（推荐/热门）

**Events**:
- `@click`: 卡片点击，跳转到详情页

### 4. SearchBar 组件（搜索栏）
**位置**: Header 内部
**功能**:
- 搜索输入框
- 搜索图标按钮
- 搜索建议（可选）

**Props**:
- `placeholder`: 占位文本
- `value`: 当前搜索值

**Events**:
- `@search`: 触发搜索
- `@input`: 输入变化

### 5. ProjectGrid 组件（项目网格）
**位置**: 首页主内容区
**功能**:
- 响应式网格布局展示项目卡片
- 筛选和排序控件
- 加载更多/分页

**Props**:
- `projects`: 项目列表
- `filters`: 筛选条件
- `sortBy`: 排序方式

**Events**:
- `@filter-change`: 筛选条件变化
- `@sort-change`: 排序方式变化
- `@load-more`: 加载更多

## 后端 API 设计

### 用户相关 API

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/users/register | 用户注册 | 否 |
| POST | /api/users/login | 用户登录 | 否 |
| GET | /api/users/profile | 获取用户信息 | 是 |
| PUT | /api/users/profile | 更新用户信息 | 是 |

### 项目相关 API

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/projects | 获取项目列表（支持分页、筛选、搜索） | 否 |
| GET | /api/projects/:id | 获取项目详情 | 否 |
| POST | /api/projects | 创建项目 | 是 |
| PUT | /api/projects/:id | 更新项目 | 是 |
| DELETE | /api/projects/:id | 删除项目 | 是 |
| POST | /api/projects/:id/like | 点赞项目 | 是 |
| POST | /api/projects/:id/participate | 参与项目 | 是 |

### 分类相关 API

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/categories | 获取分类列表 | 否 |

## 页面路由设计

| 路径 | 组件 | 描述 | 认证 |
|------|------|------|------|
| / | HomeView | 首页（项目列表） | 否 |
| /project/:id | ProjectDetail | 项目详情页 | 否 |
| /publish | PublishProject | 发布项目页 | 是 |
| /login | LoginView | 登录页 | 否 |
| /register | RegisterView | 注册页 | 否 |
| /profile | ProfileView | 个人中心 | 是 |

## 样式设计

### 颜色主题
- **主色**: #6366F1 (紫色) - 用于按钮、链接、高亮
- **辅助色**: #F59E0B (橙色) - 用于徽章、点赞
- **背景色**: #F8F9FA - 页面背景
- **卡片背景**: #FFFFFF - 卡片背景
- **文字主色**: #1F2937 - 主要文字
- **文字辅色**: #6B7280 - 次要文字
- **边框色**: #E5E7EB - 边框和分隔线

### 布局规范
- **Header 高度**: 64px
- **Sidebar 宽度**: 220px
- **内容区最大宽度**: 1280px
- **卡片圆角**: 12px
- **卡片阴影**: 0 2px 8px rgba(0,0,0,0.08)
- **间距系统**: 8px 基准（8, 16, 24, 32, 48, 64）

### 响应式设计
- **桌面端**: > 1024px（完整布局）
- **平板端**: 768px - 1024px（侧栏可折叠）
- **移动端**: < 768px（单列布局，汉堡菜单）

## 安全考虑

1. **密码安全**: 后端使用 bcrypt 对密码进行哈希加密
2. **JWT 认证**: 登录成功后返回 JWT token，前端存储在 localStorage
3. **请求拦截**: Axios 拦截器自动在请求头添加 token
4. **路由守卫**: Vue Router 导航守卫保护需要认证的页面
5. **CORS 配置**: 后端配置 CORS 允许前端域名访问
6. **SQL 注入防护**: 使用 ORM 或参数化查询
7. **XSS 防护**: 对用户输入进行转义处理

## 性能优化

1. **图片优化**: 使用合适的图片格式（WebP），懒加载
2. **代码分割**: Vue Router 路由懒加载
3. **API 缓存**: 对不经常变化的数据（如分类列表）进行缓存
4. **分页加载**: 项目列表使用分页或无限滚动
5. **搜索优化**: 防抖处理，避免频繁请求

## 开发计划

### Phase 1: 基础架构搭建
- [ ] 初始化前端项目（Vite + Vue3）
- [ ] 安装和配置 Element Plus
- [ ] 初始化后端项目（Express）
- [ ] 配置 MySQL 数据库
- [ ] 创建数据库表和初始数据

### Phase 2: 核心功能开发
- [ ] Header 组件开发
- [ ] Sidebar 组件开发
- [ ] ProjectCard 组件开发
- [ ] 首页布局和样式
- [ ] 后端项目 CRUD API
- [ ] 前端项目列表对接 API

### Phase 3: 用户系统
- [ ] 用户注册/登录功能
- [ ] JWT 认证实现
- [ ] 路由守卫配置
- [ ] 个人中心页面

### Phase 4: 增强功能
- [ ] 项目详情页
- [ ] 发布项目功能
- [ ] 搜索和筛选功能
- [ ] 点赞和参与功能
- [ ] 响应式适配

### Phase 5: 测试和优化
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化
- [ ] Bug 修复
- [ ] 部署准备

## 注意事项

1. 所有 API 请求需要处理加载状态和错误状态
2. 表单验证需要前后端双重验证
3. 图片上传需要考虑文件大小和格式限制
4. 需要设计友好的空状态页面（无项目、无搜索结果等）
5. 考虑 SEO 优化（项目详情页可能需要 SSR，可作为后续优化）

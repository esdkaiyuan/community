# 共创社区平台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个全栈共创社区平台，用户可以在平台发布项目、浏览项目、参与协作，前端使用 Vue3 + Element Plus，后端使用 Node.js + Express，数据库使用 MySQL。

**Architecture:** 前后端分离架构，前端通过 Vite 构建，后端提供 RESTful API，通过 JWT 实现用户认证，使用 Axios 进行 HTTP 通信。

**Tech Stack:** 
- 前端: Vue 3, Vite, Element Plus, Pinia, Vue Router 4, Axios, SCSS
- 后端: Node.js, Express, MySQL, Sequelize, bcrypt, JWT
- 数据库: MySQL 8.0+

---

## 文件结构规划

### 前端文件
```
frontend/
├── src/
│   ├── api/
│   │   ├── request.js           # Axios 实例配置
│   │   ├── user.js              # 用户相关 API
│   │   ├── project.js           # 项目相关 API
│   │   └── category.js          # 分类相关 API
│   ├── components/
│   │   ├── Header.vue           # 顶部导航栏
│   │   ├── Sidebar.vue          # 左侧边栏
│   │   ├── ProjectCard.vue      # 项目卡片
│   │   ├── SearchBar.vue        # 搜索栏
│   │   └── ProjectGrid.vue      # 项目网格
│   ├── views/
│   │   ├── HomeView.vue         # 首页
│   │   ├── ProjectDetail.vue    # 项目详情页
│   │   ├── PublishProject.vue   # 发布项目页
│   │   ├── LoginView.vue        # 登录页
│   │   ├── RegisterView.vue     # 注册页
│   │   └── ProfileView.vue      # 个人中心
│   ├── router/
│   │   └── index.js             # 路由配置
│   ├── store/
│   │   ├── modules/
│   │   │   ├── user.js
│   │   │   ├── project.js
│   │   │   └── category.js
│   │   └── index.js
│   ├── styles/
│   │   ├── variables.scss
│   │   ├── global.scss
│   │   └── mixins.scss
│   ├── App.vue
│   └── main.js
```

### 后端文件
```
backend/
── src/
│   ├── config/
│   │   ├── database.js          # 数据库配置
│   │   └── index.js             # 应用配置
│   ├── models/
│   │   ├── User.js
│   │   ├── Project.js
│   │   ├── Category.js
│   │   ├── Tag.js
│   │   ├── ProjectTag.js
│   │   └── ProjectParticipant.js
│   ├── middleware/
│   │   ├── auth.js              # JWT 认证中间件
│   │   └── errorHandler.js      # 错误处理中间件
│   ├── routes/
│   │   ├── index.js             # 路由入口
│   │   ├── user.routes.js
│   │   ├── project.routes.js
│   │   └── category.routes.js
│   ├── controllers/
│   │   ├── user.controller.js
│   │   ├── project.controller.js
│   │   └── category.controller.js
│   ── utils/
│       ├── jwt.js               # JWT 工具
│       └── validator.js         # 数据验证工具
── database/
│   ├── schema.sql               # 数据库建表脚本
│   ── seed.js                  # 种子数据
└── server.js
```

---

## 第一阶段：项目初始化

### Task 1: 初始化前端项目

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`

- [ ] **Step 1: 创建前端项目结构**

在 `community` 目录下执行：
```bash
cd "d:\treai项目\community"
npm create vite@latest frontend -- --template vue
```

- [ ] **Step 2: 安装核心依赖**

```bash
cd frontend
npm install element-plus pinia vue-router@4 axios
npm install -D sass
```

- [ ] **Step 3: 配置 Vite**

修改 `frontend/vite.config.js`:
```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 4: 验证项目启动**

```bash
npm run dev
```
Expected: 开发服务器在 http://localhost:3000 启动成功

- [ ] **Step 5: 提交**

```bash
git add frontend/
git commit -m "feat: 初始化前端项目"
```

---

### Task 2: 初始化后端项目

**Files:**
- Create: `backend/package.json`
- Create: `backend/server.js`
- Create: `backend/.env`

- [ ] **Step 1: 创建后端项目**

```bash
cd "d:\treai项目\community"
mkdir backend
cd backend
npm init -y
npm install express mysql2 sequelize bcryptjs jsonwebtoken dotenv cors
npm install -D nodemon
```

- [ ] **Step 2: 创建 .env 配置文件**

在 `backend/.env` 中添加：
```env
PORT=5000
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=community_platform
JWT_SECRET=your_jwt_secret_key_change_this
JWT_EXPIRES_IN=7d
```

- [ ] **Step 3: 配置 package.json 脚本**

修改 `backend/package.json`:
```json
{
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  }
}
```

- [ ] **Step 4: 创建 server.js 入口文件**

在 `backend/server.js` 中添加：
```javascript
require('dotenv').config()
const express = require('express')
const cors = require('cors')

const app = express()

// 中间件
app.use(cors())
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// 路由
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Server is running' })
})

// 启动服务器
const PORT = process.env.PORT || 5000
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`)
})
```

- [ ] **Step 5: 测试后端启动**

```bash
npm run dev
```
Expected: 服务器在 http://localhost:5000 启动，访问 /api/health 返回 {status: "ok"}

- [ ] **Step 6: 提交**

```bash
git add backend/
git commit -m "feat: 初始化后端项目"
```

---

### Task 3: 创建数据库和表结构

**Files:**
- Create: `backend/database/schema.sql`
- Create: `backend/database/seed.js`

- [ ] **Step 1: 创建数据库建表脚本**

在 `backend/database/schema.sql` 中添加：
```sql
CREATE DATABASE IF NOT EXISTS community_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE community_platform;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar VARCHAR(255) DEFAULT NULL,
    bio TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 分类表
CREATE TABLE IF NOT EXISTS categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(50) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    cover_image VARCHAR(255) DEFAULT NULL,
    category_id INT DEFAULT NULL,
    creator_id INT NOT NULL,
    status ENUM('draft', 'published', 'completed', 'archived') DEFAULT 'published',
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    participants_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目标签关联表
CREATE TABLE IF NOT EXISTS project_tags (
    project_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (project_id, tag_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 项目参与者表
CREATE TABLE IF NOT EXISTS project_participants (
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('creator', 'member', 'observer') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

- [ ] **Step 2: 创建种子数据脚本**

在 `backend/database/seed.js` 中添加完整种子数据（包含分类、用户、项目、标签等模拟数据）

- [ ] **Step 3: 执行数据库脚本**

```bash
mysql -u root -p < backend/database/schema.sql
```

- [ ] **Step 4: 提交**

```bash
git add backend/database/
git commit -m "feat: 创建数据库表结构和种子数据"
```

---

## 第二阶段：后端核心功能开发

### Task 4: 配置数据库连接和模型

**Files:**
- Create: `backend/src/config/database.js`
- Create: `backend/src/models/User.js`
- Create: `backend/src/models/Project.js`
- Create: `backend/src/models/Category.js`
- Create: `backend/src/models/Tag.js`
- Create: `backend/src/models/ProjectTag.js`
- Create: `backend/src/models/ProjectParticipant.js`
- Create: `backend/src/models/index.js`

- [ ] **Step 1: 创建数据库配置**

在 `backend/src/config/database.js` 中配置 Sequelize 连接

- [ ] **Step 2: 创建所有数据模型**

依次创建各个模型文件，定义表结构和关联关系

- [ ] **Step 3: 测试数据库连接**

创建测试脚本验证连接是否成功

```bash
node backend/src/models/index.js
```
Expected: 输出 "Database connected successfully"

- [ ] **Step 4: 提交**

```bash
git add backend/src/config/ backend/src/models/
git commit -m "feat: 配置数据库连接和数据模型"
```

---

### Task 5: 实现用户认证功能

**Files:**
- Create: `backend/src/utils/jwt.js`
- Create: `backend/src/middleware/auth.js`
- Create: `backend/src/controllers/user.controller.js`
- Create: `backend/src/routes/user.routes.js`
- Modify: `backend/src/routes/index.js`

- [ ] **Step 1: 创建 JWT 工具函数**

在 `backend/src/utils/jwt.js` 中实现：
```javascript
const jwt = require('jsonwebtoken')

const generateToken = (userId) => {
  return jwt.sign(
    { userId },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRES_IN }
  )
}

const verifyToken = (token) => {
  return jwt.verify(token, process.env.JWT_SECRET)
}

module.exports = { generateToken, verifyToken }
```

- [ ] **Step 2: 创建认证中间件**

在 `backend/src/middleware/auth.js` 中实现 JWT 验证逻辑

- [ ] **Step 3: 实现用户控制器**

在 `backend/src/controllers/user.controller.js` 中实现注册、登录、获取用户信息等接口

- [ ] **Step 4: 创建路由**

在 `backend/src/routes/user.routes.js` 中定义用户相关路由

- [ ] **Step 5: 测试用户注册和登录**

```bash
curl -X POST http://localhost:5000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'
```
Expected: 返回用户信息和 token

- [ ] **Step 6: 提交**

```bash
git add backend/src/utils/jwt.js backend/src/middleware/auth.js backend/src/controllers/user.controller.js backend/src/routes/user.routes.js
git commit -m "feat: 实现用户认证功能"
```

---

### Task 6: 实现项目 CRUD 功能

**Files:**
- Create: `backend/src/controllers/project.controller.js`
- Create: `backend/src/routes/project.routes.js`
- Modify: `backend/src/routes/index.js`

- [ ] **Step 1: 实现项目控制器**

在 `backend/src/controllers/project.controller.js` 中实现：
- `getProjects`: 获取项目列表（支持分页、筛选、搜索）
- `getProjectById`: 获取项目详情
- `createProject`: 创建项目
- `updateProject`: 更新项目
- `deleteProject`: 删除项目
- `likeProject`: 点赞项目
- `participateProject`: 参与项目

- [ ] **Step 2: 创建项目路由**

在 `backend/src/routes/project.routes.js` 中定义所有项目相关路由

- [ ] **Step 3: 测试项目创建**

```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"title":"Test Project","description":"A test project","categoryId":1}'
```
Expected: 返回创建的项目信息

- [ ] **Step 4: 测试项目列表查询**

```bash
curl http://localhost:5000/api/projects
```
Expected: 返回项目列表（包含分页信息）

- [ ] **Step 5: 提交**

```bash
git add backend/src/controllers/project.controller.js backend/src/routes/project.routes.js
git commit -m "feat: 实现项目 CRUD 功能"
```

---

### Task 7: 实现分类功能

**Files:**
- Create: `backend/src/controllers/category.controller.js`
- Create: `backend/src/routes/category.routes.js`
- Modify: `backend/src/routes/index.js`

- [ ] **Step 1: 实现分类控制器**

实现获取分类列表、获取分类详情等接口

- [ ] **Step 2: 创建分类路由**

定义分类相关路由

- [ ] **Step 3: 测试分类查询**

```bash
curl http://localhost:5000/api/categories
```
Expected: 返回所有分类列表

- [ ] **Step 4: 提交**

```bash
git add backend/src/controllers/category.controller.js backend/src/routes/category.routes.js
git commit -m "feat: 实现分类功能"
```

---

## 第三阶段：前端基础组件开发

### Task 8: 配置前端基础环境

**Files:**
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/styles/variables.scss`
- Create: `frontend/src/styles/global.scss`
- Create: `frontend/src/api/request.js`

- [ ] **Step 1: 配置 Element Plus**

修改 `frontend/src/main.js`:
```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 2: 创建全局样式**

在 `frontend/src/styles/variables.scss` 中定义颜色变量：
```scss
$primary-color: #6366F1;
$secondary-color: #F59E0B;
$bg-color: #F8F9FA;
$card-bg: #FFFFFF;
$text-primary: #1F2937;
$text-secondary: #6B7280;
$border-color: #E5E7EB;
```

- [ ] **Step 3: 配置 Axios 实例**

在 `frontend/src/api/request.js` 中创建带拦截器的 Axios 实例

- [ ] **Step 4: 提交**

```bash
git add frontend/src/main.js frontend/src/App.vue frontend/src/styles/ frontend/src/api/
git commit -m "feat: 配置前端基础环境"
```

---

### Task 9: 开发 Header 组件

**Files:**
- Create: `frontend/src/components/Header.vue`

- [ ] **Step 1: 实现 Header 组件**

在 `frontend/src/components/Header.vue` 中实现：
- Logo 和品牌名称
- 搜索框（居中）
- 登录/注册按钮
- 用户头像下拉菜单（登录状态）

完整组件代码包含模板、样式和逻辑

- [ ] **Step 2: 在 App.vue 中集成 Header**

修改 `frontend/src/App.vue` 添加 Header 组件

- [ ] **Step 3: 截图验证**

启动前端开发服务器，截图检查 Header 显示效果是否符合设计图

```bash
cd frontend
npm run dev
```
在浏览器中打开 http://localhost:3000，检查 Header 组件

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/Header.vue frontend/src/App.vue
git commit -m "feat: 开发 Header 组件"
```

---

### Task 10: 开发 Sidebar 组件

**Files:**
- Create: `frontend/src/components/Sidebar.vue`

- [ ] **Step 1: 实现 Sidebar 组件**

在 `frontend/src/components/Sidebar.vue` 中实现：
- 主导航菜单（首页、发现项目、热门项目等）
- 分类列表（从 API 加载）
- "发布你的项目" 区块
- "发布项目" 按钮

- [ ] **Step 2: 在 App.vue 中集成 Sidebar**

修改布局，添加 Sidebar 组件

- [ ] **Step 3: 截图验证**

在浏览器中检查 Sidebar 显示效果和样式

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/Sidebar.vue
git commit -m "feat: 开发 Sidebar 组件"
```

---

### Task 11: 开发 ProjectCard 组件

**Files:**
- Create: `frontend/src/components/ProjectCard.vue`

- [ ] **Step 1: 实现 ProjectCard 组件**

在 `frontend/src/components/ProjectCard.vue` 中实现项目卡片：
- 封面图片
- 推荐/热门标签
- 标题和描述
- 标签列表
- 参与人数、点赞数、评论数

- [ ] **Step 2: 创建测试数据验证组件**

在临时页面中使用模拟数据测试 ProjectCard 渲染效果

- [ ] **Step 3: 截图验证**

截图检查 ProjectCard 样式是否符合设计图要求

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/ProjectCard.vue
git commit -m "feat: 开发 ProjectCard 组件"
```

---

### Task 12: 开发 ProjectGrid 组件

**Files:**
- Create: `frontend/src/components/ProjectGrid.vue`

- [ ] **Step 1: 实现 ProjectGrid 组件**

在 `frontend/src/components/ProjectGrid.vue` 中实现：
- 响应式网格布局
- 筛选和排序控件
- 加载更多功能
- 集成 ProjectCard 组件

- [ ] **Step 2: 截图验证**

检查网格布局在不同屏幕尺寸下的表现

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ProjectGrid.vue
git commit -m "feat: 开发 ProjectGrid 组件"
```

---

## 第四阶段：页面开发与集成

### Task 13: 配置路由和状态管理

**Files:**
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/store/index.js`
- Create: `frontend/src/store/modules/user.js`
- Create: `frontend/src/store/modules/project.js`
- Create: `frontend/src/store/modules/category.js`

- [ ] **Step 1: 配置路由**

在 `frontend/src/router/index.js` 中定义所有页面路由，包括路由守卫

- [ ] **Step 2: 创建 Pinia Store**

创建 user、project、category 三个状态管理模块

- [ ] **Step 3: 测试路由跳转**

创建测试页面验证路由配置正确

- [ ] **Step 4: 提交**

```bash
git add frontend/src/router/ frontend/src/store/
git commit -m "feat: 配置路由和状态管理"
```

---

### Task 14: 开发首页

**Files:**
- Create: `frontend/src/views/HomeView.vue`
- Create: `frontend/src/api/project.js`
- Create: `frontend/src/api/category.js`

- [ ] **Step 1: 创建 API 接口**

在 `frontend/src/api/project.js` 和 `frontend/src/api/category.js` 中封装项目相关 API 调用

- [ ] **Step 2: 实现首页**

在 `frontend/src/views/HomeView.vue` 中集成：
- Header 组件
- Sidebar 组件
- ProjectGrid 组件
- 搜索和筛选功能

- [ ] **Step 3: 对接后端 API**

将模拟数据替换为真实 API 调用

- [ ] **Step 4: 截图验证**

完整截图检查首页效果，与设计图对比

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/HomeView.vue frontend/src/api/
git commit -m "feat: 开发首页"
```

---

### Task 15: 开发登录/注册页面

**Files:**
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/RegisterView.vue`
- Create: `frontend/src/api/user.js`

- [ ] **Step 1: 实现登录页面**

在 `frontend/src/views/LoginView.vue` 中实现登录表单和逻辑

- [ ] **Step 2: 实现注册页面**

在 `frontend/src/views/RegisterView.vue` 中实现注册表单和逻辑

- [ ] **Step 3: 测试登录注册流程**

完整测试注册 -> 登录 -> 获取用户信息的流程

- [ ] **Step 4: 截图验证**

检查登录和注册页面样式

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/LoginView.vue frontend/src/views/RegisterView.vue frontend/src/api/user.js
git commit -m "feat: 开发登录注册页面"
```

---

### Task 16: 开发项目详情页

**Files:**
- Create: `frontend/src/views/ProjectDetail.vue`

- [ ] **Step 1: 实现项目详情页**

显示项目完整信息、参与者列表、评论区等

- [ ] **Step 2: 截图验证**

检查详情页布局和内容展示

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/ProjectDetail.vue
git commit -m "feat: 开发项目详情页"
```

---

### Task 17: 开发发布项目页面

**Files:**
- Create: `frontend/src/views/PublishProject.vue`

- [ ] **Step 1: 实现发布项目表单**

包含标题、描述、分类选择、封面上传、标签输入等字段

- [ ] **Step 2: 实现表单验证和提交**

- [ ] **Step 3: 截图验证**

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/PublishProject.vue
git commit -m "feat: 开发发布项目页面"
```

---

## 第五阶段：功能完善与测试

### Task 18: 实现搜索和筛选功能

**Files:**
- Modify: `frontend/src/views/HomeView.vue`
- Modify: `frontend/src/components/Sidebar.vue`
- Modify: `backend/src/controllers/project.controller.js`

- [ ] **Step 1: 前端搜索功能**

实现搜索框输入、防抖处理、API 调用

- [ ] **Step 2: 前端筛选功能**

实现分类筛选、排序方式选择

- [ ] **Step 3: 后端搜索接口**

完善项目列表查询，支持关键词搜索、分类筛选、排序

- [ ] **Step 4: 集成测试**

测试搜索和筛选功能的完整流程

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: 实现搜索和筛选功能"
```

---

### Task 19: 实现点赞和参与功能

**Files:**
- Modify: `frontend/src/components/ProjectCard.vue`
- Modify: `frontend/src/views/ProjectDetail.vue`
- Modify: `backend/src/controllers/project.controller.js`

- [ ] **Step 1: 后端点赞和参与接口**

实现点赞和参与项目的后端逻辑

- [ ] **Step 2: 前端交互**

在卡片和详情页添加点赞和参与按钮

- [ ] **Step 3: 测试功能**

测试点赞和参与的完整流程

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: 实现点赞和参与功能"
```

---

### Task 20: 响应式适配

**Files:**
- Modify: `frontend/src/styles/global.scss`
- Modify: `frontend/src/components/Header.vue`
- Modify: `frontend/src/components/Sidebar.vue`
- Modify: `frontend/src/components/ProjectGrid.vue`

- [ ] **Step 1: 平板端适配 (768px - 1024px)**

侧栏可折叠，调整布局

- [ ] **Step 2: 移动端适配 (< 768px)**

单列布局，汉堡菜单，优化触摸交互

- [ ] **Step 3: 多设备测试**

在不同屏幕尺寸下测试页面显示

- [ ] **Step 4: 截图验证**

截图记录各断点的显示效果

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: 响应式适配"
```

---

### Task 21: 错误处理和加载状态

**Files:**
- Modify: `frontend/src/api/request.js`
- Modify: `frontend/src/components/ProjectGrid.vue`
- Modify: 所有视图组件

- [ ] **Step 1: 完善 Axios 拦截器**

处理 401、403、500 等错误状态

- [ ] **Step 2: 添加加载状态**

在所有数据加载处添加 loading 效果

- [ ] **Step 3: 添加空状态处理**

无数据、无搜索结果等场景的友好提示

- [ ] **Step 4: 测试各种错误场景**

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: 完善错误处理和加载状态"
```

---

### Task 22: 最终测试与优化

**Files:**
- 全项目文件

- [ ] **Step 1: 完整功能测试**

测试所有功能的完整流程：
- 用户注册/登录
- 浏览项目列表
- 搜索和筛选项目
- 查看项目详情
- 发布新项目
- 点赞和参与项目
- 退出登录

- [ ] **Step 2: 性能优化**

- 路由懒加载
- 图片懒加载
- 代码分割
- API 请求优化

- [ ] **Step 3: 浏览器兼容性测试**

在 Chrome、Firefox、Edge 中测试

- [ ] **Step 4: 截图验证**

最终完整截图检查所有页面

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: 最终测试与优化"
```

---

## 完成标准

所有任务完成后，应该能够：
1. ✅ 前端在 http://localhost:3000 正常运行
2. ✅ 后端在 http://localhost:5000 正常运行
3. ✅ 用户可以注册、登录、退出
4. ✅ 首页展示项目卡片列表，支持搜索和筛选
5. ✅ 可以查看项目详情
6. ✅ 登录用户可以发布新项目
7. ✅ 可以点赞和参与项目
8. ✅ 页面在桌面端、平板端、移动端正常显示
9. ✅ 所有截图与设计图一致

---

## 注意事项

1. 每个 Task 完成后必须截图验证，确保视觉效果符合设计图
2. 遇到 API 错误时，检查后端日志和浏览器 Network 面板
3. 样式问题优先使用浏览器开发者工具调试
4. 数据库问题检查 MySQL 服务是否正常运行
5. 保持代码提交频率，每个小功能完成后立即提交
6. 使用 Element Plus 官方文档查阅组件用法：https://element-plus.org/

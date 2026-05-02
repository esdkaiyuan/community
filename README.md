# 共创社区平台 - 启动指南

## 前置要求

1. **Node.js** (v16+)
2. **MySQL** (v8.0+)
3. **npm** 或 **yarn**

## 快速开始

### 1. 配置数据库

#### 创建数据库
在 MySQL 中执行以下命令：

```sql
CREATE DATABASE community_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 修改数据库配置
编辑 `backend/.env` 文件，修改数据库密码：

```env
DB_PASSWORD=你的MySQL密码
```

### 2. 初始化数据库

在 MySQL 中执行数据库脚本：

```bash
mysql -u root -p community_platform < backend/database/schema.sql
mysql -u root -p community_platform < backend/database/seed.sql
```

或者手动执行 SQL 文件中的内容。

### 3. 安装依赖

```bash
# 后端
cd backend
npm install

# 前端
cd frontend
npm install
```

### 4. 启动服务

#### 启动后端（终端 1）
```bash
cd backend
npm run dev
```

后端服务将运行在 http://localhost:5000

#### 启动前端（终端 2）
```bash
cd frontend
npm run dev
```

前端服务将运行在 http://localhost:3000

### 5. 访问应用

打开浏览器访问 http://localhost:3000

## 功能说明

### 已完成的功能

✅ **前端功能**
- [x] 首页 - 项目列表展示（卡片形式）
- [x] 顶部导航栏 - Logo、搜索框、登录/注册
- [x] 左侧边栏 - 分类筛选
- [x] 项目卡片 - 封面、标题、描述、参与人数、点赞数
- [x] 登录/注册页面
- [x] 发布项目页面
- [x] 项目详情页面（基础版）
- [x] 响应式布局

✅ **后端功能**
- [x] 用户认证（JWT）
- [x] 用户注册/登录
- [x] 项目 CRUD
- [x] 分类列表
- [x] 点赞功能
- [x] 参与功能

### 待完善的功能

⏳ **需要进一步完善**
- [ ] 数据库连接测试和优化
- [ ] 项目详情页完整功能
- [ ] 搜索和筛选功能优化
- [ ] 图片上传功能
- [ ] 评论功能
- [ ] 实时通知

## 常见问题

### 1. 后端启动失败

**问题**: `Error: Cannot find module '../../config/database'`

**解决**: 确保所有模型文件的引用路径正确，应该是 `require('../config/database')`

### 2. 数据库连接失败

**问题**: `Access denied for user 'root'@'localhost'`

**解决**: 检查 `backend/.env` 文件中的数据库用户名和密码是否正确

### 3. 前端 API 请求失败

**问题**: `Network Error` 或 `500 Internal Server Error`

**解决**: 
- 确保后端服务已启动
- 确保数据库已创建并初始化
- 检查 `frontend/vite.config.js` 中的代理配置

### 4. 端口被占用

**问题**: `Port 3000 is already in use`

**解决**: 
- 修改 `frontend/vite.config.js` 中的 `server.port`
- 或者关闭占用端口的进程

## 技术栈

### 前端
- Vue 3 (Composition API)
- Element Plus
- Vite
- Pinia
- Vue Router 4
- Axios
- SCSS

### 后端
- Node.js
- Express
- MySQL
- Sequelize
- JWT
- bcryptjs

## 项目结构

```
community/
├── frontend/              # Vue3 前端
│   ├── src/
│   │   ├── api/          # API 接口
│   │   ├── components/   # 公共组件
│   │   ├── views/        # 页面视图
│   │   ├── router/       # 路由配置
│   │   ├── store/        # 状态管理
│   │   └── styles/       # 全局样式
│   └── ...
├── backend/               # Node.js 后端
│   ├── src/
│   │   ├── config/       # 配置文件
│   │   ├── controllers/  # 控制器
│   │   ├── models/       # 数据模型
│   │   ├── routes/       # 路由
│   │   └── middleware/   # 中间件
│   └── ...
└── database/              # 数据库脚本
    ├── schema.sql        # 表结构
    └── seed.sql          # 种子数据
```

## 开发建议

1. **先启动后端**，确保数据库连接正常
2. **再启动前端**，查看页面效果
3. **注册账号**后体验完整功能
4. **发布项目**测试 CRUD 功能

## 下一步计划

- [ ] 完善项目详情页
- [ ] 添加图片上传功能
- [ ] 实现评论系统
- [ ] 添加消息通知
- [ ] 优化移动端体验
- [ ] 添加单元测试

## 联系方式

如有问题，请提交 Issue 或联系开发者。

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

前端服务将运行在 http://localhost:3001

### 5. 访问应用

打开浏览器访问 http://localhost:3001

## 功能说明

### 已完成的功能

✅ **前端功能**
- [x] 首页 - 项目列表展示（卡片形式）
- [x] 顶部导航栏 - Logo、搜索框、登录/注册、消息通知入口
- [x] 左侧边栏 - 分类筛选
- [x] 项目卡片 - 封面、标题、描述、参与人数、点赞数、就地收藏
- [x] 登录/注册页面
- [x] 发布 / 编辑项目页面（含封面图片上传：点击或拖拽，支持外链兜底）
- [x] 项目详情页面（含评论与回复、点赞、参与、浏览次数与发布日期规格条）
- [x] 公开主页 - 「TA 发布的 / TA 参与的」，可下钻到广场筛选视图
- [x] 搜索、标签筛选、排序（最新 / 最热 / 本周活跃）
- [x] 通知中心（含深链直达某条评论）
- [x] 响应式布局 + 深浅色主题
- [x] 统一错误提示与表单内联校验

✅ **后端功能**
- [x] 用户认证（JWT）
- [x] 用户注册/登录
- [x] 项目 CRUD（含封面 URL 持久化）
- [x] 封面图片上传（类型/体积/魔数三重校验 + 静态直出）
- [x] 分类列表
- [x] 点赞 / 收藏 / 参与功能
- [x] 评论与回复
- [x] 站内通知（参与 / 评论 / 点赞 / 收藏 / 回复）
- [x] 标签归一化与相关推荐

### 待完善的功能

⏳ **需要进一步完善**
- [ ] 图片裁剪 / 压缩（当前只做体积上限校验）
- [ ] 自动化测试接入 CI（`scripts/` 下的验证脚本目前靠手动执行）
- [ ] 单元测试

## 上传文件的清理策略

封面上传会产生磁盘文件，本项目用「实时回收 + 定期清扫」两层兜住，不会无限堆积：

1. **实时回收**：编辑项目时更换封面、清空封面、把封面换成站外链接，旧的站内文件会在保存成功后立即删除。
   删除前会再查一次引用数 —— 同一张图被多个项目引用时不会误删（`backend/src/services/cover.service.js`）。
2. **定期清扫**：兜住「选了图、图已落盘、但用户没提交就关页面」这类服务端无从归属的文件。

```bash
cd backend
npm run uploads:prune:dry   # 干跑：只列出孤儿候选，不删任何东西
npm run uploads:prune       # 真删（等价于 node scripts/prune-uploads.js --apply）
```

判定「孤儿」需要同时满足三条，口径刻意保守：文件位于 `backend/uploads/projects/` 且命名符合服务端规则、
**全表（含软删除项目）没有任何 `cover_image` 指向它**、且修改时间已超过宽限期（默认 24 小时）。
宽限期是为了避开竞态：正在填表单的人，他的图还没被任何项目引用，但那不是垃圾。

生产环境已在 `backend/ecosystem.config.js` 里注册了一个 PM2 定时任务，每天凌晨 3:30 自动执行清扫，
不需要额外配置 crontab。

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

**问题**: `Port 3001 is already in use`

**解决**: 
- 修改 `frontend/vite.config.js` 中的 `server.port`
- 或者关闭占用端口的进程

> 注意：Vite 默认监听 `localhost`（本机可能解析到 IPv6 的 `::1`）。用 `127.0.0.1:3001` 访问可能连不上，请用 `localhost:3001`。

## 技术栈

### 前端
- Vue 3 (Composition API + `<script setup>`)
- Vite
- Tailwind CSS 4（设计令牌走 CSS 变量，深浅色自动翻转）
- Pinia
- Vue Router 4
- Axios

### 后端
- Node.js
- Express 5
- MySQL 8
- Sequelize
- JWT
- bcryptjs
- multer（封面图片上传，含文件魔数校验）

## 项目结构

```
community/
├── frontend/              # Vue3 前端（:3001）
│   ├── src/
│   │   ├── api/          # API 接口封装
│   │   ├── components/   # 公共组件
│   │   ├── views/        # 页面视图
│   │   ├── composables/  # 组合式函数
│   │   ├── router/       # 路由配置
│   │   ├── store/        # Pinia 状态管理
│   │   ├── utils/        # 工具函数
│   │   └── style.css     # 全局样式 + 设计令牌
│   └── vite.config.js
├── backend/               # Node.js 后端（:5000）
│   ├── src/
│   │   ├── config/       # 配置文件
│   │   ├── controllers/  # 控制器（薄，只做参数搬运）
│   │   ├── services/     # 业务逻辑与 SQL
│   │   ├── models/       # 数据模型
│   │   ├── routes/       # 路由
│   │   ├── utils/        # 工具函数（含上传文件的安全路径校验）
│   │   └── middleware/   # 中间件（鉴权 / 限流 / 上传）
│   ├── scripts/          # 运维脚本（prune-uploads.js 孤儿封面清扫）
│   ├── uploads/          # 用户上传的封面（运行时数据，不进仓库）
│   └── server.js
├── scripts/               # Playwright + urllib 端到端验证脚本
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

- [ ] 图片裁剪与压缩
- [ ] 把 `scripts/verify_*.py` 接入 CI
- [ ] 单元测试与覆盖率
- [ ] 移动端交互细节继续打磨

## 联系方式

如有问题，请提交 Issue 或联系开发者。

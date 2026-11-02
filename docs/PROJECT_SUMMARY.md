# 共创社区平台 - 项目总结

> 成稿于 2026-01-03，**2026-11-02 按当前代码库整体校准**。
> 早期设计稿与实施计划保留在 `docs/superpowers/`，仅作历史存档，不代表当前实现。

## 项目概述

共创社区是一个面向项目协作的 Web 平台：用户可以发布项目、浏览与搜索他人项目、点赞 / 收藏 / 参与协作，并在项目下评论、回复与 @ 提及。平台采用前后端分离架构，前端以卡片流展示项目，后端提供 REST API。

## 技术架构

### 前端

- Vue 3（Composition API + `<script setup>`）
- Vite 5
- Tailwind CSS 3.4 + CSS 变量设计令牌（Apple HIG 风格，支持深浅色）
- Pinia
- Vue Router 4
- Axios

### 后端

- Node.js
- Express 4
- MySQL 8
- Sequelize 6
- JWT（`jsonwebtoken`）
- bcryptjs
- multer（封面上传，含文件魔数校验）
- helmet、express-rate-limit

### 运行端口

- 后端：`http://localhost:5000`
- 前端：`http://localhost:3001`（Vite 把 `/api` 与 `/uploads` 代理到后端）

## 当前功能

### 前端

- **首页**：项目卡片流、分类筛选、关键词搜索、热门标签、编辑推荐筛选
- **排序**：最新 / 最热 / 参与最多 / 本周热门
- **项目卡片**：封面、标题、摘要、标签、参与数、点赞数、就地收藏
- **发布 / 编辑项目**：封面点击或拖拽上传、本机压缩、可拖动构图、标签、仓库地址、截止日期
- **项目详情**：浏览量、发布日期、点赞 / 收藏 / 参与、共创者名单、相关推荐
- **评论**：评论与回复树、评论点赞、深链定位、@ 提及高亮与补全
- **评论富文本**：仅支持粗体、行内代码、围栏代码块，纯插值渲染（零 `v-html`）
- **用户认证**：登录 / 注册、登录态持久化
- **个人中心**：我的发布、我的参与、我的收藏、我的评论、资料编辑、改密
- **他人主页**：TA 发布的 / TA 参与的，可下钻到广场筛选视图
- **通知中心**：类型筛选、已读筛选、单条 / 批量标记已读、评论深链
- **账号安全页**：针对我的失败尝试、我的操作记录、修改登录密码
- **全局体验**：统一错误提示、表单内联校验、自定义确认框、深色模式、响应式与 44px 触控热区

### 后端

- **认证**：JWT；`token_version` 支持改密后旧令牌全部作废
- **用户**：注册 / 登录 / 资料 / 改密 / 我的评论 / 我的统计 / 我的收藏 / 公开主页
- **项目**：列表、详情、创建、编辑、软删除；分类、标签、搜索、排序、热门标签、相关推荐
- **互动**：点赞、收藏、参与（含创建者退出保护）
- **评论**：发表 / 删除、回复、评论点赞、深链定位
- **通知**：参与 / 评论 / 回复 / 提及四类实际触发点
- **上传**：封面类型 / 体积 / 魔数三重校验，静态直出，孤儿文件定时清扫
- **审计**：操作日志（发布 / 编辑 / 删除 / 评论 / 注册 / 改资料 / 改密）
- **安全**：安全事件（登录失败 / 注册被拒 / 令牌无效）脱敏并按来源聚合
- **健壮性**：统一响应 `{code, message, data?}`、分页与排序参数收口、全局限流与敏感接口独立限流
- **运维**：健康检查、优雅停机、PM2 定时任务（上传清扫 / 日志留存清理）

## 数据模型

建库脚本唯一来源：`backend/database/schema.sql`，共 12 张表：

| 表 | 用途 |
| --- | --- |
| `users` | 用户（bcrypt 哈希、`token_version` 会话版本） |
| `categories` | 分类（8 条种子由 `seed.js` 幂等写入） |
| `projects` | 项目（软删除，标签存 `tags` JSON 数组） |
| `project_comments` | 评论与回复（`parent_id` 自引用） |
| `comment_likes` | 评论点赞 |
| `notifications` | 站内通知 |
| `project_favorites` | 项目收藏 |
| `project_likes` | 项目点赞 |
| `project_participants` | 项目参与者 |
| `project_views` | 登录用户浏览去重 |
| `activity_logs` | 操作日志（刻意不挂外键） |
| `security_events` | 安全事件（按指纹聚合） |

标签没有独立表，唯一真源是 `projects.tags`。

## 前端状态管理与路由

### 状态管理

当前只有 `store/user.js` 一个 Pinia store，负责 token、用户信息、登录 / 注册 / 刷新 / 登出 / 换发令牌。项目列表、分类、通知等数据由各页面直接通过 `api/` 层获取，没有额外的全局 store。

### 路由

| 路径 | 页面 | 说明 |
| --- | --- | --- |
| `/` | HomeView | 首页 / 广场 |
| `/login` | LoginView | 登录 |
| `/register` | RegisterView | 注册 |
| `/project/:id` | ProjectDetailView | 项目详情 |
| `/publish` | PublishView | 发布项目（需登录） |
| `/project/:id/edit` | ProjectEditView | 编辑项目（需登录） |
| `/user/:id` | UserProfileView | 共创者主页 |
| `/profile` | ProfileView | 个人中心（需登录） |
| `/notifications` | NotificationsView | 通知中心（需登录） |
| `/security` | SecurityView | 账号安全（需登录） |
| `/:pathMatch(.*)*` | NotFoundView | 404 |

## 项目结构

```
community/
├── frontend/          # Vue 3 前端（:3001）
│   ├── src/api/       # 接口封装
│   ├── src/components/# 公共组件
│   ├── src/views/     # 页面视图
│   ├── src/composables/ # useToast / useConfirm 等
│   ├── src/router/    # 路由
│   ├── src/store/     # Pinia（仅 user）
│   ├── src/utils/     # 压缩、裁剪、富文本、时间等
│   └── src/style.css  # 设计令牌与全局样式
├── backend/           # Express 后端（:5000）
│   ├── src/config/    # 环境变量、数据库连接
│   ├── src/controllers/ # 控制器
│   ├── src/services/  # 业务逻辑与 SQL
│   ├── src/models/    # Sequelize 模型
│   ├── src/routes/    # 路由
│   ├── src/middleware/# 鉴权 / 限流 / 上传
│   ├── src/utils/     # 工具函数
│   ├── database/      # schema.sql + seed.js
│   ├── scripts/       # 运维脚本
│   └── tests/unit/    # node:test 单元测试
├── scripts/           # 端到端验证与巡检脚本
└── docs/              # 部署、审计、设计文档
```

## 质量保障

- **后端单元测试**：`backend/tests/unit/`，5 个文件 / 55 项，`npm test` 运行
- **端到端验证**：39 个 `scripts/verify_*.py` + `audit_frontend_ui.py`，由 `scripts/run_verify_suite.py` 顺序执行
- **接口巡检**：`scripts/audit_backend_api.py` 用坏输入矩阵检查全端点不产生 5xx
- **结构一致性**：`scripts/verify_schema_consistency.py` 校验 `schema.sql` ↔ 线上库 ↔ Sequelize 模型
- **CI**：`.github/workflows/verify.yml` 在全新 MySQL 8.4 环境建库、跑单测与全量验证套件

## 部署建议

### 开发环境

```bash
cd backend && npm run dev     # :5000
cd frontend && npm run dev    # :3001
```

### 生产环境

1. 前端 `npm run build`，`dist/` 交给 Nginx 或 CDN
2. 后端用 PM2 托管（`backend/ecosystem.config.js`），配置 Nginx 反向代理
3. MySQL 定期备份；上传目录纳入备份
4. 生产环境必须显式配置 `JWT_SECRET`，凭据只放环境变量或 `backend/.env`

## 已知遗留项（产品决策，未擅自启用或删除）

- `users.status` / `users.is_admin`、`categories.project_count` / `categories.status`、`projects.status` / `access_type` / `access_password` 等线上遗留列：代码零读写
- `projects.repository_url` / `end_date` 已接成真实功能
- `notifications.type` 中的 `like` 取值：枚举存在但无触发点，点赞项目不会通知作者
- 更完整的逐列结论见 `docs/遗留列处置决策清单.md` 与 `docs/功能与数据设计审计报告.md`

## 相关文档

- 启动与功能说明：`README.md`
- 本地 MySQL：`docs/MYSQL_SETUP.md`
- 宝塔部署：`docs/BAOTA_DEPLOYMENT.md` / `docs/DEPLOYMENT_CHECKLIST.md`
- 前端审计：`docs/FRONTEND_AUDIT.md`
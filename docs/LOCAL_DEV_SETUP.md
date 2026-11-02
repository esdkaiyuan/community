# 本地快速开发配置

> 2026-11-02 校准：本文旧版曾建议改用 SQLite 并修改 `database.js`，但当前
> `backend/src/config/database.js` 只支持 MySQL 方言，`sequelize.sync()` 也与
> 线上表结构存在漂移。本地开发请直接使用 MySQL 8 + `schema.sql`。

## 前置要求

- Node.js 16+
- MySQL 8（安装方式见 `docs/MYSQL_SETUP.md`）

## 1. 创建数据库

```sql
CREATE DATABASE community_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2. 配置 `backend/.env`

```env
PORT=5000
NODE_ENV=development
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=community_platform
JWT_SECRET=本地开发用随机字符串
JWT_EXPIRES_IN=7d

# 邮箱验证服务（可选；不配则验证码注册/登录/找回密码返回 503）
EMAIL_VERIFY_BASE_URL=https://email.esdkaiyuan.online/api/v1
EMAIL_VERIFY_API_KEY=sk-你的外部Key
EMAIL_VERIFY_TIMEOUT_MS=10000
```

`.env` 已被 `.gitignore` 忽略，不要提交。

## 3. 建表并写入种子

在仓库根目录执行：

```bash
mysql -u root -p community_platform < backend/database/schema.sql
node backend/database/seed.js   # 写入 8 条分类种子，可幂等重跑
```

项目没有 `db:sync` 脚本；`schema.sql` 是唯一建库脚本。

## 4. 安装依赖并启动

```bash
# 后端（:5000）
cd backend && npm install && npm run dev

# 前端（:3001）
cd frontend && npm install && npm run dev
```

访问 `http://localhost:3001`。Vite 会把 `/api` 与 `/uploads` 代理到 `http://localhost:5000`。

## 5. 验证

```bash
# 数据库连接
cd backend
node -e "require('./src/config/database').authenticate().then(()=>console.log('OK')).catch(e=>console.error(e.message))"

# 后端健康检查
curl http://localhost:5000/api/health
```

## 常见问题

- **端口占用**：前端固定 3001（`vite.config.js` 的 `strictPort` 未开启，但验证脚本默认连 3001），后端固定 5000。
- **前端用 127.0.0.1 连不上**：Vite 默认监听 `localhost`，请用 `http://localhost:3001`。
- **建表失败**：确认 MySQL 为 8.x，并先创建目标数据库；`schema.sql` 不含 `CREATE DATABASE`。
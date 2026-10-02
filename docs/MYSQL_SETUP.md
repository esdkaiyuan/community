# MySQL 安装和本地数据库配置指南

> ## ✅ 当前本地环境实际状态（2026-07-17 已验证可用）
>
> 本机已安装并运行 MySQL（Windows 服务名 `MySQL`，端口 3306），**无需再按下文方案 A/B 重新安装**。
> 实际使用的数据库与 `backend/.env` 一致（宝塔面板同名库的本地副本）：
>
> ```env
> DB_HOST=localhost
> DB_PORT=3306
> DB_USER=co_creation_esdk
> DB_NAME=co_creation_esdk
> ```
>
> 库内 7 张表：`users`、`categories`、`projects`、`project_participants`、`project_likes`、`project_favorites`、`project_comments`，含真实数据（8 个分类、项目与用户若干；`projects.deleted_at` 非空的行为已软删除的历史数据）。
>
> **注意实际表结构与本文下方示例 SQL 不同**：计数列为 `like_count` / `comment_count` / `participant_count`（单数），用户密码列为 `password`（bcrypt 哈希）。后端 Sequelize 模型已与实际表结构对齐，不要按下文示例重建表。
>
> 验证连接：
> ```powershell
> cd backend
> node -e "require('./src/config/database').authenticate().then(()=>console.log('OK')).catch(e=>console.error(e.message))"
> ```
>
> 启动后端（`npm run dev` 或 `node server.js`，监听 5000），前端 Vite 代理 `/api` → `localhost:5000`，页面即读写本地库。
> 另：下文提到的 `npm run db:sync` 脚本并不存在（backend/package.json 只有 `start`/`dev`），请忽略。

---

## 📦 方案 A：使用 Docker 安装 MySQL（推荐，快速）

### 1. 安装 Docker Desktop

如果你还没有 Docker：
- 下载地址：https://www.docker.com/products/docker-desktop/
- 安装后重启电脑

### 2. 启动 MySQL 容器

```powershell
# 在 PowerShell 中运行
docker run -d `
  --name mysql-community `
  -e MYSQL_ROOT_PASSWORD=root123 `
  -e MYSQL_DATABASE=co_creation_dev `
  -e MYSQL_USER=dev_user `
  -e MYSQL_PASSWORD=dev_password `
  -p 3306:3306 `
  mysql:8.0
```

### 3. 更新后端配置

修改 `backend/.env`：

```env
# 数据库配置（本地 Docker）
DB_HOST=localhost
DB_PORT=3306
DB_USER=dev_user
DB_PASSWORD=dev_password
DB_NAME=co_creation_dev
```

---

## 📦 方案 B：手动安装 MySQL（传统方式）

### 1. 下载 MySQL

**方法1：使用 MySQL Installer（推荐）**
- 下载：https://dev.mysql.com/downloads/installer/
- 选择 "mysql-installer-community-8.0.xx.msi"
- 安装时选择 "Developer Default" 或 "Server only"

**方法2：使用 Chocolatey（包管理器）**
```powershell
# 安装 Chocolatey（如果没有）
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装 MySQL
choco install mysql -y
```

### 2. 安装配置

1. 运行 MySQL Installer
2. 选择 "Custom" 安装类型
3. 选择 "MySQL Server 8.0.x"
4. 设置 root 密码（记住这个密码！）
5. 完成安装

### 3. 启动 MySQL 服务

```powershell
# 检查服务
Get-Service MySQL80

# 启动服务
Start-Service MySQL80

# 设置为自动启动
Set-Service MySQL80 -StartupType Automatic
```

### 4. 创建数据库和用户

```powershell
# 登录 MySQL
mysql -u root -p
# 输入安装时设置的 root 密码
```

```sql
-- 创建数据库
CREATE DATABASE co_creation_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'dev_user'@'localhost' IDENTIFIED BY 'dev_password';

-- 授权
GRANT ALL PRIVILEGES ON co_creation_dev.* TO 'dev_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 5. 更新后端配置

修改 `backend/.env`：

```env
# 数据库配置（本地 MySQL）
DB_HOST=localhost
DB_PORT=3306
DB_USER=dev_user
DB_PASSWORD=dev_password
DB_NAME=co_creation_dev
```

---

## 🗄️ 初始化数据库表

### 方法1：使用 Sequelize 自动同步（推荐）

```powershell
cd backend
npm run db:sync
```

这会根据模型自动创建所有表。

### 方法2：手动执行 SQL 脚本

仓库里已有权威的建库脚本 `backend/database/schema.sql`，直接执行它即可：

```powershell
mysql -u dev_user -p co_creation_dev < backend/database/schema.sql
node backend/database/seed.js   # 写入 8 条分类种子
```

> 本节曾内嵌一份手写的示例 schema，但里面的 `projects.user_id`、
> `views` / `likes` / `participants`、`status ENUM('draft','published','archived')`
> 等与真实结构完全不符，且结尾写着「保存为 backend/database/schema.sql」——
> 照做会把真正的建库脚本覆盖成错的。
>
> 建库脚本只能有一份：`backend/database/schema.sql`。
> `scripts/verify_schema_consistency.py` 会**真的把它执行一遍**（隔离命名空间下建表
> 再比对线上结构），所以它不会再退化成「能看不能跑」。

---

## ✅ 验证连接

```powershell
cd backend
node -e "
const sequelize = require('./src/config/database');
sequelize.authenticate()
  .then(() => console.log('✓ 数据库连接成功'))
  .catch(err => console.error('✗ 数据库连接失败:', err.message));
"
```

---

## 🚀 重启服务

```powershell
# 停止当前服务（Ctrl+C）

# 重新启动
cd backend
npm run dev

cd ../frontend
npm run dev
```

---

##  快速检查清单

- [ ] MySQL 服务正在运行
- [ ] 数据库 `co_creation_dev` 已创建
- [ ] 用户 `dev_user` 已创建并授权
- [ ] `.env` 文件已更新
- [ ] 数据库表已创建（使用 `db:sync` 或 SQL 脚本）
- [ ] 后端服务已重启
- [ ] 前端页面可以正常加载数据

---

## 💡 常见问题

### Q: MySQL 服务无法启动
A: 检查端口 3306 是否被占用：
```powershell
netstat -ano | findstr :3306
```

### Q: 连接被拒绝
A: 检查防火墙设置，确保 3306 端口开放

### Q: 权限错误
A: 重新执行授权语句：
```sql
GRANT ALL PRIVILEGES ON co_creation_dev.* TO 'dev_user'@'localhost';
FLUSH PRIVILEGES;
```

### Q: 字符集问题
A: 确保数据库使用 utf8mb4：
```sql
ALTER DATABASE co_creation_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## 🎯 推荐方案

**对于本地开发，我强烈推荐使用 Docker 方案**，因为：
- ✅ 安装简单，一条命令搞定
- ✅ 不影响系统环境
- ✅ 可以随时删除重建
- ✅ 版本控制方便

如果你选择 Docker 方案，只需执行：

```powershell
docker run -d --name mysql-community -e MYSQL_ROOT_PASSWORD=root123 -e MYSQL_DATABASE=co_creation_dev -e MYSQL_USER=dev_user -e MYSQL_PASSWORD=dev_password -p 3306:3306 mysql:8.0
```

然后修改 `.env` 文件，运行 `npm run db:sync` 即可！

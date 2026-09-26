# 本地快速开发配置

## 🎯 最快的解决方案：使用 SQLite（无需安装 MySQL）

### 方案 1：改用 SQLite（推荐，5分钟搞定）

SQLite 是文件型数据库，无需安装任何服务，适合本地开发。

**步骤：**

1. 安装 SQLite 依赖：
```bash
cd backend
npm install sqlite3 better-sqlite3
```

2. 修改 `backend/src/config/database.js`：
```javascript
const { Sequelize } = require('sequelize')
require('dotenv').config()

// 开发环境使用 SQLite
const sequelize = process.env.NODE_ENV === 'development'
  ? new Sequelize({
      dialect: 'sqlite',
      storage: './database.sqlite',
      logging: false
    })
  : new Sequelize(
      process.env.DB_NAME,
      process.env.DB_USER,
      process.env.DB_PASSWORD,
      {
        host: process.env.DB_HOST,
        port: process.env.DB_PORT,
        dialect: 'mysql',
        logging: false,
        pool: {
          max: 5,
          min: 0,
          acquire: 30000,
          idle: 10000
        }
      }
    )

module.exports = sequelize
```

3. 运行同步：
```bash
npm run db:sync
```

4. 重启服务即可！

---

## 📦 方案 2：安装 MySQL（传统方式）

### 快速安装 MySQL

**方法 A：使用 XAMPP（最简单）**

1. 下载 XAMPP：https://www.apachefriends.org/
2. 安装时只选择 MySQL
3. 启动 XAMPP Control Panel
4. 点击 MySQL 的 Start 按钮
5. 访问 http://localhost/phpmyadmin 创建数据库

**方法 B：使用 MySQL Installer**

1. 下载：https://dev.mysql.com/downloads/installer/
2. 选择 "Developer Default"
3. 设置 root 密码（记住！）
4. 完成安装

### 创建数据库

```sql
-- 访问 phpMyAdmin 或命令行
CREATE DATABASE co_creation_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'dev_user'@'localhost' IDENTIFIED BY 'dev_password';
GRANT ALL PRIVILEGES ON co_creation_dev.* TO 'dev_user'@'localhost';
FLUSH PRIVILEGES;
```

### 更新配置

修改 `backend/.env`：
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=dev_user
DB_PASSWORD=dev_password
DB_NAME=co_creation_dev
```

### 初始化数据库

```bash
cd backend
mysql -u dev_user -p co_creation_dev < database/init-database.sql
npm run db:sync
```

---

## 🚀 方案 3：临时方案（仅测试 UI）

如果只想测试前端 UI，不需要真实数据库：

**修改后端 API 返回模拟数据：**

在 `backend/src/controllers/categoryController.js` 和 `projectController.js` 中返回硬编码数据。

---

## 💡 推荐

**对于快速本地开发，我强烈推荐方案 1（SQLite）**，因为：
- ✅ 无需安装任何软件
- ✅ 5分钟配置完成
- ✅ 数据保存在本地文件
- ✅ 随时可以切换到 MySQL

你想使用哪个方案？我可以帮你快速配置！

# 宝塔面板部署指南

## 📋 部署前准备

### 1. 服务器要求
- 操作系统：CentOS 7+ / Ubuntu 18.04+ / Debian 9+
- 宝塔面板版本：7.x 或更高
- Node.js 版本：16.x 或更高
- MySQL 版本：5.7 或 8.0
- Nginx 版本：1.18 或更高

### 2. 已配置的信息
- **数据库名**: `co_creation_esdk`
- **数据库用户**: `co_creation_esdk`
- **数据库密码**: `<见 backend/.env，切勿写入仓库>`
- **后端端口**: `5000`
- **前端端口**: `3000`（开发）/ `80`（生产）

---

## 🚀 部署步骤

### 第一步：安装宝塔面板必要软件

1. 登录宝塔面板
2. 安装以下软件：
   - ✅ Nginx 1.20+
   - ✅ MySQL 5.7 或 8.0
   - ✅ Node.js 16.x（通过 PM2 管理器安装）
   - ✅ PM2 管理器

### 第二步：上传项目文件

#### 方法1：使用 Git（推荐）
```bash
# 在服务器上执行
cd /www/wwwroot
git clone https://your-repo-url.git community
cd community
```

#### 方法2：使用 FTP/SFTP
1. 使用 FileZilla 或其他 FTP 工具
2. 连接到服务器
3. 上传整个项目到 `/www/wwwroot/community`

### 第三步：配置数据库

1. **创建数据库**（如果还未创建）
   - 进入宝塔面板 → 数据库
   - 添加数据库：
     - 数据库名：`co_creation_esdk`
     - 用户名：`co_creation_esdk`
     - 密码：`<见 backend/.env，切勿写入仓库>`
     - 访问权限：本地服务器

2. **导入数据库结构**
   ```bash
   # 进入项目目录
   cd /www/wwwroot/community/backend
   
   # 使用 Sequelize 同步数据库结构
   npm run db:sync
   ```
   
   或者手动执行 SQL 文件（如果有）：
   ```bash
   mysql -u co_creation_esdk -p co_creation_esdk < database/schema.sql
   ```

### 第四步：配置后端服务

1. **安装依赖**
   ```bash
   cd /www/wwwroot/community/backend
   npm install --production
   ```

2. **配置环境变量**
   
   `.env` 文件已经配置好，确认以下内容：
   ```env
   PORT=5000
   NODE_ENV=production
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=co_creation_esdk
   DB_PASSWORD=<见 backend/.env，切勿写入仓库>
   DB_NAME=co_creation_esdk
   JWT_SECRET=co_creation_community_secret_key_2024_change_in_production
   JWT_EXPIRES_IN=7d
   ```

3. **使用 PM2 启动后端服务**
   ```bash
   # 安装 PM2（如果未安装）
   npm install -g pm2
   
   # 启动后端服务
   cd /www/wwwroot/community/backend
   pm2 start server.js --name "community-backend"
   
   # 设置开机自启
   pm2 startup
   pm2 save
   
   # 查看运行状态
   pm2 status
   pm2 logs community-backend
   ```

### 第五步：构建前端

1. **安装依赖**
   ```bash
   cd /www/wwwroot/community/frontend
   npm install
   ```

2. **配置 API 地址**
   
   创建或修改 `frontend/.env.production`：
   ```env
   VITE_API_BASE_URL=http://your-domain.com/api
   # 或使用 IP：VITE_API_BASE_URL=http://your-server-ip:5000/api
   ```

3. **构建生产版本**
   ```bash
   npm run build
   ```
   
   构建完成后，静态文件会生成在 `frontend/dist` 目录

### 第六步：配置 Nginx

1. **在宝塔面板中添加网站**
   - 网站 → 添加站点
   - 域名：`your-domain.com`（或服务器IP）
   - 根目录：`/www/wwwroot/community/frontend/dist`
   - PHP版本：纯静态
   - 数据库：不创建

2. **配置 Nginx 反向代理**
   
   进入网站设置 → 配置文件，添加以下内容：

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;  # 修改为你的域名或IP
       
       # 前端静态文件
       root /www/wwwroot/community/frontend/dist;
       index index.html;
       
       # 前端路由支持（Vue Router history 模式）
       location / {
           try_files $uri $uri/ /index.html;
       }
       
       # 后端 API 反向代理
       location /api/ {
           proxy_pass http://127.0.0.1:5000/;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # 超时设置
           proxy_connect_timeout 60s;
           proxy_send_timeout 60s;
           proxy_read_timeout 60s;
       }
       
       # 静态资源缓存
       location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
           expires 30d;
           add_header Cache-Control "public, immutable";
       }
       
       # Gzip 压缩
       gzip on;
       gzip_vary on;
       gzip_min_length 1024;
       gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;
   }
   ```

3. **重启 Nginx**
   ```bash
   nginx -t  # 测试配置
   nginx -s reload  # 重载配置
   ```

### 第七步：配置防火墙和安全组

1. **开放必要端口**
   - 80（HTTP）
   - 443（HTTPS，如果启用SSL）
   - 5000（后端API，仅内部访问）

2. **在宝塔面板中配置**
   - 安全 → 放行端口
   - 添加：80、443

3. **云服务器安全组**（阿里云/腾讯云等）
   - 入站规则：允许 80、443 端口

### 第八步：配置 SSL 证书（可选但推荐）

1. **在宝塔面板中申请免费 SSL**
   - 网站 → SSL → Let's Encrypt
   - 申请证书
   - 强制 HTTPS

2. **更新 Nginx 配置**
   
   SSL 会自动配置，确保 API 代理也使用 HTTPS。

---

## 🔧 常用管理命令

### PM2 管理后端
```bash
# 查看状态
pm2 status

# 查看日志
pm2 logs community-backend

# 重启服务
pm2 restart community-backend

# 停止服务
pm2 stop community-backend

# 删除服务
pm2 delete community-backend

# 监控
pm2 monit
```

### 查看日志
```bash
# 后端日志
tail -f /www/wwwroot/community/backend/logs/app.log

# PM2 日志
pm2 logs community-backend --lines 100

# Nginx 日志
tail -f /www/wwwlogs/your-domain.com.error.log
tail -f /www/wwwlogs/your-domain.com.access.log
```

### 更新项目
```bash
cd /www/wwwroot/community

# 拉取最新代码
git pull

# 更新后端
cd backend
npm install --production
pm2 restart community-backend

# 重新构建前端
cd ../frontend
npm install
npm run build
```

---

## ⚠️ 注意事项

### 1. 安全性
- ✅ 修改 `.env` 中的 `JWT_SECRET` 为随机字符串
- ✅ 不要将 `.env` 文件提交到 Git
- ✅ 定期更新系统和软件包
- ✅ 配置防火墙，只开放必要端口
- ✅ 使用 HTTPS 加密传输

### 2. 性能优化
- ✅ 启用 Nginx Gzip 压缩
- ✅ 配置静态资源缓存
- ✅ 使用 CDN 加速静态资源
- ✅ 数据库连接池配置合理
- ✅ 启用 PM2 集群模式（多核CPU）

### 3. 备份策略
- ✅ 定期备份数据库
  ```bash
  mysqldump -u co_creation_esdk -p co_creation_esdk > backup_$(date +%Y%m%d).sql
  ```
- ✅ 备份项目文件
- ✅ 备份 Nginx 配置
- ✅ 设置自动备份任务

### 4. 监控
- ✅ 使用宝塔面板监控系统资源
- ✅ 配置 PM2 进程监控
- ✅ 设置内存和 CPU 告警
- ✅ 定期检查日志文件

---

## 🐛 常见问题

### 问题1：后端无法连接数据库
**解决方案**：
```bash
# 检查数据库是否运行
systemctl status mysqld

# 测试数据库连接
mysql -u co_creation_esdk -p -h localhost

# 检查 .env 配置
cat /www/wwwroot/community/backend/.env

# 查看后端日志
pm2 logs community-backend
```

### 问题2：前端页面空白
**解决方案**：
```bash
# 检查构建是否成功
ls -la /www/wwwroot/community/frontend/dist

# 检查 Nginx 配置
nginx -t

# 检查浏览器控制台错误
# F12 打开开发者工具查看 Console
```

### 问题3：API 请求失败（404/502）
**解决方案**：
```bash
# 检查后端是否运行
pm2 status

# 检查端口是否监听
netstat -tlnp | grep 5000

# 测试 API
curl http://localhost:5000/api/health

# 检查 Nginx 反向代理配置
cat /www/server/panel/vhost/nginx/your-domain.com.conf
```

### 问题4：PM2 进程自动退出
**解决方案**：
```bash
# 查看详细错误日志
pm2 logs community-backend --err

# 检查内存限制
pm2 describe community-backend

# 增加内存限制（如果需要）
pm2 start server.js --name "community-backend" --max-memory-restart 500M
```

---

## 📞 技术支持

如遇到问题，请检查：
1. 系统日志：`/var/log/messages`
2. Nginx 日志：`/www/wwwlogs/`
3. PM2 日志：`pm2 logs`
4. 数据库日志：`/www/server/data/*.err`

---

## ✅ 部署检查清单

- [ ] 宝塔面板已安装必要软件（Nginx、MySQL、Node.js、PM2）
- [ ] 数据库已创建并导入数据结构
- [ ] 后端依赖已安装（npm install）
- [ ] `.env` 文件配置正确
- [ ] PM2 后端服务正常运行
- [ ] 前端已构建（npm run build）
- [ ] Nginx 网站已创建
- [ ] Nginx 反向代理配置正确
- [ ] 防火墙端口已开放
- [ ] SSL 证书已配置（可选）
- [ ] 域名解析已设置（如果使用域名）
- [ ] 网站可以正常访问
- [ ] API 接口可以正常调用
- [ ] 数据库连接正常
- [ ] 已设置自动备份
- [ ] 已配置监控告警

---

**祝部署顺利！** 🎉

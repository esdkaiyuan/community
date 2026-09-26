# 🚀 宝塔面板部署检查清单

## 📋 部署前准备

### 服务器环境
- [ ] 已安装宝塔面板（7.x+）
- [ ] 已安装 Nginx 1.20+
- [ ] 已安装 MySQL 5.7/8.0
- [ ] 已安装 Node.js 16.x+（通过 PM2 管理器）
- [ ] 已安装 PM2 管理器

### 数据库配置
- [ ] 数据库名：`co_creation_esdk`
- [ ] 数据库用户：`co_creation_esdk`
- [ ] 数据库密码：`GchzPPQ8sM6Rc2Xn`
- [ ] 访问权限：本地服务器
- [ ] 已导入数据库结构（执行 `npm run db:sync` 或 SQL 文件）

---

## 🔧 部署步骤

### 1️⃣ 上传项目
```bash
cd /www/wwwroot
git clone <your-repo-url> community
# 或使用 FTP 上传
```

### 2️⃣ 配置后端
```bash
cd /www/wwwroot/community/backend

# 确认 .env 配置正确
cat .env

# 安装依赖
npm install --production

# 创建日志目录
mkdir -p logs

# 启动服务
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 3️⃣ 构建前端
```bash
cd /www/wwwroot/community/frontend

# 修改 API 地址
vim .env.production
# 设置 VITE_API_BASE_URL=http://your-domain.com/api

# 安装依赖
npm install

# 构建
npm run build
```

### 4️⃣ 配置 Nginx
在宝塔面板中：
1. 添加网站
   - 域名：`your-domain.com` 或服务器 IP
   - 根目录：`/www/wwwroot/community/frontend/dist`
   - PHP：纯静态

2. 配置反向代理（网站设置 → 配置文件）
   ```nginx
   location /api/ {
       proxy_pass http://127.0.0.1:5000/;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   }
   
   location / {
       try_files $uri $uri/ /index.html;
   }
   ```

3. 重启 Nginx
   ```bash
   nginx -t && nginx -s reload
   ```

### 5️⃣ 配置防火墙
- [ ] 开放端口 80（HTTP）
- [ ] 开放端口 443（HTTPS，如果启用 SSL）
- [ ] 云服务器安全组放行相应端口

### 6️⃣ 配置 SSL（可选但推荐）
- [ ] 申请 Let's Encrypt 免费证书
- [ ] 强制 HTTPS
- [ ] 测试 HTTPS 访问

---

## ✅ 验证部署

### 测试后端
```bash
# 检查 PM2 状态
pm2 status

# 查看日志
pm2 logs community-backend

# 测试 API
curl http://localhost:5000/api/health
```

### 测试前端
```bash
# 浏览器访问
http://your-domain.com
# 或
http://your-server-ip
```

### 功能测试
- [ ] 首页可以正常访问
- [ ] 注册页面显示验证码
- [ ] 可以成功注册用户
- [ ] 可以登录
- [ ] 可以浏览项目列表
- [ ] API 请求正常（无 404/502 错误）

---

## 🔍 故障排查

### 后端无法启动
```bash
# 查看详细错误
pm2 logs community-backend --err

# 检查端口占用
netstat -tlnp | grep 5000

# 检查 .env 配置
cat /www/wwwroot/community/backend/.env
```

### 前端页面空白
```bash
# 检查构建文件
ls -la /www/wwwroot/community/frontend/dist/

# 检查 Nginx 配置
nginx -t

# 查看浏览器控制台错误（F12）
```

### API 请求失败
```bash
# 检查后端是否运行
pm2 status

# 测试 API
curl http://localhost:5000/api/categories

# 检查 Nginx 反向代理
tail -f /www/wwwlogs/your-domain.com.error.log
```

### 数据库连接失败
```bash
# 测试数据库连接
mysql -u co_creation_esdk -p'GchzPPQ8sM6Rc2Xn' -h localhost

# 检查数据库是否存在
mysql -u co_creation_esdk -p'GchzPPQ8sM6Rc2Xn' -e "SHOW DATABASES;"
```

---

## 📊 监控和维护

### 日常维护命令
```bash
# 查看服务状态
pm2 status

# 查看日志
pm2 logs community-backend --lines 50

# 重启服务
pm2 restart community-backend

# 停止服务
pm2 stop community-backend

# 更新项目
cd /www/wwwroot/community
git pull
cd backend && npm install --production && pm2 restart community-backend
cd ../frontend && npm install && npm run build
```

### 备份数据库
```bash
# 手动备份
mysqldump -u co_creation_esdk -p'GchzPPQ8sM6Rc2Xn' co_creation_esdk > backup_$(date +%Y%m%d_%H%M%S).sql

# 设置定时备份（crontab）
0 2 * * * mysqldump -u co_creation_esdk -p'GchzPPQ8sM6Rc2Xn' co_creation_esdk > /backup/db_$(date +\%Y\%m\%d).sql
```

### 清理日志
```bash
# 清理 PM2 日志
pm2 flush

# 清理 Nginx 日志
> /www/wwwlogs/your-domain.com.access.log
> /www/wwwlogs/your-domain.com.error.log
```

---

## 🔒 安全建议

- [ ] 修改 `.env` 中的 `JWT_SECRET` 为随机字符串
- [ ] 不要将 `.env` 文件提交到 Git
- [ ] 定期更新系统和软件包
- [ ] 配置防火墙，只开放必要端口
- [ ] 使用 HTTPS 加密传输
- [ ] 定期备份数据库
- [ ] 监控系统资源使用情况
- [ ] 设置内存和 CPU 告警

---

## 📞 需要帮助？

查看详细文档：[BAOTA_DEPLOYMENT.md](BAOTA_DEPLOYMENT.md)

常见问题：
1. 确保数据库已创建并配置正确
2. 确保 PM2 服务正常运行
3. 确保 Nginx 反向代理配置正确
4. 检查防火墙和安全组设置
5. 查看日志文件定位问题

---

**部署完成后，记得删除此检查清单文件！** ✅

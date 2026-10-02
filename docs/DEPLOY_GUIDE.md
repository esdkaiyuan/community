# 🚀 共创社区平台 - 宝塔面板部署指南

## 📦 已生成的部署包

### 前端部署包
- **文件名**: `frontend-deploy-20260503_212932.zip`
- **大小**: 0.41 MB
- **位置**: `frontend/frontend-deploy-20260503_212932.zip`
- **包含内容**:
  - dist/ - 构建后的静态文件
  - DEPLOY_README.txt - 部署说明

### 后端部署包
- **文件名**: `backend-deploy-20260503_211850.zip`
- **大小**: 5 MB
- **位置**: `backend/backend-deploy-20260503_211850.zip`
- **包含内容**:
  - src/ - 后端源代码
  - node_modules/ - 生产依赖
  - ecosystem.config.js - PM2 配置
  - .env - 数据库配置
  - DEPLOY_README.txt - 部署说明

---

## 📋 数据库配置

以下配置已包含在后端 `.env` 文件中：

```
数据库名: co_creation_esdk
用户名: co_creation_esdk
密码: <见 backend/.env，切勿写入仓库>
主机: localhost:3306
```

---

## 🔧 部署步骤

### 第一步：上传文件到服务器

#### 方法 1：使用宝塔面板文件管理器
1. 登录宝塔面板
2. 进入"文件"
3. 上传两个压缩包到 `/www/wwwroot/`

#### 方法 2：使用 SCP/SFTP
```bash
# 上传前端
scp frontend/frontend-deploy-*.zip root@your-server:/www/wwwroot/

# 上传后端
scp backend/backend-deploy-*.zip root@your-server:/www/wwwroot/
```

### 第二步：解压文件

```bash
# SSH 登录服务器
ssh root@your-server

# 创建目录
mkdir -p /www/wwwroot/community-frontend
mkdir -p /www/wwwroot/community-backend

# 解压前端
cd /www/wwwroot/community-frontend
unzip /www/wwwroot/frontend-deploy-*.zip

# 解压后端
cd /www/wwwroot/community-backend
unzip /www/wwwroot/backend-deploy-*.zip
```

### 第三步：配置前端网站

#### 在宝塔面板中：
1. 进入"网站" → "添加站点"
2. 域名：填写你的域名（或 IP）
3. 根目录：`/www/wwwroot/community-frontend`
4. PHP 版本：纯静态
5. 点击"提交"

#### 配置 Nginx：
1. 点击网站 → 设置 → 配置文件
2. 添加以下配置：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}

location /api/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

3. 保存并重载 Nginx

### 第四步：启动后端服务

```bash
# 进入后端目录
cd /www/wwwroot/community-backend

# 安装 PM2（如果未安装）
npm install -g pm2

# 启动后端服务
pm2 start ecosystem.config.js

# 保存 PM2 配置
pm2 save

# 设置开机自启
pm2 startup
```

### 第五步：验证部署

```bash
# 检查后端服务状态
pm2 status

# 查看后端日志
pm2 logs community-backend

# 测试后端 API
curl http://localhost:5000/api/health
curl http://localhost:5000/api/categories

# 测试前端
curl http://localhost
```

### 第六步：浏览器访问

打开浏览器访问你的域名或 IP 地址，应该能看到共创社区平台！

---

## 🔍 常见问题排查

### 问题 1：前端显示但 API 请求失败

**症状**：页面可以打开，但项目列表加载失败

**解决方案**：
```bash
# 1. 检查后端服务是否运行
pm2 status

# 2. 查看后端日志
pm2 logs community-backend

# 3. 测试后端 API
curl http://localhost:5000/api/categories

# 4. 检查 Nginx 配置
nginx -t
nginx -s reload
```

### 问题 2：数据库连接失败

**症状**：后端日志显示 `ECONNREFUSED` 或 `Access denied`

**解决方案**：
```bash
# 1. 检查 MySQL 服务
systemctl status mysqld

# 2. 测试数据库连接
mysql -u co_creation_esdk -p co_creation_esdk

# 3. 如果数据库未初始化，执行 SQL 脚本
mysql -u co_creation_esdk -p co_creation_esdk < backend/database/schema.sql
```

### 问题 3：Nginx 反向代理不工作

**症状**：直接访问 `/api/` 返回 404

**解决方案**：
```bash
# 1. 检查 Nginx 配置
cat /www/server/panel/vhost/nginx/your-domain.com.conf

# 2. 确保有 location /api/ 配置块

# 3. 测试配置
nginx -t

# 4. 重载配置
nginx -s reload
```

### 问题 4：CORS 跨域错误

**症状**：浏览器控制台显示 CORS 错误

**解决方案**：
后端已配置 CORS，确保 `ecosystem.config.js` 正常运行。如果还有问题，检查后端代码中的 CORS 配置。

---

## 📊 服务管理命令

### 后端服务管理
```bash
# 查看服务状态
pm2 status

# 查看日志
pm2 logs community-backend

# 重启服务
pm2 restart community-backend

# 停止服务
pm2 stop community-backend

# 删除服务
pm2 delete community-backend

# 查看实时日志
pm2 monit
```

### Nginx 管理
```bash
# 测试配置
nginx -t

# 重载配置
nginx -s reload

# 重启 Nginx
systemctl restart nginx

# 查看错误日志
tail -f /www/wwwlogs/your-domain.com.error.log

# 查看访问日志
tail -f /www/wwwlogs/your-domain.com.log
```

---

##  安全建议

### 1. 修改默认密码
```bash
# 修改 JWT_SECRET（在 backend/.env 中）
JWT_SECRET=your-new-secret-key-change-this
```

### 2. 配置防火墙
```bash
# 只开放必要端口
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-port=5000/tcp
firewall-cmd --reload
```

### 3. 配置 HTTPS（推荐）
1. 在宝塔面板中申请 SSL 证书
2. 开启强制 HTTPS
3. 配置 HSTS

### 4. 定期备份
```bash
# 备份数据库
mysqldump -u co_creation_esdk -p co_creation_esdk > backup_$(date +%Y%m%d).sql

# 备份代码
tar -czf backup_$(date +%Y%m%d).tar.gz /www/wwwroot/community-backend
```

---

## 📝 部署检查清单

部署完成后，请检查以下项目：

- [ ] 前端文件已上传并解压
- [ ] 后端文件已上传并解压
- [ ] 前端网站已在宝塔面板中创建
- [ ] Nginx 配置已添加 `/api/` 反向代理
- [ ] 后端服务已通过 PM2 启动
- [ ] 数据库连接正常
- [ ] 前端页面可以正常访问
- [ ] API 请求正常（项目列表、分类等）
- [ ] 登录/注册功能正常
- [ ] 发布项目功能正常
- [ ] 移动端响应式正常

---

## 🎉 部署完成！

如果所有检查项都通过，恭喜你！共创社区平台已成功部署到宝塔面板。

### 后续维护

1. **更新前端**：重新构建并上传 `frontend-deploy-*.zip`
2. **更新后端**：修改代码后重新打包并上传 `backend-deploy-*.zip`
3. **查看日志**：定期检查 `pm2 logs` 和 Nginx 日志
4. **备份数据**：定期备份数据库和上传的文件

---

##  技术支持

如遇问题，请检查：
1. 后端日志：`pm2 logs community-backend`
2. Nginx 错误日志：`/www/wwwlogs/`
3. 浏览器控制台错误
4. 网络请求状态（F12 → Network）

祝你使用愉快！ 🎊

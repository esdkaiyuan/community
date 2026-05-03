# 前端部署包使用说明

## 📦 已生成的部署包

**文件名**: `frontend-deploy-20260503_201248.zip`  
**大小**: 0.41 MB  
**位置**: `d:\treai项目\community\frontend\`

---

## 🚀 如何重新构建

### 在 Windows 上

#### 方法1: 使用批处理脚本（推荐）
```bash
cd frontend
build-frontend.bat
```

#### 方法2: 手动构建
```bash
cd frontend
npm install
npm run build
# 然后手动压缩 dist 目录
```

### 在 Linux/Mac 上

```bash
cd frontend
chmod +x build-frontend.sh
./build-frontend.sh
```

---

## 📤 部署到服务器

### 步骤1: 上传压缩包

```bash
# 使用 SCP
scp frontend-deploy-*.zip root@your-server:/www/wwwroot/

# 或使用 FTP/SFTP 工具上传
```

### 步骤2: 解压到网站根目录

```bash
# SSH 登录服务器
ssh root@your-server

# 创建网站目录
mkdir -p /www/wwwroot/community-frontend

# 解压
cd /www/wwwroot/community-frontend
unzip /www/wwwroot/frontend-deploy-*.zip

# 设置权限
chown -R www:www /www/wwwroot/community-frontend
chmod -R 755 /www/wwwroot/community-frontend
```

### 步骤3: 配置 Nginx

在宝塔面板中：

1. **添加网站**
   - 域名：`your-domain.com`
   - 根目录：`/www/wwwroot/community-frontend`
   - PHP：纯静态

2. **配置伪静态**（Vue Router history 模式必需）
   
   网站设置 → 伪静态，添加：
   ```nginx
   location / {
       try_files $uri $uri/ /index.html;
   }
   ```

3. **配置反向代理**（API 请求转发到后端）
   
   网站设置 → 配置文件，在 server 块中添加：
   ```nginx
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
   }
   ```

4. **重启 Nginx**
   ```bash
   nginx -t && nginx -s reload
   ```

### 步骤4: 配置 API 地址

如果前端需要访问不同域的 API，需要在构建前修改：

```bash
# 编辑 .env.production
vim .env.production

# 设置正确的 API 地址
VITE_API_BASE_URL=http://your-domain.com/api
# 或
VITE_API_BASE_URL=http://your-server-ip:5000/api

# 重新构建
npm run build
```

---

## 🔧 Nginx 完整配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /www/wwwroot/community-frontend;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json application/javascript;

    # Vue Router history 模式支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
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

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
}
```

---

## ✅ 验证部署

### 1. 检查文件
```bash
ls -la /www/wwwroot/community-frontend/
# 应该看到 index.html 和 assets/ 目录
```

### 2. 测试访问
```bash
# 本地测试
curl http://localhost

# 远程测试
curl http://your-domain.com
```

### 3. 检查 API 连接
```bash
# 测试 API 反向代理
curl http://your-domain.com/api/health
```

### 4. 浏览器测试
打开浏览器访问 `http://your-domain.com`，检查：
- ✅ 页面正常显示
- ✅ 控制台无错误
- ✅ API 请求成功
- ✅ 路由跳转正常

---

## ⚠️ 常见问题

### 问题1: 页面空白
**原因**: Nginx 配置错误或文件路径不对

**解决**:
```bash
# 检查 Nginx 配置
nginx -t

# 检查文件是否存在
ls -la /www/wwwroot/community-frontend/index.html

# 查看 Nginx 错误日志
tail -f /www/wwwlogs/your-domain.com.error.log
```

### 问题2: 路由 404
**原因**: 未配置 Vue Router history 模式支持

**解决**: 确保 Nginx 配置中有：
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### 问题3: API 请求失败
**原因**: 反向代理配置错误或后端服务未启动

**解决**:
```bash
# 检查后端服务
pm2 status

# 测试后端 API
curl http://localhost:5000/api/health

# 检查 Nginx 反向代理配置
cat /www/server/panel/vhost/nginx/your-domain.com.conf
```

### 问题4: 静态资源 404
**原因**: 路径配置错误

**解决**: 检查 `vite.config.js` 中的 `base` 配置，确保是 `/`

---

## 🎯 优化建议

### 1. 启用 HTTPS
```bash
# 在宝塔面板中申请 Let's Encrypt 证书
# 网站 → SSL → Let's Encrypt → 申请
```

### 2. 启用 CDN
将静态资源（JS、CSS、图片）托管到 CDN 加速访问。

### 3. 开启 Gzip/Brotli 压缩
已在 Nginx 配置中启用 Gzip。

### 4. 配置浏览器缓存
已在 Nginx 配置中设置静态资源缓存 30 天。

### 5. 使用 HTTP/2
```nginx
listen 443 ssl http2;
```

---

## 📊 构建信息

- **构建工具**: Vite 5.4.21
- **框架**: Vue 3
- **UI库**: Element Plus
- **构建时间**: 约 8 秒
- **输出大小**: 约 0.41 MB（压缩后）
- **未压缩大小**: 约 1.4 MB

---

## 🔄 更新流程

当代码有更新时：

```bash
# 1. 拉取最新代码
git pull

# 2. 安装依赖（如果有新依赖）
npm install

# 3. 重新构建
npm run build

# 4. 创建新的部署包
# 运行 build-frontend.sh 或 build-frontend.bat

# 5. 上传到服务器并替换旧文件
# 6. 清除浏览器缓存或 CDN 缓存
```

---

**祝部署顺利！** 🎉

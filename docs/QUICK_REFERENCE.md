# 🚀 宝塔面板部署 - 快速参考

## 📌 数据库信息
```
数据库名: co_creation_esdk
用户名:   co_creation_esdk
密码:     <见 backend/.env，切勿写入仓库>
主机:     localhost
端口:     3306
```

## 🔑 关键配置

### 后端 (.env)
```env
PORT=5000
NODE_ENV=production
DB_HOST=localhost
DB_USER=co_creation_esdk
DB_PASSWORD=<见 backend/.env，切勿写入仓库>
DB_NAME=co_creation_esdk
```

### 前端 (.env.production)
```env
VITE_API_BASE_URL=http://your-domain.com/api
```

## 📂 项目路径
```
项目根目录: /www/wwwroot/community
后端目录:   /www/wwwroot/community/backend
前端目录:   /www/wwwroot/community/frontend
静态文件:   /www/wwwroot/community/frontend/dist
```

## ⚡ 快速命令

### 启动服务
```bash
cd /www/wwwroot/community/backend
pm2 start ecosystem.config.js
pm2 save
```

### 查看状态
```bash
pm2 status
pm2 logs community-backend
```

### 重启服务
```bash
pm2 restart community-backend
```

### 更新项目
```bash
cd /www/wwwroot/community
git pull
cd backend && npm install --production && pm2 restart community-backend
cd ../frontend && npm install && npm run build
```

### 备份数据库
```bash
mysqldump -u co_creation_esdk -p co_creation_esdk > backup_$(date +%Y%m%d).sql
```

## 🔧 Nginx 配置要点

### 反向代理
```nginx
location /api/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

location / {
    try_files $uri $uri/ /index.html;
}
```

## 📊 日志位置
```
PM2 日志:    pm2 logs community-backend
Nginx 访问:  /www/wwwlogs/your-domain.com.access.log
Nginx 错误:  /www/wwwlogs/your-domain.com.error.log
后端日志:    /www/wwwroot/community/backend/logs/
```

## ✅ 检查清单
- [ ] 数据库已创建
- [ ] 后端依赖已安装
- [ ] PM2 服务已启动
- [ ] 前端已构建
- [ ] Nginx 已配置
- [ ] 防火墙已开放端口
- [ ] 网站可以访问
- [ ] API 可以调用

## 🆘 常见问题

**后端无法启动？**
```bash
pm2 logs community-backend --err
netstat -tlnp | grep 5000
```

**前端页面空白？**
```bash
ls -la /www/wwwroot/community/frontend/dist/
nginx -t
```

**API 404/502？**
```bash
pm2 status
curl http://localhost:5000/api/health
tail -f /www/wwwlogs/your-domain.com.error.log
```

---
详细文档: [BAOTA_DEPLOYMENT.md](BAOTA_DEPLOYMENT.md)
检查清单: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

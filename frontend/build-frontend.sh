#!/bin/bash

# 共创社区平台 - 前端构建和打包脚本
# 使用方法: chmod +x build-frontend.sh && ./build-frontend.sh

echo "======================================"
echo "共创社区平台 - 前端构建打包"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在前端目录
if [ ! -f "package.json" ] || [ ! -d "src" ]; then
    echo -e "${RED}错误: 请在前端目录运行此脚本${NC}"
    echo -e "${YELLOW}提示: cd /www/wwwroot/community/frontend${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}开始构建前端...${NC}"
echo ""

# 1. 检查环境
echo -e "${GREEN}[1/5] 检查环境...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未检测到 Node.js${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: 未检测到 npm${NC}"
    exit 1
fi

echo -e "${GREEN}Node.js 版本: $(node --version)${NC}"
echo -e "${GREEN}npm 版本: $(npm --version)${NC}"
echo ""

# 2. 安装依赖
echo -e "${GREEN}[2/5] 安装依赖...${NC}"
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}依赖安装失败${NC}"
    exit 1
fi
echo -e "${GREEN}依赖安装完成${NC}"
echo ""

# 3. 检查配置文件
echo -e "${GREEN}[3/5] 检查配置文件...${NC}"
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}警告: .env.production 不存在，使用默认配置${NC}"
    echo "VITE_API_BASE_URL=/api" > .env.production
fi

echo -e "${GREEN}API 地址配置:${NC}"
cat .env.production | grep VITE_API_BASE_URL
echo ""

# 4. 构建
echo -e "${GREEN}[4/5] 开始构建...${NC}"
npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}构建完成${NC}"
echo ""

# 5. 创建部署包
echo -e "${GREEN}[5/5] 创建部署包...${NC}"

# 获取版本号
VERSION=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="frontend-deploy-${VERSION}.zip"

# 检查 dist 目录
if [ ! -d "dist" ]; then
    echo -e "${RED}错误: dist 目录不存在${NC}"
    exit 1
fi

# 创建临时目录
TEMP_DIR="temp-frontend-deploy"
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

# 复制构建文件
cp -r dist/* $TEMP_DIR/

# 复制配置文件
if [ -f ".env.production" ]; then
    cp .env.production $TEMP_DIR/.env.production.example
fi

# 创建 README
cat > $TEMP_DIR/DEPLOY_README.txt << 'EOF'
# 前端部署说明

## 文件说明
- index.html: 入口文件
- assets/: 静态资源（JS、CSS、图片等）

## 部署步骤

### 方法1: Nginx 直接托管（推荐）

1. 将所有文件上传到 Nginx 网站根目录
   例如: /www/wwwroot/your-domain.com/

2. 配置 Nginx（参考以下配置）

3. 重启 Nginx
   systemctl restart nginx

### 方法2: 宝塔面板部署

1. 在宝塔面板中添加网站
2. 将所有文件上传到网站根目录
3. 配置伪静态（Vue Router history 模式需要）

## Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /www/wwwroot/your-domain.com;
    index index.html;

    # Vue Router history 模式支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## 注意事项

1. 确保 .env.production 中配置的 API 地址正确
2. 如果使用 history 模式，必须配置 Nginx 伪静态
3. 建议启用 Gzip 压缩和 HTTPS

## 常见问题

**页面空白？**
- 检查浏览器控制台错误
- 确认 Nginx 配置正确
- 检查 API 地址配置

**路由 404？**
- 确保配置了 try_files $uri $uri/ /index.html
- 刷新 Nginx: nginx -s reload

---
构建时间: $(date '+%Y-%m-%d %H:%M:%S')
EOF

# 创建压缩包
cd $TEMP_DIR
zip -r ../$PACKAGE_NAME . > /dev/null 2>&1
cd ..

# 清理临时目录
rm -rf $TEMP_DIR

# 显示结果
PACKAGE_SIZE=$(du -h $PACKAGE_NAME | cut -f1)

echo ""
echo -e "${GREEN}======================================"
echo "✅ 前端部署包创建成功！"
echo "======================================${NC}"
echo ""
echo -e "${GREEN}文件名: ${PACKAGE_NAME}${NC}"
echo -e "${GREEN}大小: ${PACKAGE_SIZE}${NC}"
echo -e "${GREEN}位置: $(pwd)/${PACKAGE_NAME}${NC}"
echo ""
echo -e "${YELLOW}📋 下一步操作:${NC}"
echo "1. 将压缩包上传到服务器"
echo "2. 解压到 Nginx 网站根目录"
echo "3. 配置 Nginx（参考 DEPLOY_README.txt）"
echo "4. 重启 Nginx"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo "- 确保后端 API 服务已启动（端口 5000）"
echo "- 配置正确的 API 地址（.env.production）"
echo "- 建议使用 HTTPS 和 CDN 加速"
echo ""

#!/bin/bash

# 共创社区平台 - 宝塔面板快速部署脚本
# 使用方法: chmod +x deploy.sh && ./deploy.sh

echo "======================================"
echo "共创社区平台 - 宝塔面板部署脚本"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在正确的项目目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    echo -e "${YELLOW}提示: 当前目录应该包含 backend/ 和 frontend/ 文件夹${NC}"
    echo -e "${YELLOW}当前目录: $(pwd)${NC}"
    echo -e "${YELLOW}目录内容:$(ls -la | head -10)${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}开始部署...${NC}"
echo ""

# 0. 检查环境
echo -e "${GREEN}[0/8] 检查环境...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未检测到 Node.js，请先安装 Node.js v16+${NC}"
    echo -e "${YELLOW}提示: 在宝塔面板中安装 PM2管理器 或手动安装 Node.js${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: 未检测到 npm${NC}"
    exit 1
fi

if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}警告: 未检测到 PM2，正在安装...${NC}"
    npm install -g pm2
    if [ $? -ne 0 ]; then
        echo -e "${RED}PM2 安装失败${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Node.js 版本: $(node --version)${NC}"
echo -e "${GREEN}npm 版本: $(npm --version)${NC}"
echo -e "${GREEN}PM2 版本: $(pm2 --version)${NC}"
echo ""

# 1. 更新代码（可选）
echo -e "${GREEN}[1/8] 检查代码更新...${NC}"
if [ -d ".git" ]; then
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}代码已更新${NC}"
    else
        echo -e "${YELLOW}跳过 Git 更新（可能不是 Git 仓库或无远程配置）${NC}"
    fi
else
    echo -e "${YELLOW}跳过 Git 更新（不是 Git 仓库）${NC}"
fi
echo ""

# 2. 安装后端依赖
echo -e "${GREEN}[2/8] 安装后端依赖...${NC}"
cd backend
npm install --production
if [ $? -ne 0 ]; then
    echo -e "${RED}后端依赖安装失败${NC}"
    exit 1
fi
echo -e "${GREEN}后端依赖安装完成${NC}"
echo ""

# 3. 创建日志目录
echo -e "${GREEN}[3/8] 创建日志目录...${NC}"
mkdir -p logs
echo -e "${GREEN}日志目录已创建${NC}"
echo ""

# 4. 停止旧服务（如果存在）
echo -e "${GREEN}[4/8] 停止旧服务...${NC}"
pm2 stop community-backend 2>/dev/null || true
echo -e "${GREEN}旧服务已停止${NC}"
echo ""

# 5. 启动后端服务
echo -e "${GREEN}[5/8] 启动后端服务...${NC}"
pm2 start ecosystem.config.js
if [ $? -ne 0 ]; then
    echo -e "${RED}后端服务启动失败${NC}"
    echo -e "${YELLOW}查看详细错误: pm2 logs community-backend --err${NC}"
    exit 1
fi
pm2 save
echo -e "${GREEN}后端服务已启动${NC}"
echo ""

# 6. 安装前端依赖
echo -e "${GREEN}[6/8] 安装前端依赖...${NC}"
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}前端依赖安装失败${NC}"
    exit 1
fi
echo -e "${GREEN}前端依赖安装完成${NC}"
echo ""

# 7. 构建前端
echo -e "${GREEN}[7/8] 构建前端...${NC}"
npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}前端构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}前端构建完成${NC}"
echo ""

# 8. 检查服务状态
echo -e "${GREEN}[8/8] 检查服务状态...${NC}"
cd ../backend
pm2 status

echo ""
echo -e "${GREEN}======================================"
echo "✅ 部署完成！"
echo "======================================${NC}"
echo ""
echo -e "${GREEN}后端服务: http://localhost:5000${NC}"
echo -e "${GREEN}前端静态文件: /www/wwwroot/community/frontend/dist${NC}"
echo ""
echo -e "${YELLOW}📋 下一步操作:${NC}"
echo "1. 配置 Nginx 反向代理（参考 BAOTA_DEPLOYMENT.md）"
echo "2. 配置防火墙，开放端口 80 和 443"
echo "3. 申请 SSL 证书（可选但推荐）"
echo "4. 测试网站访问"
echo ""
echo -e "${YELLOW}🔧 常用命令:${NC}"
echo "  查看后端日志: pm2 logs community-backend"
echo "  重启后端服务: pm2 restart community-backend"
echo "  查看服务状态: pm2 status"
echo "  停止服务: pm2 stop community-backend"
echo ""
echo -e "${YELLOW}⚠️  注意事项:${NC}"
echo "1. 确保 frontend/.env.production 中配置了正确的 API 地址"
echo "2. 确保数据库 co_creation_esdk 已创建并可连接"
echo "3. 生产环境建议修改 backend/.env 中的 JWT_SECRET"
echo ""

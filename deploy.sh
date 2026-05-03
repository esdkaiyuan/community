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
if [ ! -f "package.json" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}开始部署...${NC}"
echo ""

# 1. 更新代码
echo -e "${GREEN}[1/7] 更新代码...${NC}"
git pull origin main || git pull origin master
if [ $? -ne 0 ]; then
    echo -e "${RED}代码更新失败，请检查 Git 配置${NC}"
    exit 1
fi

# 2. 安装后端依赖
echo -e "${GREEN}[2/7] 安装后端依赖...${NC}"
cd backend
npm install --production
if [ $? -ne 0 ]; then
    echo -e "${RED}后端依赖安装失败${NC}"
    exit 1
fi

# 3. 创建日志目录
echo -e "${GREEN}[3/7] 创建日志目录...${NC}"
mkdir -p logs

# 4. 重启后端服务
echo -e "${GREEN}[4/7] 重启后端服务...${NC}"
pm2 restart ecosystem.config.js || pm2 start ecosystem.config.js
if [ $? -ne 0 ]; then
    echo -e "${RED}后端服务启动失败${NC}"
    exit 1
fi

# 5. 安装前端依赖
echo -e "${GREEN}[5/7] 安装前端依赖...${NC}"
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}前端依赖安装失败${NC}"
    exit 1
fi

# 6. 构建前端
echo -e "${GREEN}[6/7] 构建前端...${NC}"
npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}前端构建失败${NC}"
    exit 1
fi

# 7. 检查服务状态
echo -e "${GREEN}[7/7] 检查服务状态...${NC}"
cd ../backend
pm2 status

echo ""
echo -e "${GREEN}======================================"
echo "部署完成！"
echo "======================================${NC}"
echo ""
echo "后端服务: http://localhost:5000"
echo "前端地址: /www/wwwroot/community/frontend/dist"
echo ""
echo -e "${YELLOW}提示:${NC}"
echo "1. 请确保 Nginx 已正确配置反向代理"
echo "2. 请确保数据库已创建并导入数据"
echo "3. 查看日志: pm2 logs community-backend"
echo "4. 重启服务: pm2 restart community-backend"
echo ""

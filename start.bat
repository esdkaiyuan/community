@echo off
REM 共创社区平台 - Windows 本地开发环境启动脚本

echo ======================================
echo 共创社区平台 - 开发环境
echo ======================================
echo.

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js v16+
    pause
    exit /b 1
)

echo [1/2] 启动后端服务...
cd backend
start "后端服务" cmd /k "npm run dev"
timeout /t 2 /nobreak >nul

echo [2/2] 启动前端服务...
cd ..\frontend
start "前端服务" cmd /k "npm run dev"

echo.
echo ======================================
echo 服务启动中...
echo ======================================
echo.
echo 后端地址: http://localhost:5000
echo 前端地址: http://localhost:3000
echo.
echo 按任意键关闭此窗口（不会影响已启动的服务）
pause >nul

@echo off
REM ========================================
REM 共创社区平台 - 后端打包脚本
REM ========================================

echo ========================================
echo 共创社区平台 - 后端打包
echo ========================================
echo.

REM 检查是否在后端目录
if not exist "package.json" (
    echo [错误] 请在后端目录运行此脚本
    echo [提示] cd backend
    pause
    exit /b 1
)

echo [1/5] 清理旧文件...
if exist "backend-deploy-*.zip" del /q backend-deploy-*.zip
if exist "node_modules" (
    echo 删除 node_modules...
    rmdir /s /q node_modules
)
echo.

echo [2/5] 安装生产依赖...
call npm install --production
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo 依赖安装完成
echo.

echo [3/5] 检查数据库配置...
if exist ".env" (
    echo 数据库配置:
    findstr "DB_" .env
) else (
    echo [警告] .env 文件不存在
)
echo.

echo [4/5] 创建压缩包...
set timestamp=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
set packageName=backend-deploy-%timestamp%.zip

powershell -Command "Compress-Archive -Path * -DestinationPath %packageName% -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

for %%F in (%packageName%) do set size=%%~zF
set /a sizeMB=%size%/1048576

echo.
echo ========================================
echo ✅ 后端打包完成！
echo ========================================
echo.
echo  文件信息:
echo   文件名: %packageName%
echo   大小: %sizeMB% MB
echo   位置: %CD%\%packageName%
echo.
echo 📋 包含内容:
echo   - src/               后端源代码
echo   - node_modules/      生产依赖
echo   - ecosystem.config.js PM2 配置
echo   - .env               数据库配置
echo   - package.json       项目配置
echo.
echo  下一步:
echo   1. 上传到服务器
echo   2. 解压到 /www/wwwroot/community/backend
echo   3. 执行: pm2 start ecosystem.config.js
echo.

pause

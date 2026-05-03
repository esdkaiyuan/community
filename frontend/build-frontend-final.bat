@echo off
REM ========================================
REM 共创社区平台 - 前端打包脚本
REM ========================================

echo ========================================
echo 共创社区平台 - 前端打包
echo ========================================
echo.

REM 检查是否在前端目录
if not exist "package.json" (
    echo [错误] 请在前端目录运行此脚本
    echo [提示] cd frontend
    pause
    exit /b 1
)

echo [1/5] 检查 dist 目录...
if not exist "dist" (
    echo dist 目录不存在，正在构建...
    call npm run build
    if errorlevel 1 (
        echo [错误] 构建失败
        pause
        exit /b 1
    )
)
echo dist 目录存在
echo.

echo [2/5] 创建部署说明文件...
(
echo # 前端部署说明
echo.
echo ## 数据库配置
echo - 数据库名: co_creation_esdk
echo - 用户名: co_creation_esdk
echo - 密码: GchzPPQ8sM6Rc2Xn
echo - 主机: localhost:3306
echo.
echo ## 部署步骤
echo 1. 上传此压缩包到服务器
echo 2. 解压到网站目录
echo 3. 在宝塔面板配置 Nginx 反向代理
echo.
echo ## Nginx 配置
echo location /api/ {
echo     proxy_pass http://127.0.0.1:5000/;
echo     proxy_http_version 1.1;
echo     proxy_set_header Host $host;
echo     proxy_set_header X-Real-IP $remote_addr;
echo     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
echo }
) > dist\DEPLOY_README.txt
echo 部署说明已创建
echo.

echo [3/5] 创建压缩包...
set timestamp=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
set packageName=frontend-deploy-%timestamp%.zip

powershell -Command "Compress-Archive -Path dist\* -DestinationPath %packageName% -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

for %%F in (%packageName%) do set size=%%~zF
set /a sizeMB=%size%/1048576

echo.
echo ========================================
echo ✅ 前端打包完成！
echo ========================================
echo.
echo 📦 文件信息:
echo   文件名: %packageName%
echo   大小: %sizeMB% MB
echo   位置: %CD%\%packageName%
echo.
echo  包含内容:
echo   - dist/index.html (入口文件)
echo   - dist/assets/ (JS/CSS/图片)
echo   - DEPLOY_README.txt (部署说明)
echo.
echo  下一步:
echo   1. 上传到服务器
echo   2. 解压到网站目录
echo   3. 配置 Nginx 反向代理
echo.

pause

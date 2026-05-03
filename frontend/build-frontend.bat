@echo off
REM 共创社区平台 - 前端构建和打包脚本 (Windows版本)
REM 使用方法: 双击运行 build-frontend.bat

echo ======================================
echo 共创社区平台 - 前端构建打包
echo ======================================
echo.

REM 检查是否在前端目录
if not exist "package.json" (
    echo [错误] 请在前端目录运行此脚本
    echo [提示] cd frontend
    pause
    exit /b 1
)

if not exist "src" (
    echo [错误] 请在前端目录运行此脚本
    echo [提示] cd frontend
    pause
    exit /b 1
)

echo [1/5] 检查环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js
    pause
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 npm
    pause
    exit /b 1
)

echo Node.js 版本:
node --version
echo npm 版本:
npm --version
echo.

echo [2/5] 安装依赖...
call npm install
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [成功] 依赖安装完成
echo.

echo [3/5] 检查配置文件...
if not exist ".env.production" (
    echo [警告] .env.production 不存在，创建默认配置
    echo VITE_API_BASE_URL=/api > .env.production
)

echo API 地址配置:
findstr "VITE_API_BASE_URL" .env.production
echo.

echo [4/5] 开始构建...
call npm run build
if errorlevel 1 (
    echo [错误] 构建失败
    pause
    exit /b 1
)
echo [成功] 构建完成
echo.

echo [5/5] 创建部署包...

REM 获取时间戳
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set VERSION=%datetime:~0,8%_%datetime:~8,6%
set PACKAGE_NAME=frontend-deploy-%VERSION%.zip

REM 检查 dist 目录
if not exist "dist" (
    echo [错误] dist 目录不存在
    pause
    exit /b 1
)

REM 创建临时目录
if exist "temp-frontend-deploy" rmdir /s /q "temp-frontend-deploy"
mkdir temp-frontend-deploy

REM 复制文件
xcopy /E /I /Y "dist\*" "temp-frontend-deploy\" >nul

REM 复制配置文件
if exist ".env.production" copy /Y ".env.production" "temp-frontend-deploy\.env.production.example" >nul

REM 创建 README
(
echo # 前端部署说明
echo.
echo ## 文件说明
echo - index.html: 入口文件
echo - assets/: 静态资源（JS、CSS、图片等）
echo.
echo ## 部署步骤
echo.
echo ### 方法1: Nginx 直接托管（推荐）
echo.
echo 1. 将所有文件上传到 Nginx 网站根目录
echo    例如: /www/wwwroot/your-domain.com/
echo.
echo 2. 配置 Nginx
echo.
echo 3. 重启 Nginx
echo    systemctl restart nginx
echo.
echo ### 方法2: 宝塔面板部署
echo.
echo 1. 在宝塔面板中添加网站
echo 2. 将所有文件上传到网站根目录
echo 3. 配置伪静态（Vue Router history 模式需要）
echo.
echo ## Nginx 配置示例
echo.
echo ```nginx
echo server {
echo     listen 80;
echo     server_name your-domain.com;
echo     root /www/wwwroot/your-domain.com;
echo     index index.html;
echo.
echo     # Vue Router history 模式支持
echo     location / {
echo         try_files $uri $uri/ /index.html;
echo     }
echo.
echo     # API 反向代理
echo     location /api/ {
echo         proxy_pass http://127.0.0.1:5000/;
echo         proxy_set_header Host $host;
echo         proxy_set_header X-Real-IP $remote_addr;
echo         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
echo     }
echo.
echo     # 静态资源缓存
echo     location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
echo         expires 30d;
echo         add_header Cache-Control "public, immutable";
echo     }
echo }
echo ```
echo.
echo ## 注意事项
echo.
echo 1. 确保 .env.production 中配置的 API 地址正确
echo 2. 如果使用 history 模式，必须配置 Nginx 伪静态
echo 3. 建议启用 Gzip 压缩和 HTTPS
echo.
echo ---
echo 构建时间: %date% %time%
) > "temp-frontend-deploy\DEPLOY_README.txt"

REM 创建压缩包
cd temp-frontend-deploy
powershell -Command "Compress-Archive -Path * -DestinationPath ..\%PACKAGE_NAME% -CompressionLevel Optimal"
cd ..

REM 清理临时目录
rmdir /s /q "temp-frontend-deploy"

REM 显示结果
for %%A in (%PACKAGE_NAME%) do set PACKAGE_SIZE=%%~zA
set /a PACKAGE_SIZE_MB=%PACKAGE_SIZE%/1048576

echo.
echo ======================================
echo [成功] 前端部署包创建成功！
echo ======================================
echo.
echo 文件名: %PACKAGE_NAME%
echo 大小: %PACKAGE_SIZE_MB% MB
echo 位置: %CD%\%PACKAGE_NAME%
echo.
echo [下一步操作]
echo 1. 将压缩包上传到服务器
echo 2. 解压到 Nginx 网站根目录
echo 3. 配置 Nginx（参考 DEPLOY_README.txt）
echo 4. 重启 Nginx
echo.
echo [提示]
echo - 确保后端 API 服务已启动（端口 5000）
echo - 配置正确的 API 地址（.env.production）
echo - 建议使用 HTTPS 和 CDN 加速
echo.

pause

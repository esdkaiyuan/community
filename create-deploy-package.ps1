# 共创社区平台 - 部署包创建脚本
# 此脚本会创建一个干净的部署压缩包，排除开发文件和截图

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "共创社区平台 - 创建部署包" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 设置变量
$ProjectRoot = $PSScriptRoot
$DeployPackage = Join-Path $ProjectRoot "community-deploy-v1.0.zip"
$TempDir = Join-Path $ProjectRoot "temp-deploy"

# 清理旧文件
if (Test-Path $DeployPackage) {
    Write-Host "删除旧的部署包..." -ForegroundColor Yellow
    Remove-Item $DeployPackage -Force
}

if (Test-Path $TempDir) {
    Write-Host "清理临时目录..." -ForegroundColor Yellow
    Remove-Item $TempDir -Recurse -Force
}

Write-Host ""
Write-Host "创建临时目录..." -ForegroundColor Green
New-Item -ItemType Directory -Path $TempDir | Out-Null

# 复制必要的文件和目录
Write-Host "复制项目文件..." -ForegroundColor Green

# 后端
Write-Host "  - 后端代码" -ForegroundColor Gray
Copy-Item -Path (Join-Path $ProjectRoot "backend") -Destination (Join-Path $TempDir "backend") -Recurse -Force
# 删除后端的 node_modules
if (Test-Path (Join-Path $TempDir "backend\node_modules")) {
    Remove-Item (Join-Path $TempDir "backend\node_modules") -Recurse -Force
}

# 前端
Write-Host "  - 前端代码" -ForegroundColor Gray
Copy-Item -Path (Join-Path $ProjectRoot "frontend") -Destination (Join-Path $TempDir "frontend") -Recurse -Force
# 删除前端的 node_modules 和 dist
if (Test-Path (Join-Path $TempDir "frontend\node_modules")) {
    Remove-Item (Join-Path $TempDir "frontend\node_modules") -Recurse -Force
}
if (Test-Path (Join-Path $TempDir "frontend\dist")) {
    Remove-Item (Join-Path $TempDir "frontend\dist") -Recurse -Force
}

# 文档
Write-Host "  - 部署文档" -ForegroundColor Gray
$DocsToCopy = @(
    "BAOTA_DEPLOYMENT.md",
    "DEPLOYMENT_CHECKLIST.md",
    "QUICK_REFERENCE.md",
    "README.md",
    "RESPONSIVE_TESTING.md",
    "deploy.sh",
    "start.bat",
    ".gitignore"
)

foreach ($doc in $DocsToCopy) {
    $src = Join-Path $ProjectRoot $doc
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $TempDir $doc) -Force
    }
}

# 创建 README for deployment
Write-Host "  - 创建部署说明" -ForegroundColor Gray
$DeployReadme = @"
# Community Platform - Deployment Package v1.0

## Contents

- Backend source code (backend/)
- Frontend source code (frontend/)
- Deployment documentation
- Configuration files

## Quick Start

### 1. Extract files
```bash
unzip community-deploy-v1.0.zip
cd community
```

### 2. Read deployment docs
- **Full Guide**: BAOTA_DEPLOYMENT.md
- **Checklist**: DEPLOYMENT_CHECKLIST.md
- **Quick Reference**: QUICK_REFERENCE.md

### 3. Database Configuration
Database info (create in Baota panel):
- Database: co_creation_esdk
- Username: co_creation_esdk
- Password: GchzPPQ8sM6Rc2Xn

### 4. Install and Start

#### Backend
```bash
cd backend
npm install --production
pm2 start ecosystem.config.js
```

#### Frontend
```bash
cd ../frontend
npm install
npm run build
```

### 5. Configure Nginx
See BAOTA_DEPLOYMENT.md for Nginx configuration

## Notes

1. Do NOT commit .env files to Git
2. Change JWT_SECRET to a random string in production
3. Configure correct API URL in frontend/.env.production
4. Ensure server has Node.js 16+, MySQL 5.7+, Nginx 1.18+

## Support

For issues, check logs:
- PM2 logs: pm2 logs community-backend
- Nginx logs: /www/wwwlogs/your-domain.com.error.log

---
Version: v1.0
Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

Set-Content -Path (Join-Path $TempDir "DEPLOY_README.md") -Value $DeployReadme -Encoding UTF8

Write-Host ""
Write-Host "创建压缩包..." -ForegroundColor Green
Compress-Archive -Path (Join-Path $TempDir "\*") -DestinationPath $DeployPackage -CompressionLevel Optimal

# 获取文件大小
$FileSize = (Get-Item $DeployPackage).Length / 1MB
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✅ 部署包创建成功！" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "文件位置: $DeployPackage" -ForegroundColor Yellow
Write-Host "文件大小: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 下一步：" -ForegroundColor Cyan
Write-Host "1. 将压缩包上传到服务器" -ForegroundColor White
Write-Host "2. 解压: unzip community-deploy-v1.0.zip" -ForegroundColor White
Write-Host "3. 阅读: DEPLOY_README.md" -ForegroundColor White
Write-Host "4. 按照 BAOTA_DEPLOYMENT.md 进行部署" -ForegroundColor White
Write-Host ""

# 清理临时目录
Write-Host "清理临时文件..." -ForegroundColor Gray
Remove-Item $TempDir -Recurse -Force

Write-Host "完成！" -ForegroundColor Green

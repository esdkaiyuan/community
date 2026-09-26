# ========================================
# Community Platform - MySQL One-Click Install Script
# ========================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "MySQL 8.0 One-Click Install Script" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Check administrator permission
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")
if (-not $isAdmin) {
    Write-Host "[Error] Please run this script as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell -> Run as Administrator`n" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if Chocolatey is installed
Write-Host "[1/6] Checking Chocolatey..." -ForegroundColor Green
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Chocolatey not found, installing..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "[Error] Chocolatey installation failed" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "[OK] Chocolatey installed successfully`n" -ForegroundColor Green
} else {
    Write-Host "[OK] Chocolatey already installed`n" -ForegroundColor Green
}

# Install MySQL
Write-Host "[2/6] Installing MySQL 8.0..." -ForegroundColor Green
choco install mysql -y --params "/Password:root123"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] MySQL installation failed" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[OK] MySQL installed successfully`n" -ForegroundColor Green

# Start MySQL service
Write-Host "[3/6] Starting MySQL service..." -ForegroundColor Green
Start-Service MySQL80
Set-Service MySQL80 -StartupType Automatic
Write-Host "[OK] MySQL service started and set to automatic`n" -ForegroundColor Green

# Wait for service to fully start
Write-Host "[4/6] Waiting for MySQL service..." -ForegroundColor Green
Start-Sleep -Seconds 5

# Test connection
Write-Host "[5/6] Testing MySQL connection..." -ForegroundColor Green
$env:Path += ";C:\Program Files\MySQL\MySQL Server 8.0\bin"

try {
    $result = & mysql -u root -proot123 -e "SELECT 'Connection successful!' AS status;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] MySQL connection test passed`n" -ForegroundColor Green
    } else {
        Write-Host "[Warning] Connection test returned error, service may still be starting" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[Warning] Cannot test connection immediately, please test manually later" -ForegroundColor Yellow
}

# Create database and user
Write-Host "[6/6] Creating community database..." -ForegroundColor Green

$sqlCommands = @"
CREATE DATABASE IF NOT EXISTS co_creation_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'dev_user'@'localhost' IDENTIFIED BY 'dev_password';
GRANT ALL PRIVILEGES ON co_creation_dev.* TO 'dev_user'@'localhost';
FLUSH PRIVILEGES;
"@

try {
    & mysql -u root -proot123 -e "$sqlCommands" 2>&1
    Write-Host "[OK] Database and user created successfully`n" -ForegroundColor Green
} catch {
    Write-Host "[Warning] Database creation may need manual execution" -ForegroundColor Yellow
}

# Complete
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "MySQL Installation Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "MySQL Information:" -ForegroundColor Yellow
Write-Host "  Version: MySQL 8.0" -ForegroundColor White
Write-Host "  Root Password: root123" -ForegroundColor White
Write-Host "  Service Name: MySQL80" -ForegroundColor White
Write-Host "  Port: 3306`n" -ForegroundColor White

Write-Host "Community Database:" -ForegroundColor Yellow
Write-Host "  Database: co_creation_dev" -ForegroundColor White
Write-Host "  Username: dev_user" -ForegroundColor White
Write-Host "  Password: dev_password" -ForegroundColor White
Write-Host "  Host: localhost:3306`n" -ForegroundColor White

Write-Host "Common Commands:" -ForegroundColor Yellow
Write-Host "  Start service: Start-Service MySQL80" -ForegroundColor Gray
Write-Host "  Stop service: Stop-Service MySQL80" -ForegroundColor Gray
Write-Host "  Check status: Get-Service MySQL80" -ForegroundColor Gray
Write-Host "  Connect DB: mysql -u root -proot123" -ForegroundColor Gray
Write-Host "  Connect dev: mysql -u dev_user -pdev_password co_creation_dev`n" -ForegroundColor Gray

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Update backend/.env with database config" -ForegroundColor Gray
Write-Host "  2. Run: cd backend; npm run db:sync" -ForegroundColor Gray
Write-Host "  3. Restart backend service`n" -ForegroundColor Gray

# Update backend config
Write-Host "`nUpdating backend configuration..." -ForegroundColor Green

$envContent = @"
# Server Configuration
PORT=5000
NODE_ENV=development

# Database Configuration (Local MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_USER=dev_user
DB_PASSWORD=dev_password
DB_NAME=co_creation_dev

# JWT Configuration
JWT_SECRET=co_creation_community_secret_key_2024_change_in_production
JWT_EXPIRES_IN=7d
"@

$envContent | Out-File -FilePath "backend\.env" -Encoding UTF8
Write-Host "[OK] Configuration updated: backend\.env`n" -ForegroundColor Green

# Initialize database
Write-Host "`nInitializing database tables..." -ForegroundColor Green
Push-Location backend
npm run db:sync
Pop-Location
Write-Host "[OK] Database tables initialized`n" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All Done! Ready to start the project!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "You can now start the project:" -ForegroundColor Yellow
Write-Host "  cd backend; npm run dev" -ForegroundColor White
Write-Host "  cd frontend; npm run dev`n" -ForegroundColor White

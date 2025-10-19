# ENABLE-WSL-MIRRORED-NETWORKING.ps1
# Enables WSL mirrored networking mode to fix Windows-to-WSL connectivity
# This is the BEST solution for WSL2 networking issues
# Requires: Windows 11 22H2+ or Windows 10 with WSL 2.0.0+

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  ENABLE WSL MIRRORED NETWORKING" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check WSL version
Write-Host "1. Checking WSL version..." -ForegroundColor Cyan
try {
    $wslVersion = wsl --version 2>&1
    Write-Host $wslVersion -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "   ⚠️  Could not determine WSL version" -ForegroundColor Yellow
    Write-Host "   Proceeding anyway..." -ForegroundColor Yellow
    Write-Host ""
}

# Define .wslconfig path
$wslConfigPath = "$env:USERPROFILE\.wslconfig"
Write-Host "2. WSL config file: $wslConfigPath" -ForegroundColor Cyan
Write-Host ""

# Check if .wslconfig exists
$configExists = Test-Path $wslConfigPath
if ($configExists) {
    Write-Host "3. Existing .wslconfig found. Backing up..." -ForegroundColor Yellow
    $backupPath = "$wslConfigPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $wslConfigPath $backupPath
    Write-Host "   ✓ Backup created: $backupPath" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "4. Current .wslconfig content:" -ForegroundColor Cyan
    Get-Content $wslConfigPath | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
    Write-Host ""
} else {
    Write-Host "3. No existing .wslconfig found." -ForegroundColor White
    Write-Host ""
}

# Prepare new configuration
$newConfig = @"
[wsl2]
# Mirrored networking mode - makes WSL2 networking work like WSL1
# This allows Windows to directly access services running in WSL
networkingMode=mirrored

# DNS tunneling - improves DNS resolution
dnsTunneling=true

# Auto proxy - automatically uses Windows proxy settings
autoProxy=true

# Memory settings (optional - adjust based on your system)
memory=8GB
processors=4

# Enable systemd (optional - useful for some services)
# systemd=true
"@

Write-Host "4. New .wslconfig configuration:" -ForegroundColor Cyan
$newConfig -split "`n" | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""

$confirm = Read-Host "Do you want to create/update .wslconfig with mirrored networking? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Configuration cancelled." -ForegroundColor Yellow
    exit 0
}

# Write new configuration
Write-Host ""
Write-Host "5. Writing new .wslconfig..." -ForegroundColor Cyan
$newConfig | Out-File -FilePath $wslConfigPath -Encoding UTF8
Write-Host "   ✓ Configuration written" -ForegroundColor Green
Write-Host ""

# Shutdown WSL to apply changes
Write-Host "6. Shutting down WSL to apply changes..." -ForegroundColor Yellow
Write-Host "   (This will stop all WSL distributions and Docker containers)" -ForegroundColor Yellow
Write-Host ""

$confirmShutdown = Read-Host "Proceed with WSL shutdown? (yes/no)"
if ($confirmShutdown -ne "yes") {
    Write-Host ""
    Write-Host "⚠️  WSL shutdown cancelled." -ForegroundColor Yellow
    Write-Host "   Changes will take effect after you manually run: wsl --shutdown" -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "   Shutting down WSL..." -ForegroundColor Yellow
wsl --shutdown
Start-Sleep -Seconds 5
Write-Host "   ✓ WSL shutdown complete" -ForegroundColor Green
Write-Host ""

Write-Host "7. Starting WSL..." -ForegroundColor Cyan
wsl echo "WSL started with new networking configuration"
Start-Sleep -Seconds 3
Write-Host "   ✓ WSL started" -ForegroundColor Green
Write-Host ""

# Get new WSL IP
Write-Host "8. New WSL IP address:" -ForegroundColor Cyan
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "   $wslIP" -ForegroundColor Green
Write-Host ""

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  CONFIGURATION COMPLETE" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Start your Docker containers in WSL:" -ForegroundColor White
Write-Host "   cd '$PWD'" -ForegroundColor Cyan
Write-Host "   wsl bash -c 'cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d'" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Wait 30 seconds for backend to start" -ForegroundColor White
Write-Host ""
Write-Host "3. Test connectivity:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/api/health/live" -ForegroundColor Cyan
Write-Host "   OR" -ForegroundColor White
Write-Host "   curl http://${wslIP}:8000/api/health/live" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Update UI .env.local:" -ForegroundColor White
Write-Host "   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Start UI:" -ForegroundColor White
Write-Host "   cd ui" -ForegroundColor Cyan
Write-Host "   npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "📖 More info: https://learn.microsoft.com/en-us/windows/wsl/networking#mirrored-mode-networking" -ForegroundColor Gray
Write-Host ""

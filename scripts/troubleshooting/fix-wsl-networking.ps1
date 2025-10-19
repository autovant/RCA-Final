# Fix WSL2 Networking Issues
# This script diagnoses and fixes WSL2 networking problems with Docker containers
# Run as Administrator

#Requires -RunAsAdministrator

Write-Host "RCA WSL2 Networking Diagnostic & Fix" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check .wslconfig
Write-Host "[1/6] Checking WSL configuration..." -ForegroundColor Yellow
$wslConfigPath = "$env:USERPROFILE\.wslconfig"

if (Test-Path $wslConfigPath) {
    $config = Get-Content $wslConfigPath -Raw
    if ($config -match "networkingMode\s*=\s*mirrored") {
        Write-Host "  ✓ Mirrored networking mode is enabled" -ForegroundColor Green
    } else {
        Write-Host "  ! Mirrored networking mode NOT found" -ForegroundColor Yellow
        Write-Host "  Adding mirrored networking to .wslconfig..." -ForegroundColor Yellow
        
        Add-Content -Path $wslConfigPath -Value "`n[wsl2]`nnetworkingMode=mirrored`ndnsTunneling=true`nautoProxy=true"
        Write-Host "  ✓ Configuration updated (WSL restart required)" -ForegroundColor Green
    }
} else {
    Write-Host "  ! No .wslconfig found, creating..." -ForegroundColor Yellow
    @"
[wsl2]
networkingMode=mirrored
dnsTunneling=true
autoProxy=true
memory=8GB
processors=4
"@ | Out-File -FilePath $wslConfigPath -Encoding UTF8
    Write-Host "  ✓ .wslconfig created (WSL restart required)" -ForegroundColor Green
}

# Step 2: Get WSL IP for diagnostic purposes
Write-Host ""
Write-Host "[2/6] Checking WSL network status..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "  WSL IP: $wslIP" -ForegroundColor Cyan

# Step 3: Check for stale Docker containers
Write-Host ""
Write-Host "[3/6] Checking Docker containers..." -ForegroundColor Yellow
$containers = wsl docker ps --format "{{.Names}}|{{.Ports}}" | ConvertFrom-Csv -Delimiter '|' -Header Name,Ports

Write-Host "  Running containers:" -ForegroundColor Cyan
foreach ($container in $containers) {
    Write-Host "    - $($container.Name)" -ForegroundColor White
}

# Step 4: Stop and remove old/duplicate containers
Write-Host ""
Write-Host "[4/6] Cleaning up old containers..." -ForegroundColor Yellow

# Stop all containers first
Write-Host "  Stopping all containers..." -ForegroundColor Cyan
wsl docker stop $(wsl docker ps -aq) 2>$null

# Remove containers that might be using ports
$oldContainers = @('rca_redis_local', 'rca_postgres_local', 'rca-ollama', 'rca-qdrant')
foreach ($container in $oldContainers) {
    Write-Host "  Removing $container if exists..." -ForegroundColor Cyan
    wsl docker rm -f $container 2>$null
}

Write-Host "  ✓ Cleanup complete" -ForegroundColor Green

# Step 5: Check and remove any port proxy rules (not needed with mirrored mode)
Write-Host ""
Write-Host "[5/6] Checking Windows port proxy rules..." -ForegroundColor Yellow
$proxies = netsh interface portproxy show v4tov4

if ($proxies -match "15432|16379") {
    Write-Host "  ! Found port proxy rules (not needed with mirrored mode)" -ForegroundColor Yellow
    Write-Host "  Removing port proxy rules..." -ForegroundColor Cyan
    
    $portsToClean = @(3000, 8000, 8001, 8002, 15432, 16379)
    foreach ($port in $portsToClean) {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=127.0.0.1 2>$null
    }
    Write-Host "  ✓ Port proxy rules removed" -ForegroundColor Green
} else {
    Write-Host "  ✓ No conflicting port proxy rules" -ForegroundColor Green
}

# Step 6: Restart WSL
Write-Host ""
Write-Host "[6/6] Restarting WSL to apply networking changes..." -ForegroundColor Yellow
Write-Host "  This will close all WSL sessions and restart the subsystem..." -ForegroundColor Cyan
Write-Host ""

$response = Read-Host "  Restart WSL now? (Y/N)"
if ($response -eq 'Y' -or $response -eq 'y') {
    Write-Host "  Shutting down WSL..." -ForegroundColor Cyan
    wsl --shutdown
    
    Start-Sleep -Seconds 3
    
    Write-Host "  Starting WSL..." -ForegroundColor Cyan
    wsl echo "WSL restarted successfully"
    
    Write-Host "  ✓ WSL restarted" -ForegroundColor Green
} else {
    Write-Host "  ! Skipped WSL restart" -ForegroundColor Yellow
    Write-Host "  Please run 'wsl --shutdown' manually when ready" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Diagnostic & Fix Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: ./start-environment.ps1" -ForegroundColor White
Write-Host "  2. Access UI at: http://localhost:3000" -ForegroundColor White
Write-Host "  3. Access API at: http://localhost:8001" -ForegroundColor White
Write-Host ""
Write-Host "If problems persist:" -ForegroundColor Yellow
Write-Host "  - Check Windows Firewall settings" -ForegroundColor White
Write-Host "  - Ensure no VPN is interfering" -ForegroundColor White
Write-Host "  - Try: wsl --update" -ForegroundColor White
Write-Host ""

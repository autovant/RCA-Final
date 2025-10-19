#!/usr/bin/env pwsh
# Quick access script - opens the RCA Engine UI in your default browser

Write-Host "`n🚀 RCA Engine - Quick Access`n" -ForegroundColor Cyan

# Check if containers are running
$containersRunning = wsl bash -c "docker ps --filter name=rca_ui --format '{{.Names}}' 2>/dev/null"

if (-not $containersRunning) {
    Write-Host "⚠️  Containers not running. Starting them now..." -ForegroundColor Yellow
    wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d"
    Write-Host "Waiting for services to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

# Try localhost first (works after Windows restart with mirrored networking)
Write-Host "Testing localhost access..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Opening UI at http://localhost:3000`n" -ForegroundColor Green
        Start-Process "http://localhost:3000"
        Start-Process "http://localhost:8000/docs"
        Write-Host "📖 API Docs opened at http://localhost:8000/docs`n" -ForegroundColor Green
        exit 0
    }
} catch {
    Write-Host "❌ Localhost not accessible (Windows restart needed for mirrored networking)" -ForegroundColor Red
}

# Fallback to LAN IP
Write-Host "`nTrying LAN IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Split()[0].Trim()
$uiUrl = "http://${wslIP}:3000"
$apiUrl = "http://${wslIP}:8000/docs"

try {
    $response = Invoke-WebRequest -Uri $uiUrl -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Opening UI at $uiUrl`n" -ForegroundColor Green
        Start-Process $uiUrl
        Start-Process $apiUrl
        Write-Host "📖 API Docs opened at $apiUrl`n" -ForegroundColor Green
        Write-Host "💡 Tip: Restart Windows to enable localhost access (mirrored networking)`n" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "❌ Cannot access UI at $uiUrl" -ForegroundColor Red
    Write-Host "`nTroubleshooting:`n" -ForegroundColor Yellow
    Write-Host "1. Check containers are running:" -ForegroundColor White
    Write-Host "   wsl bash -c `"docker compose -f deploy/docker/docker-compose.yml ps`"`n" -ForegroundColor Gray
    Write-Host "2. View logs:" -ForegroundColor White
    Write-Host "   wsl bash -c `"docker compose -f deploy/docker/docker-compose.yml logs ui`"`n" -ForegroundColor Gray
    Write-Host "3. Restart Windows to enable localhost access`n" -ForegroundColor White
    exit 1
}

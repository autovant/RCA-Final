# Quick Start RCA - Bypass Timeout Issues
# This script starts containers and gives you manual commands for backend/frontend

Write-Host "RCA Quick Start (Manual Mode)" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# Start containers
Write-Host "[Step 1/4] Starting Docker containers..." -ForegroundColor Yellow
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f docker-compose.dev.yml up -d"

Write-Host ""
Write-Host "  Waiting for containers..." -ForegroundColor Gray
Start-Sleep -Seconds 8

# Check container status
Write-Host ""
$containers = wsl docker ps --filter "name=rca_" --format "table {{.Names}}\t{{.Status}}"
Write-Host $containers
Write-Host ""

# Test connection
Write-Host "[Step 2/4] Testing database connection..." -ForegroundColor Yellow
$testResult = Test-NetConnection -ComputerName localhost -Port 15432 -WarningAction SilentlyContinue -InformationLevel Quiet

if ($testResult.TcpTestSucceeded) {
    Write-Host "  ✓ PostgreSQL accessible at localhost:15432" -ForegroundColor Green
} else {
    Write-Host "  ✗ PostgreSQL not accessible!" -ForegroundColor Red
    Write-Host "  Run this command as Administrator: .\fix-docker-port-forwarding.ps1" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Continue anyway? (Y/N)"
    if ($response -ne 'Y' -and $response -ne 'y') {
        exit 1
    }
}

Write-Host ""
Write-Host "[Step 3/4] To start the BACKEND, open a new terminal and run:" -ForegroundColor Yellow
Write-Host "  python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Step 4/4] To start the FRONTEND, open another terminal and run:" -ForegroundColor Yellow
Write-Host "  cd ui" -ForegroundColor Cyan
Write-Host "  npm run dev" -ForegroundColor Cyan
Write-Host ""

Write-Host "==============================" -ForegroundColor Cyan
Write-Host "Access URLs:" -ForegroundColor Green
Write-Host "  UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8001" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8001/docs" -ForegroundColor White
Write-Host ""

$autoStart = Read-Host "Would you like to auto-start backend and frontend now? (Y/N)"

if ($autoStart -eq 'Y' -or $autoStart -eq 'y') {
    Write-Host ""
    Write-Host "Starting backend in new window..." -ForegroundColor Yellow
    
    # Start backend
    Start-Process pwsh -ArgumentList @(
        '-NoExit',
        '-Command',
        "Write-Host 'RCA Backend API - Press Ctrl+C to stop' -ForegroundColor Cyan; python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload"
    ) -WorkingDirectory (Get-Location)
    
    Start-Sleep -Seconds 2
    
    Write-Host "Starting frontend in new window..." -ForegroundColor Yellow
    
    # Start frontend
    Start-Process pwsh -ArgumentList @(
        '-NoExit',
        '-Command',
        "Write-Host 'RCA Frontend UI - Press Ctrl+C to stop' -ForegroundColor Cyan; cd ui; npm run dev"
    ) -WorkingDirectory (Get-Location)
    
    Write-Host ""
    Write-Host "✓ Backend and frontend started in separate windows!" -ForegroundColor Green
    Write-Host "  Wait about 10 seconds, then open http://localhost:3000" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Database containers are running. You can close this window." -ForegroundColor Gray
Write-Host ""

# RCA-Final - Complete Startup Script (WSL Backend + Windows Frontend)

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  RCA-Final - Starting Application                      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Start Backend in WSL
Write-Host "→ Starting Backend in WSL..." -ForegroundColor Cyan
Start-Process -FilePath "wsl" -ArgumentList "bash", "-c", "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && ./start-backend-wsl.sh" -WindowStyle Normal

# Wait for backend to start
Write-Host "→ Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Start Frontend in Windows
Write-Host "→ Starting Frontend..." -ForegroundColor Cyan
Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\ui'; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Application Started!                                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  • Backend API:  " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:8001" -ForegroundColor Green
Write-Host "  • API Docs:     " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:8001/docs" -ForegroundColor Green
Write-Host "  • Frontend:     " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "  • Database:     rca_engine_final (isolated)" -ForegroundColor Cyan
Write-Host "  • Redis DB:     1 (isolated)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two terminal windows have been opened:" -ForegroundColor Yellow
Write-Host "  1. WSL - Backend server" -ForegroundColor Yellow
Write-Host "  2. PowerShell - Frontend server" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop the servers" -ForegroundColor Yellow
Write-Host ""

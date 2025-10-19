# Quick Start for Demos
# Starts everything in separate terminal windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Demo Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
if (-not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: .\setup-dev-environment.ps1" -ForegroundColor Yellow
    exit 1
}

# Start database
Write-Host "Starting database..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml up -d db redis
Start-Sleep -Seconds 3
Write-Host "✓ Database starting" -ForegroundColor Green

# Wait for database
Write-Host "Waiting for database..." -ForegroundColor Yellow
$maxAttempts = 20
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $attempt++
    $healthCheck = docker inspect --format='{{.State.Health.Status}}' rca_db 2>$null
    if ($healthCheck -eq "healthy") {
        break
    }
    Start-Sleep -Seconds 2
}
Write-Host "✓ Database ready" -ForegroundColor Green

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m alembic upgrade head 2>&1 | Out-Null
Write-Host "✓ Migrations complete" -ForegroundColor Green

Write-Host ""
Write-Host "Starting services in new windows..." -ForegroundColor Yellow
Write-Host ""

# Start Backend in new window
Write-Host "Starting Backend API on port 8000..." -ForegroundColor Cyan
$backendScript = @"
Write-Host 'RCA Engine - Backend API' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
cd '$PWD'
& '.\venv\Scripts\activate.ps1'
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
"@
$backendScript | Out-File -FilePath "temp-start-backend.ps1" -Encoding UTF8
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "temp-start-backend.ps1"
Start-Sleep -Seconds 3

# Start UI in new window
Write-Host "Starting UI on port 3000..." -ForegroundColor Cyan
$uiScript = @"
Write-Host 'RCA Engine - Frontend UI' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
cd '$PWD\ui'
npm run dev
"@
$uiScript | Out-File -FilePath "temp-start-ui.ps1" -Encoding UTF8
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "temp-start-ui.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services Starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend will be ready in ~5 seconds at:" -ForegroundColor Yellow
Write-Host "  API:      http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "UI will be ready in ~10 seconds at:" -ForegroundColor Yellow
Write-Host "  UI:       http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Check the new terminal windows for status." -ForegroundColor Gray
Write-Host "Close those windows to stop the services." -ForegroundColor Gray
Write-Host ""

# Wait a moment then open browser
Start-Sleep -Seconds 8
Write-Host "Opening browser..." -ForegroundColor Yellow
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "✓ Demo environment ready!" -ForegroundColor Green
Write-Host ""

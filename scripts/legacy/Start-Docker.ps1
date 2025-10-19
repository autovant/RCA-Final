#Requires -Version 7.0
<#
.SYNOPSIS
    Start RCA Engine with GitHub Copilot Integration (Docker Mode)

.DESCRIPTION
    Starts all services in Docker containers using docker-compose with development overrides.
    - Backend API: localhost:8000
    - Frontend UI: localhost:3000 (Docker)
    - PostgreSQL: localhost:15432
    - Redis: localhost:16379
#>

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  RCA Engine - Docker Startup (GitHub Copilot)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Change to docker directory
$dockerPath = "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker"

Write-Host "→ Stopping any existing containers..." -ForegroundColor Yellow
wsl bash -c "cd '$dockerPath' && docker compose -f docker-compose.yml -f docker-compose.dev.yml down" 2>$null

Write-Host "→ Starting Docker containers (backend only, this takes ~30 seconds)..." -ForegroundColor Yellow
# Start backend services only (not UI - we'll run that on Windows in dev mode)
# Service names: db, redis, rca_core (not rca_db, rca_redis)
$result = wsl bash -c "cd '$dockerPath' && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db redis rca_core" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start Docker containers" -ForegroundColor Red
    Write-Host $result
    exit 1
}

Write-Host "✓ Containers started successfully" -ForegroundColor Green
Write-Host ""

# Wait for services to become healthy
Write-Host "→ Waiting for services to become healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check container status
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Cyan
wsl bash -c "docker ps --filter name=rca --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" | Out-String | Write-Host

# Test backend health
Write-Host ""
Write-Host "→ Testing backend health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health/live" -Method GET -TimeoutSec 5
    if ($health.status -eq "ok") {
        Write-Host "✓ Backend is healthy: $($health.app) v$($health.version)" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Backend health check failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Checking backend logs:" -ForegroundColor Yellow
    wsl bash -c "docker logs rca_core --tail 20"
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Services Running" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend UI:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  PostgreSQL:   localhost:15432" -ForegroundColor Gray
Write-Host "  Redis:        localhost:16379" -ForegroundColor Gray
Write-Host ""
Write-Host "  Provider:     GitHub Copilot (gpt-4)" -ForegroundColor Yellow
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

# Start UI in development mode (Windows)
Write-Host ""
Write-Host "→ Starting UI in development mode..." -ForegroundColor Yellow
$uiPath = Join-Path $PSScriptRoot "ui"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$uiPath'; npm run dev" -WindowStyle Normal

Start-Sleep -Seconds 5

# Open browser
Write-Host "→ Opening browser..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "To view backend logs:" -ForegroundColor Cyan
Write-Host "  wsl bash -c 'docker logs -f rca_core'" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Cyan
Write-Host "  .\Stop-Docker.ps1" -ForegroundColor Gray
Write-Host "  (Then manually close the UI terminal window)" -ForegroundColor Gray
Write-Host ""

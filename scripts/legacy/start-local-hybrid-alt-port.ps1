#Requires -Version 7.0
<#
.SYNOPSIS
    Alternative startup using port 8002 (avoids Windows port conflicts)

.DESCRIPTION
    If port 8001 has access issues, use this script which runs on port 8002 instead.
    Automatically updates all configuration to use 8002.
#>

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = 'Stop'
$BACKEND_PORT = 8002

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message, [string]$Status = "")
    if ($Status -eq "OK") {
        Write-Host "  ✓ $Message" -ForegroundColor Green
    } elseif ($Status -eq "WARN") {
        Write-Host "  ⚠ $Message" -ForegroundColor Yellow
    } elseif ($Status -eq "ERROR") {
        Write-Host "  ✗ $Message" -ForegroundColor Red
    } else {
        Write-Host "  → $Message" -ForegroundColor Cyan
    }
}

Write-Header "RCA Engine - Alternative Port (8002)"

Write-Host "⚠ Using port $BACKEND_PORT to avoid Windows conflicts" -ForegroundColor Yellow
Write-Host ""

# Check setup
if (-not (Test-Path "venv") -or -not (Test-Path "ui\node_modules")) {
    Write-Host "Setup incomplete! Run this first:" -ForegroundColor Red
    Write-Host "  .\setup-local-hybrid.ps1" -ForegroundColor Cyan
    return
}

# Ensure databases are running
Write-Header "Step 1: Database Services"

Write-Step "Checking Docker containers..."
$runningContainers = wsl docker ps --filter "name=rca_" --format "{{.Names}}"
$allContainers = wsl docker ps -a --filter "name=rca_" --format "{{.Names}}"

if ($allContainers -match "rca_db") {
    # Container exists, check if it's running
    if ($runningContainers -notmatch "rca_db") {
        Write-Step "Starting existing database container..."
        wsl docker start rca_db | Out-Null
        Start-Sleep -Seconds 3
        Write-Step "Database container started" "OK"
    } else {
        Write-Step "Database container already running" "OK"
    }
} else {
    # Container doesn't exist, create it
    Write-Step "Creating database containers..."
    wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f docker-compose.dev.yml up -d"
    Start-Sleep -Seconds 8
    Write-Step "Database containers created and started" "OK"
}

# Start Redis if not running
if ($allContainers -match "rca_redis") {
    if ($runningContainers -notmatch "rca_redis") {
        Write-Step "Starting Redis container..."
        wsl docker start rca_redis | Out-Null
        Start-Sleep -Seconds 2
    }
}

# Verify connectivity
Write-Step "Verifying database connectivity..."
$pgTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 15432 -WarningAction SilentlyContinue
if ($pgTest.TcpTestSucceeded) {
    Write-Step "PostgreSQL ready on localhost:15432" "OK"
} else {
    Write-Step "PostgreSQL not accessible - checking port forwarding..." "ERROR"
    Write-Host ""
    Write-Host "Trying to fix port forwarding..." -ForegroundColor Yellow
    wsl docker restart rca_db | Out-Null
    Start-Sleep -Seconds 5
    
    $pgTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 15432 -WarningAction SilentlyContinue
    if ($pgTest.TcpTestSucceeded) {
        Write-Step "PostgreSQL now accessible after restart" "OK"
    } else {
        Write-Step "Still cannot access PostgreSQL - run .\fix-docker-port-forwarding.ps1" "ERROR"
        return
    }
}

# Update UI configuration to use port 8002
Write-Header "Step 2: Configuration"

$uiEnvContent = "NEXT_PUBLIC_API_BASE_URL=http://localhost:$BACKEND_PORT"
$uiEnvContent | Out-File -FilePath "ui\.env.local" -Encoding UTF8 -NoNewline
Write-Step "Updated UI to use port $BACKEND_PORT" "OK"

# Use .env.local if it exists
if (Test-Path ".env.local") {
    Copy-Item ".env.local" ".env" -Force
}

# Start backend
$backendProcess = $null
if (-not $FrontendOnly) {
    Write-Header "Step 3: Starting Backend"
    
    $backendScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA Backend API - Port $BACKEND_PORT' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'API Docs: http://localhost:$BACKEND_PORT/docs' -ForegroundColor Green
Write-Host 'Health:   http://localhost:$BACKEND_PORT/health' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
`$env:PYTHONPATH = '$PSScriptRoot'

python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload
"@

    $scriptPath = Join-Path $env:TEMP "rca-backend-alt.ps1"
    $backendScript | Out-File -FilePath $scriptPath -Encoding UTF8
    
    Write-Step "Launching backend server on port $BACKEND_PORT..."
    $backendProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
    Write-Step "Backend starting (PID: $($backendProcess.Id))" "OK"
    
    Start-Sleep -Seconds 5
}

# Start frontend
$frontendProcess = $null
if (-not $BackendOnly) {
    Write-Header "Step 4: Starting Frontend"
    
    $frontendScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA Frontend UI - Port 3000' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Application: http://localhost:3000' -ForegroundColor Green
Write-Host 'Backend API: http://localhost:$BACKEND_PORT' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

cd ui
npm run dev
"@

    $scriptPath = Join-Path $env:TEMP "rca-frontend-alt.ps1"
    $frontendScript | Out-File -FilePath $scriptPath -Encoding UTF8
    
    Write-Step "Launching frontend server..."
    $frontendProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
    Write-Step "Frontend starting (PID: $($frontendProcess.Id))" "OK"
}

# Save PIDs
$pids = @{}
if ($backendProcess) { $pids.Backend = $backendProcess.Id }
if ($frontendProcess) { $pids.Frontend = $frontendProcess.Id }
$pids | ConvertTo-Json | Out-File -FilePath ".local-pids.json" -Encoding UTF8

# Summary
Write-Header "All Services Running!"

Write-Host "🚀 Your RCA Engine is running on alternative port!" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  • Application:  http://localhost:3000" -ForegroundColor White
Write-Host "  • API:          http://localhost:$BACKEND_PORT" -ForegroundColor White
Write-Host "  • API Docs:     http://localhost:$BACKEND_PORT/docs" -ForegroundColor White
Write-Host "  • Health Check: http://localhost:$BACKEND_PORT/health" -ForegroundColor White
Write-Host ""
Write-Host "⚠ Using port $BACKEND_PORT to avoid Windows conflicts" -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend & Frontend are running in separate windows." -ForegroundColor Gray
Write-Host "Close those windows or run .\stop-local-windows.ps1 to stop." -ForegroundColor Gray
Write-Host ""

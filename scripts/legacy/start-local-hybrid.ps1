#Requires -Version 7.0
<#
.SYNOPSIS
    Start RCA Engine in hybrid mode (Docker databases + native Windows app)

.DESCRIPTION
    The fastest and simplest way to run RCA Engine locally:
    - Uses existing Docker containers for PostgreSQL and Redis
    - Runs backend and frontend natively on Windows
    - No Windows Docker Desktop needed

.EXAMPLE
    .\start-local-hybrid.ps1
#>

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = 'Stop'
$copilotPort = 5001

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

function Get-DotEnvValue {
    param([string]$Key)

    if (-not (Test-Path ".env")) {
        return $null
    }

    $line = Get-Content ".env" | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $value = ($line -split "=", 2)[1].Trim()
    return $value.Trim('"').Trim("'")
}

function Start-CopilotProxy {
    Write-Header "Step 4: GitHub Copilot Proxy"

    if (-not (Test-Path "copilot-to-api-main\server.py")) {
        Write-Step "Copilot proxy server not found - skipping" "WARN"
        return $null
    }

    if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Step "Python environment missing - cannot start Copilot proxy" "WARN"
        return $null
    }

    $token = Get-DotEnvValue "GITHUB_TOKEN"
    if (-not $token -and $env:GITHUB_TOKEN) {
        $token = $env:GITHUB_TOKEN
    }

    if (-not $token) {
        Write-Step "GITHUB_TOKEN not configured; Copilot proxy will fail authentication" "WARN"
    }

    $proxyScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' GitHub Copilot Proxy - Port $copilotPort' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Health: http://localhost:$copilotPort/health' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
python -m pip install --disable-pip-version-check --quiet -r '.\copilot-to-api-main\requirements.txt' | Out-Null

if (-not `$env:GITHUB_TOKEN) {
    Write-Warning 'GITHUB_TOKEN not present; proxy requests will fail until configured.'
}

`$env:PORT = '$copilotPort'
python '.\copilot-to-api-main\server.py'
"@

    $scriptPath = Join-Path $env:TEMP "rca-copilot-proxy.ps1"
    $proxyScript | Out-File -FilePath $scriptPath -Encoding UTF8

    $originalToken = $env:GITHUB_TOKEN
    if ($token) {
        $env:GITHUB_TOKEN = $token
    }

    try {
        Write-Step "Launching Copilot proxy..."
        $process = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
        Write-Step "Copilot proxy starting (PID: $($process.Id))" "OK"
        return $process
    } finally {
        if ($originalToken) {
            $env:GITHUB_TOKEN = $originalToken
        } else {
            Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
        }
    }
}

Write-Header "RCA Engine - Hybrid Local Startup"

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

# Use .env.local if it exists
if (Test-Path ".env.local") {
    Copy-Item ".env.local" ".env" -Force
}

# Ensure UI has correct .env.local
Write-Header "Step 1.5: Frontend Configuration"

$uiEnvPath = "ui\.env.local"
$uiEnvContent = "NEXT_PUBLIC_API_BASE_URL=http://localhost:8001"

if (Test-Path $uiEnvPath) {
    $existingContent = Get-Content $uiEnvPath -Raw
    if ($existingContent -match "localhost:8000") {
        Write-Step "Updating UI .env.local to use port 8001..." "WARN"
        $uiEnvContent | Out-File -FilePath $uiEnvPath -Encoding UTF8 -NoNewline
        Write-Step "UI configuration updated" "OK"
    } else {
        Write-Step "UI .env.local already configured correctly" "OK"
    }
} else {
    Write-Step "Creating UI .env.local with port 8001..."
    $uiEnvContent | Out-File -FilePath $uiEnvPath -Encoding UTF8 -NoNewline
    Write-Step "UI configuration created" "OK"
}

# Start backend
$backendProcess = $null
$copilotProcess = $null
if (-not $FrontendOnly) {
    Write-Header "Step 2: Starting Backend"
    
    $backendScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA Backend API - Port 8001' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'API Docs: http://localhost:8001/docs' -ForegroundColor Green
Write-Host 'Health:   http://localhost:8001/health' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
`$env:PYTHONPATH = '$PSScriptRoot'

python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
"@

    $scriptPath = Join-Path $env:TEMP "rca-backend-hybrid.ps1"
    $backendScript | Out-File -FilePath $scriptPath -Encoding UTF8
    
    Write-Step "Launching backend server..."
    $backendProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
    Write-Step "Backend starting (PID: $($backendProcess.Id))" "OK"
    
    Start-Sleep -Seconds 5
}

# Start Copilot proxy when backend is active
if ($backendProcess) {
    $copilotProcess = Start-CopilotProxy
}

# Start frontend
$frontendProcess = $null
if (-not $BackendOnly) {
    Write-Header "Step 3: Starting Frontend"
    
    $frontendScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA Frontend UI - Port 3000' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Application: http://localhost:3000' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

cd ui
npm run dev
"@

    $scriptPath = Join-Path $env:TEMP "rca-frontend-hybrid.ps1"
    $frontendScript | Out-File -FilePath $scriptPath -Encoding UTF8
    
    Write-Step "Launching frontend server..."
    $frontendProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
    Write-Step "Frontend starting (PID: $($frontendProcess.Id))" "OK"
}

# Save PIDs
$pids = @{}
if ($backendProcess) { $pids.Backend = $backendProcess.Id }
if ($frontendProcess) { $pids.Frontend = $frontendProcess.Id }
if ($copilotProcess) { $pids.CopilotProxy = $copilotProcess.Id }
$pids | ConvertTo-Json | Out-File -FilePath ".local-pids.json" -Encoding UTF8

# Summary
Write-Header "All Services Running!"

Write-Host "🚀 Your RCA Engine is running!" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  • Application:  http://localhost:3000" -ForegroundColor White
Write-Host "  • API:          http://localhost:8001" -ForegroundColor White
Write-Host "  • API Docs:     http://localhost:8001/docs" -ForegroundColor White
Write-Host "  • Health Check: http://localhost:8001/health" -ForegroundColor White
Write-Host "  • Copilot Proxy: http://localhost:$copilotPort" -ForegroundColor White
Write-Host ""
Write-Host "Backend, frontend, and Copilot proxy are running in separate windows." -ForegroundColor Gray
Write-Host "Close those windows or run .\stop-local-windows.ps1 to stop." -ForegroundColor Gray
Write-Host ""
Write-Host "Tip: Code changes will auto-reload!" -ForegroundColor Cyan
Write-Host ""

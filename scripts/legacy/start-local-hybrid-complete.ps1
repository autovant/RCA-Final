#Requires -Version 7.0
<#
.SYNOPSIS
    Complete RCA Engine startup - All components in separate windows

.DESCRIPTION
    Launches all RCA Engine components in separate terminal windows:
    - PostgreSQL & Redis (Docker)
    - Backend API
    - Frontend UI
    - File Watcher Service
    - Copilot API Proxy (optional)

.PARAMETER SkipCopilot
    Skip starting the Copilot API proxy

.PARAMETER SkipWatcher
    Skip starting the file watcher service

.EXAMPLE
    .\start-local-hybrid-complete.ps1
    
.EXAMPLE
    .\start-local-hybrid-complete.ps1 -SkipCopilot
#>

param(
    [switch]$SkipCopilot,
    [switch]$SkipWatcher
)

$ErrorActionPreference = 'Stop'
$BACKEND_PORT = 8002
$COPILOT_PORT = 5001

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

Write-Header "RCA Engine - Complete Startup (All Components)"

# Check setup
if (-not (Test-Path "venv")) {
    Write-Host "❌ Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Run setup first: .\setup-local-hybrid.ps1" -ForegroundColor Yellow
    return
}

if (-not (Test-Path "ui\node_modules")) {
    Write-Host "❌ Frontend dependencies not found!" -ForegroundColor Red
    Write-Host "Run setup first: .\setup-local-hybrid.ps1" -ForegroundColor Yellow
    return
}

# =============================================================================
# Step 1: Database Services
# =============================================================================
Write-Header "Step 1: Database Services"

Write-Step "Checking Docker containers..."
$runningContainers = wsl docker ps --filter "name=rca_" --format "{{.Names}}"
$allContainers = wsl docker ps -a --filter "name=rca_" --format "{{.Names}}"

if ($allContainers -match "rca_db") {
    if ($runningContainers -notmatch "rca_db") {
        Write-Step "Starting existing database container..."
        wsl docker start rca_db | Out-Null
        Start-Sleep -Seconds 3
        Write-Step "Database container started" "OK"
    } else {
        Write-Step "Database container already running" "OK"
    }
} else {
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
    Write-Step "PostgreSQL not accessible - attempting restart..." "WARN"
    wsl docker restart rca_db | Out-Null
    Start-Sleep -Seconds 5
    
    $pgTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 15432 -WarningAction SilentlyContinue
    if ($pgTest.TcpTestSucceeded) {
        Write-Step "PostgreSQL now accessible" "OK"
    } else {
        Write-Step "Cannot access PostgreSQL - run .\fix-docker-port-forwarding.ps1" "ERROR"
        return
    }
}

# =============================================================================
# Step 2: Configuration
# =============================================================================
Write-Header "Step 2: Configuration"

# Update UI configuration
$uiEnvContent = "NEXT_PUBLIC_API_BASE_URL=http://localhost:$BACKEND_PORT"
$uiEnvContent | Out-File -FilePath "ui\.env.local" -Encoding UTF8 -NoNewline
Write-Step "Updated UI to use port $BACKEND_PORT" "OK"

# Use .env.local if it exists
if (Test-Path ".env.local") {
    Copy-Item ".env.local" ".env" -Force
    Write-Step "Using .env.local configuration" "OK"
}

# =============================================================================
# Step 3: Start Backend API
# =============================================================================
Write-Header "Step 3: Starting Backend API"

$backendScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' 🚀 RCA Backend API - Port $BACKEND_PORT' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host '📍 API Docs:  http://localhost:$BACKEND_PORT/docs' -ForegroundColor Green
Write-Host '❤️  Health:    http://localhost:$BACKEND_PORT/health' -ForegroundColor Green
Write-Host '🔄 Hot-reload: Enabled' -ForegroundColor Yellow
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Gray
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
`$env:PYTHONPATH = '$PSScriptRoot'

python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload
"@

$scriptPath = Join-Path $env:TEMP "rca-backend.ps1"
$backendScript | Out-File -FilePath $scriptPath -Encoding UTF8

Write-Step "Launching backend server on port $BACKEND_PORT..."
$backendProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
Write-Step "Backend starting (PID: $($backendProcess.Id))" "OK"

# =============================================================================
# Step 4: Start Frontend UI
# =============================================================================
Write-Header "Step 4: Starting Frontend UI"

$frontendScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' 🎨 RCA Frontend UI - Port 3000' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host '🌐 Application: http://localhost:3000' -ForegroundColor Green
Write-Host '🔧 Backend API: http://localhost:$BACKEND_PORT' -ForegroundColor Green
Write-Host '🔄 Hot-reload:  Enabled' -ForegroundColor Yellow
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Gray
Write-Host ''

cd ui
npm run dev
"@

$scriptPath = Join-Path $env:TEMP "rca-frontend.ps1"
$frontendScript | Out-File -FilePath $scriptPath -Encoding UTF8

Write-Step "Launching frontend server..."
$frontendProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
Write-Step "Frontend starting (PID: $($frontendProcess.Id))" "OK"

# =============================================================================
# Step 5: Start File Watcher (Optional)
# =============================================================================
$watcherProcess = $null
if (-not $SkipWatcher) {
    Write-Header "Step 5: Starting File Watcher Service"
    
    if (Test-Path "scripts\file_watcher.py") {
        $devToken = $null
        if (Test-Path ".env") {
            $tokenLine = Get-Content ".env" | Where-Object { $_ -match '^LOCAL_DEV_AUTH_TOKEN=' } | Select-Object -First 1
            if ($tokenLine) {
                $devToken = ($tokenLine -split "=", 2)[1].Trim('"')
            }
        }

        $tokenExportLine = "# No API auth token detected; uploads will require manual authentication"
        if ($devToken) {
            $tokenExportLine = "`$env:API_AUTH_TOKEN = '$devToken'"
        }

        $watcherScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' 👁️  File Watcher Service' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host '📂 Monitoring directories for new log files' -ForegroundColor Green
Write-Host '🔄 Auto-creates RCA jobs when files detected' -ForegroundColor Green
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Gray
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
`$env:PYTHONPATH = '$PSScriptRoot'
`$env:API_URL = 'http://localhost:$BACKEND_PORT'

`$repoRoot = (Get-Location).Path
`$watchFolder = Join-Path `$repoRoot 'watch-folder'
if (-not (Test-Path `$watchFolder)) {
    New-Item -ItemType Directory -Path `$watchFolder -Force | Out-Null
}
`$env:WATCH_FOLDER = `$watchFolder
`$env:POLL_INTERVAL = '10'
`$env:DEBOUNCE_SECONDS = '5'
`$env:MAX_FILE_SIZE_MB = '100'
`$env:FILE_PATTERNS = '*.log,*.txt,*.json'
$tokenExportLine

python -m scripts.file_watcher
"@

        $scriptPath = Join-Path $env:TEMP "rca-watcher.ps1"
        $watcherScript | Out-File -FilePath $scriptPath -Encoding UTF8
        
        Write-Step "Launching file watcher service..."
        $watcherProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
        Write-Step "File watcher starting (PID: $($watcherProcess.Id))" "OK"
    } else {
        Write-Step "File watcher script not found - skipping" "WARN"
    }
} else {
    Write-Header "Step 5: File Watcher Service"
    Write-Step "Skipped (use without -SkipWatcher to enable)" "WARN"
}

# =============================================================================
# Step 6: Start Copilot API Proxy (Optional)
# =============================================================================
$copilotProcess = $null
if (-not $SkipCopilot) {
    Write-Header "Step 6: Starting Copilot API Proxy"

    if (Test-Path "copilot-to-api-main\server.py") {
        $githubToken = Get-DotEnvValue "GITHUB_TOKEN"
        if (-not $githubToken -and $env:GITHUB_TOKEN) {
            $githubToken = $env:GITHUB_TOKEN
        }

        if (-not $githubToken) {
            Write-Step "GITHUB_TOKEN not configured; Copilot proxy will fail authentication" "WARN"
        }

        $copilotScript = @"
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' 🤖 GitHub Copilot API Proxy' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host "🔌 Proxy URL: http://localhost:$COPILOT_PORT" -ForegroundColor Green
Write-Host '🎯 OpenAI-compatible API for GitHub Copilot' -ForegroundColor Green
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Gray
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
python -m pip install --disable-pip-version-check --quiet -r '.\copilot-to-api-main\requirements.txt' | Out-Null

if (-not `$env:GITHUB_TOKEN) {
    Write-Warning 'GITHUB_TOKEN not present; proxy requests will fail until configured.'
}

`$env:PORT = '$COPILOT_PORT'
python '.\copilot-to-api-main\server.py'
"@

        $scriptPath = Join-Path $env:TEMP "rca-copilot.ps1"
        $copilotScript | Out-File -FilePath $scriptPath -Encoding UTF8

        $originalToken = $env:GITHUB_TOKEN
        if ($githubToken) {
            $env:GITHUB_TOKEN = $githubToken
        }

        try {
            Write-Step "Launching Copilot API proxy..."
            $copilotProcess = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
            Write-Step "Copilot proxy starting (PID: $($copilotProcess.Id))" "OK"
        } finally {
            if ($originalToken) {
                $env:GITHUB_TOKEN = $originalToken
            } else {
                Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-Step "Copilot proxy not found - skipping" "WARN"
    }
} else {
    Write-Header "Step 6: Copilot API Proxy"
    Write-Step "Skipped (use without -SkipCopilot to enable)" "WARN"
}

# =============================================================================
# Save Process IDs
# =============================================================================
$pids = @{
    Backend = $backendProcess.Id
    Frontend = $frontendProcess.Id
}
if ($watcherProcess) { $pids.Watcher = $watcherProcess.Id }
if ($copilotProcess) { $pids.CopilotProxy = $copilotProcess.Id }
$pids | ConvertTo-Json | Out-File -FilePath ".local-pids.json" -Encoding UTF8

# =============================================================================
# Summary
# =============================================================================
Write-Header "✅ All Services Starting!"

Write-Host ""
Write-Host "🚀 RCA Engine is starting with all components!" -ForegroundColor Green
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor White
Write-Host "  Service Map" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor White
Write-Host ""
Write-Host "  🌐 Frontend (UI)" -ForegroundColor Cyan
Write-Host "     http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "  🚀 Backend (API)" -ForegroundColor Cyan
Write-Host "     http://localhost:$BACKEND_PORT" -ForegroundColor White
Write-Host "     http://localhost:$BACKEND_PORT/docs  (API Documentation)" -ForegroundColor Gray
Write-Host "     http://localhost:$BACKEND_PORT/health (Health Check)" -ForegroundColor Gray
Write-Host ""
Write-Host "  🗄️  Databases (Docker)" -ForegroundColor Cyan
Write-Host "     PostgreSQL: localhost:15432" -ForegroundColor White
Write-Host "     Redis:      localhost:16379" -ForegroundColor White
Write-Host "" 
Write-Host "  🤖 Copilot Proxy" -ForegroundColor Cyan
Write-Host "     http://localhost:$COPILOT_PORT" -ForegroundColor White
Write-Host ""

if ($watcherProcess) {
    Write-Host "  👁️  File Watcher" -ForegroundColor Cyan
    Write-Host "     Monitoring for new log files" -ForegroundColor White
    Write-Host ""
}

if ($copilotProcess) {
    Write-Host "  🤖 Copilot API Proxy" -ForegroundColor Cyan
    Write-Host "     http://localhost:$COPILOT_PORT" -ForegroundColor White
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor White
Write-Host ""
Write-Host "📝 Notes:" -ForegroundColor Yellow
Write-Host "  • All services run in separate windows" -ForegroundColor Gray
Write-Host "  • Hot-reload enabled for backend and frontend" -ForegroundColor Gray
Write-Host "  • Close windows or run .\stop-local-hybrid.ps1 to stop" -ForegroundColor Gray
Write-Host "  • Using port $BACKEND_PORT for backend (avoids Windows conflicts)" -ForegroundColor Gray
Write-Host ""
Write-Host "🔍 Process IDs saved to .local-pids.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "⏱️  Give services ~10-15 seconds to fully start" -ForegroundColor Yellow
Write-Host "   Then open: http://localhost:3000" -ForegroundColor Green
Write-Host ""

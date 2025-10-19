#Requires -Version 7.0
<#
.SYNOPSIS
    Start RCA Engine in local Windows mode (No Docker)

.DESCRIPTION
    Starts all RCA Engine services running natively on Windows:
    - PostgreSQL (Windows service)
    - Redis (Windows service/process)
    - FastAPI Backend
    - Next.js Frontend

.EXAMPLE
    .\start-local-windows.ps1
#>

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$SkipHealthCheck,
    [switch]$SkipWatcher
)

$ErrorActionPreference = 'Stop'

# Configuration
$CONFIG = @{
    PostgresPort = "5433"
    RedisPort = "6380"
    BackendPort = "8001"
    FrontendPort = "3000"
    CopilotPort = "5001"
}

# Helper Functions
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

function Test-ServiceRunning {
    param([string]$ServiceName)
    try {
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        return $service -and $service.Status -eq "Running"
    } catch {
        return $false
    }
}

function Test-PortListening {
    param([int]$Port)
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
        return $connection.TcpTestSucceeded
    } catch {
        return $false
    }
}

function Start-ServiceIfNeeded {
    param([string]$ServiceName, [string]$DisplayName)
    
    Write-Step "Checking $DisplayName..."

    try {
        $services = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    } catch {
        Write-Step "$DisplayName service lookup failed: $_" "ERROR"
        return $false
    }

    if (-not $services) {
        Write-Step "$DisplayName service not found" "WARN"
        return $false
    }

    if (-not ($services -is [System.Array])) {
        $services = @($services)
    }

    # Prefer newer PostgreSQL services (15+) when multiple versions are installed
    $preference = @("postgresql-x64-15", "postgresql-x64-16", "postgresql-x64-14")
    $services = $services | Sort-Object {
        $name = $_.Name.ToLower()
        $index = $preference.IndexOf($name)
        if ($index -eq -1) { return 999 }
        return $index
    }, Name

    foreach ($svc in $services) {
        if ($svc.Status -eq "Running") {
            Write-Step "$DisplayName ($($svc.Name)) is running" "OK"
            return $true
        }

        try {
            Write-Step "Starting $DisplayName service ($($svc.Name))..."
            Start-Service -Name $svc.Name -ErrorAction Stop
            Start-Sleep -Seconds 2

            $refreshed = Get-Service -Name $svc.Name -ErrorAction Stop
            if ($refreshed.Status -eq "Running") {
                Write-Step "$DisplayName ($($svc.Name)) is running" "OK"
                return $true
            }
        } catch {
            $message = $_.Exception.Message
            if ($message -match "Cannot open" -or $message -match "Access is denied") {
                Write-Step "Insufficient permissions to control $DisplayName service ($($svc.Name)). Run the startup script in an elevated PowerShell session if service control is required." "WARN"
            } else {
                Write-Step "Failed to start $DisplayName service ($($svc.Name)): $_" "ERROR"
            }
        }
    }

    Write-Step "$DisplayName service found but not running" "WARN"
    return $false
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

function Start-RedisManually {
    Write-Step "Attempting to start Redis manually..."
    
    $redisExe = "C:\Program Files\Redis\redis-server.exe"
    if (Test-Path $redisExe) {
        try {
            # Check if already running
            $existing = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
            if ($existing) {
                Write-Step "Redis is already running (PID: $($existing.Id))" "OK"
                return $true
            }
            
            # Start Redis
            $process = Start-Process -FilePath $redisExe -ArgumentList "--port $($CONFIG.RedisPort)" -PassThru -WindowStyle Hidden
            Start-Sleep -Seconds 2
            
            if ($process -and -not $process.HasExited) {
                Write-Step "Redis started manually (PID: $($process.Id))" "OK"
                return $true
            }
        } catch {
            Write-Step "Failed to start Redis: $_" "ERROR"
        }
    }
    
    Write-Step "Redis executable not found at: $redisExe" "WARN"
    return $false
}

function Test-DatabaseConnection {
    Write-Step "Testing database connection..."
    
    try {
    $env:PGPASSWORD = "rca_local_password"
    $null = & psql -h localhost -p $CONFIG.PostgresPort -U rca_user -d rca_engine -c "SELECT 1;" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Database connection successful" "OK"
            return $true
        }
    } catch {
        # Ignore
    }
    
    Write-Step "Database connection failed" "ERROR"
    return $false
}

function Start-Backend {
    Write-Header "Starting Backend API"
    
    # Check if virtual environment exists
    if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Step "Virtual environment not found!" "ERROR"
        Write-Host ""
        Write-Host "Please run setup-local-windows.ps1 first." -ForegroundColor Yellow
        return $null
    }
    
    # Create backend start script
    $backendScript = @"
# RCA Backend API
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA Backend API - Running on port $($CONFIG.BackendPort)' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'API Documentation: http://localhost:$($CONFIG.BackendPort)/docs' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

# Activate virtual environment
& '.\venv\Scripts\Activate.ps1'

# Set environment
`$env:PYTHONPATH = '$PSScriptRoot'

# Start server
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $($CONFIG.BackendPort) --reload
"@

    $scriptPath = Join-Path $env:TEMP "rca-backend-start.ps1"
    $backendScript | Out-File -FilePath $scriptPath -Encoding UTF8
    
    Write-Step "Starting backend server..."
    $process = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
    
    Start-Sleep -Seconds 3
    Write-Step "Backend started (PID: $($process.Id))" "OK"
    
    return $process
}

function Start-Frontend {
    Write-Header "Starting Frontend UI"
    
    # Check if node_modules exists
    if (-not (Test-Path "ui\node_modules")) {
        Write-Step "Frontend dependencies not found!" "ERROR"
        Write-Host ""
        Write-Host "Please run setup-local-windows.ps1 first." -ForegroundColor Yellow
        return $null
    }
    
    # Create frontend start script
    $frontendScript = @"
# RCA Frontend UI
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA Frontend UI - Running on port $($CONFIG.FrontendPort)' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Application URL: http://localhost:$($CONFIG.FrontendPort)' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

cd ui
npm run dev
"@

    $scriptPath = Join-Path $env:TEMP "rca-frontend-start.ps1"
    $frontendScript | Out-File -FilePath $scriptPath -Encoding UTF8
    
    Write-Step "Starting frontend server..."
    $process = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
    
    Start-Sleep -Seconds 3
    Write-Step "Frontend started (PID: $($process.Id))" "OK"
    
    return $process
}

function Start-FileWatcher {
    Write-Header "Starting File Watcher Service"

    if (-not (Test-Path "scripts\file_watcher.py")) {
        Write-Step "File watcher script not found - skipping" "WARN"
        return $null
    }

    if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Step "Python environment missing - cannot start watcher" "WARN"
        return $null
    }

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
# RCA File Watcher Service
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' RCA File Watcher Service' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Monitoring the configured watch folder for new artefacts' -ForegroundColor Green
Write-Host 'Files that match patterns are uploaded automatically' -ForegroundColor Green
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
`$repoRoot = (Get-Location).Path
`$watchFolder = Join-Path `$repoRoot 'watch-folder'
if (-not (Test-Path `$watchFolder)) {
    New-Item -ItemType Directory -Path `$watchFolder -Force | Out-Null
}

function Start-CopilotProxy {
    Write-Header "Starting GitHub Copilot Proxy"

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

    $copilotScript = @"
# GitHub Copilot Proxy
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ' GitHub Copilot Proxy - Port $($CONFIG.CopilotPort)' -ForegroundColor Cyan
Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan
Write-Host ''
Write-Host 'OpenAI-compatible proxy for GitHub Copilot' -ForegroundColor Green
Write-Host 'Health: http://localhost:$($CONFIG.CopilotPort)/health' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''

& '.\venv\Scripts\Activate.ps1'
python -m pip install --disable-pip-version-check --quiet -r '.\copilot-to-api-main\requirements.txt' | Out-Null

if (-not `$env:GITHUB_TOKEN) {
    Write-Warning 'GITHUB_TOKEN not present; proxy requests will fail until it is configured.'
}

`$env:PORT = '$($CONFIG.CopilotPort)'
python '.\copilot-to-api-main\server.py'
"@

    $scriptPath = Join-Path $env:TEMP "rca-copilot-proxy.ps1"
    $copilotScript | Out-File -FilePath $scriptPath -Encoding UTF8

    $previousToken = $env:GITHUB_TOKEN
    if ($token) {
        $env:GITHUB_TOKEN = $token
    }

    try {
        Write-Step "Launching Copilot proxy..."
        $process = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru
        Write-Step "Copilot proxy starting (PID: $($process.Id))" "OK"
        return $process
    } finally {
        if ($previousToken) {
            $env:GITHUB_TOKEN = $previousToken
        } else {
            Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
        }
    }
}
`$env:PYTHONPATH = `$repoRoot
`$env:API_URL = "http://localhost:$($CONFIG.BackendPort)"
`$env:WATCH_FOLDER = `$watchFolder
`$env:POLL_INTERVAL = '10'
`$env:DEBOUNCE_SECONDS = '5'
`$env:MAX_FILE_SIZE_MB = '100'
`$env:FILE_PATTERNS = '*.log,*.txt,*.json'
$tokenExportLine

python -m scripts.file_watcher
"@

    $scriptPath = Join-Path $env:TEMP "rca-watcher-start.ps1"
    $watcherScript | Out-File -FilePath $scriptPath -Encoding UTF8

    Write-Step "Starting file watcher..."
    $process = Start-Process pwsh -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptPath -WorkingDirectory $PSScriptRoot -PassThru

    Start-Sleep -Seconds 2
    Write-Step "File watcher started (PID: $($process.Id))" "OK"

    return $process
}

function Wait-ForService {
    param([string]$Url, [string]$Name, [int]$TimeoutSeconds = 30)
    
    Write-Step "Waiting for $Name to be ready..."
    
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Step "$Name is ready" "OK"
                return $true
            }
        } catch {
            # Ignore and retry
        }
        
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    
    Write-Step "$Name did not respond within ${TimeoutSeconds}s" "WARN"
    return $false
}

# Main Start Process
function Main {
    Write-Header "RCA Engine - Local Windows Startup"
    
    # Check if setup was run
    if (-not (Test-Path ".env")) {
        Write-Host "Environment not configured!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please run setup-local-windows.ps1 first." -ForegroundColor Yellow
        return
    }
    
    # Start PostgreSQL
    if (-not $FrontendOnly) {
        Write-Header "Step 1: Database Service"
        
        $postgresRunning = Start-ServiceIfNeeded "postgresql*" "PostgreSQL"
        
        if (-not $postgresRunning) {
            Write-Step "PostgreSQL may not be configured as a service" "WARN"
            Write-Host ""
            Write-Host "Please ensure PostgreSQL is running on port $($CONFIG.PostgresPort)" -ForegroundColor Yellow
        }
        
        if (-not $SkipHealthCheck) {
            Test-DatabaseConnection | Out-Null
        }
    }
    
    # Start Redis
    if (-not $FrontendOnly) {
        Write-Header "Step 2: Cache Service"
        
        $redisRunning = Start-ServiceIfNeeded "Redis" "Redis"
        
        if (-not $redisRunning) {
            Start-RedisManually | Out-Null
        }
    }
    
    # Start Backend
    $backendProcess = $null
    $watcherProcess = $null
    $copilotProcess = $null
    if (-not $FrontendOnly) {
        $backendProcess = Start-Backend
        
        if ($backendProcess -and -not $SkipHealthCheck) {
            Wait-ForService "http://localhost:$($CONFIG.BackendPort)/health" "Backend API" | Out-Null
        }

        if (-not $SkipWatcher) {
            $watcherProcess = Start-FileWatcher
        } else {
            Write-Header "File Watcher Service"
            Write-Step "Skipped (use without -SkipWatcher to enable)" "WARN"
        }

        $copilotProcess = Start-CopilotProxy
    }
    
    # Start Frontend
    $frontendProcess = $null
    if (-not $BackendOnly) {
        $frontendProcess = Start-Frontend
        
        if ($frontendProcess -and -not $SkipHealthCheck) {
            Wait-ForService "http://localhost:$($CONFIG.FrontendPort)" "Frontend UI" 60 | Out-Null
        }
    }
    
    # Summary
    Write-Header "All Services Started!"
    
    Write-Host "Your RCA Engine is now running locally on Windows!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access the application:" -ForegroundColor Cyan
    Write-Host "  • Frontend:    http://localhost:$($CONFIG.FrontendPort)" -ForegroundColor White
    Write-Host "  • Backend API: http://localhost:$($CONFIG.BackendPort)" -ForegroundColor White
    Write-Host "  • API Docs:    http://localhost:$($CONFIG.BackendPort)/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  • PostgreSQL:  localhost:$($CONFIG.PostgresPort)" -ForegroundColor White
    Write-Host "  • Redis:       localhost:$($CONFIG.RedisPort)" -ForegroundColor White
    
    if ($backendProcess) {
        Write-Host "  • Backend:     PID $($backendProcess.Id)" -ForegroundColor White
    }
    if ($frontendProcess) {
        Write-Host "  • Frontend:    PID $($frontendProcess.Id)" -ForegroundColor White
    }
    if ($watcherProcess) {
        Write-Host "  • File Watcher: PID $($watcherProcess.Id)" -ForegroundColor White
    }
    if ($copilotProcess) {
        Write-Host "  • Copilot Proxy: PID $($copilotProcess.Id)" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "To stop services, close the terminal windows or run:" -ForegroundColor Yellow
    Write-Host "  .\stop-local-windows.ps1" -ForegroundColor Gray
    Write-Host ""
    
    # Save PIDs for stop script
    $pids = @{}
    if ($backendProcess) { $pids.Backend = $backendProcess.Id }
    if ($frontendProcess) { $pids.Frontend = $frontendProcess.Id }
    if ($watcherProcess) { $pids.Watcher = $watcherProcess.Id }
    if ($copilotProcess) { $pids.CopilotProxy = $copilotProcess.Id }
    
    $pids | ConvertTo-Json | Out-File -FilePath ".local-pids.json" -Encoding UTF8
}

# Run main startup
Main

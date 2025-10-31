#Requires -Version 7.0
<#
.SYNOPSIS
    RCA-Final Complete Startup Script with Port Conflict Detection

.DESCRIPTION
    Launches backend (WSL) and frontend (Windows) in separate terminals
    - Checks for port conflicts (8001, 3000)
    - Offers to kill conflicting processes
    - Validates Docker containers are running
    - Opens browser automatically
    - Provides status monitoring
#>

$ErrorActionPreference = 'Stop'

# Configuration
$BACKEND_PORT = 8001
$FRONTEND_PORT = 3000
$PROJECT_ROOT = $PSScriptRoot
$WSL_PROJECT_PATH = "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final"

# Colors
function Write-Step {
    param([string]$Message, [string]$Status = "INFO")
    $color = switch ($Status) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        default { "Cyan" }
    }
    $symbol = switch ($Status) {
        "OK" { "✓" }
        "WARN" { "!" }
        "ERROR" { "✗" }
        default { "→" }
    }
    Write-Host "  $symbol $Message" -ForegroundColor $color
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Get-ProcessOnPort {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($conn) {
            $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            return @{
                ProcessId = $process.Id
                ProcessName = $process.ProcessName
                Found = $true
            }
        }
        return @{ Found = $false }
    } catch {
        return @{ Found = $false }
    }
}

function Stop-ProcessOnPort {
    param([int]$Port, [string]$ServiceName)
    
    $proc = Get-ProcessOnPort -Port $Port
    if ($proc.Found) {
        Write-Step "Port $Port is in use by $($proc.ProcessName) (PID: $($proc.ProcessId))" "WARN"
        $response = Read-Host "Kill this process to free port $Port for $ServiceName? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            try {
                Stop-Process -Id $proc.ProcessId -Force
                Write-Step "Process killed successfully" "OK"
                Start-Sleep -Seconds 2
                return $true
            } catch {
                Write-Step "Failed to kill process: $_" "ERROR"
                return $false
            }
        } else {
            Write-Step "$ServiceName cannot start on port $Port" "ERROR"
            return $false
        }
    }
    return $true
}

function Test-DockerContainers {
    Write-Step "Checking Docker containers..."
    
    try {
        $containers = wsl docker ps --format "{{.Names}}" 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Step "Docker not running in WSL" "ERROR"
            Write-Host ""
            Write-Host "Please start Docker containers first:" -ForegroundColor Yellow
            Write-Host "  1. Navigate to your other RCA app directory" -ForegroundColor Cyan
            Write-Host "  2. Run: docker-compose up -d" -ForegroundColor Cyan
            return $false
        }
        
        $rca_db = $containers | Select-String "rca_db"
        $rca_redis = $containers | Select-String "rca_redis"
        
        if (-not $rca_db) {
            Write-Step "PostgreSQL container 'rca_db' not running" "ERROR"
            return $false
        }
        if (-not $rca_redis) {
            Write-Step "Redis container 'rca_redis' not running" "ERROR"
            return $false
        }
        
        Write-Step "Docker containers running (rca_db, rca_redis)" "OK"
        return $true
    } catch {
        Write-Step "Error checking Docker: $_" "ERROR"
        return $false
    }
}

function Test-WSLEnvironment {
    Write-Step "Checking WSL Python environment..."
    
    $venvExists = wsl test -d "$WSL_PROJECT_PATH/venv-wsl" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Python venv not found, creating..." "WARN"
        wsl bash -c "cd '$WSL_PROJECT_PATH' && python3 -m venv venv-wsl && source venv-wsl/bin/activate && pip install --quiet -r requirements.txt"
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Python environment created" "OK"
        } else {
            Write-Step "Failed to create Python environment" "ERROR"
            return $false
        }
    } else {
        Write-Step "Python environment ready" "OK"
    }
    return $true
}

function Test-FrontendDependencies {
    Write-Step "Checking frontend dependencies..."
    
    if (-not (Test-Path "$PROJECT_ROOT\ui\node_modules")) {
        Write-Step "Node modules not found, installing..." "WARN"
        Push-Location "$PROJECT_ROOT\ui"
        npm install
        Pop-Location
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Frontend dependencies installed" "OK"
        } else {
            Write-Step "Failed to install dependencies" "ERROR"
            return $false
        }
    } else {
        Write-Step "Frontend dependencies ready" "OK"
    }
    return $true
}

function Start-Backend {
    Write-Header "Starting Backend Server (WSL)"
    
    # Create the startup command
    $wslCommand = "cd '$WSL_PROJECT_PATH' && source venv-wsl/bin/activate && echo '' && echo '╔════════════════════════════════════════════════════════╗' && echo '║  Backend Server (FastAPI/Uvicorn)                      ║' && echo '║  Port: $BACKEND_PORT                                          ║' && echo '║  Press Ctrl+C to stop                                  ║' && echo '╚════════════════════════════════════════════════════════╝' && echo '' && python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload"
    
    # Start Windows Terminal or wt.exe with WSL if available, otherwise use wsl directly
    $hasWindowsTerminal = Get-Command wt.exe -ErrorAction SilentlyContinue
    
    if ($hasWindowsTerminal) {
        Start-Process -FilePath "wt.exe" -ArgumentList "wsl", "bash", "-c", "`"$wslCommand`"" -WindowStyle Normal
    } else {
        # Fallback: Use cmd to launch wsl in new window
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", "wsl", "bash", "-c", "`"$wslCommand`"" -WindowStyle Normal
    }
    
    Write-Step "Backend starting on http://localhost:$BACKEND_PORT" "OK"
}

function Start-Frontend {
    Write-Header "Starting Frontend Server (Windows)"
    
    # Start PowerShell terminal with frontend
    $frontendCommand = @"
Set-Location '$PROJECT_ROOT\ui'
Write-Host ''
Write-Host '╔════════════════════════════════════════════════════════╗' -ForegroundColor Cyan
Write-Host '║  Frontend Server (Next.js)                             ║' -ForegroundColor Cyan
Write-Host '║  Port: $FRONTEND_PORT                                         ║' -ForegroundColor Cyan
Write-Host '║  Press Ctrl+C to stop                                  ║' -ForegroundColor Cyan
Write-Host '╚════════════════════════════════════════════════════════╝' -ForegroundColor Cyan
Write-Host ''
npm run dev
"@
    
    $hasWindowsTerminal = Get-Command wt.exe -ErrorAction SilentlyContinue
    
    if ($hasWindowsTerminal) {
        Start-Process -FilePath "wt.exe" -ArgumentList "pwsh", "-NoExit", "-Command", $frontendCommand -WindowStyle Normal
    } else {
        Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $frontendCommand -WindowStyle Normal
    }
    
    Write-Step "Frontend starting on http://localhost:$FRONTEND_PORT" "OK"
}

function Wait-ForService {
    param([string]$Url, [string]$Name, [int]$MaxAttempts = 30)
    
    Write-Step "Waiting for $Name to be ready..." "INFO"
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Step "$Name is ready! (took $($i*2) seconds)" "OK"
                return $true
            }
        } catch {
            # Service not ready yet
            if ($i % 5 -eq 0) {
                Write-Host "    Still waiting... ($i/$MaxAttempts)" -ForegroundColor DarkGray
            }
        }
        
        if ($i -eq $MaxAttempts) {
            Write-Step "$Name did not respond after $($MaxAttempts*2) seconds" "WARN"
            Write-Step "Check the terminal window for errors" "WARN"
            return $false
        }
        
        Start-Sleep -Seconds 2
    }
    return $false
}

# ═════════════════════════════════════════════════════════
# Main Execution
# ═════════════════════════════════════════════════════════

Clear-Host

Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  RCA-Final Application Launcher                       ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: RCA-Final (Isolated Deployment)" -ForegroundColor Yellow
Write-Host "Database: rca_engine_final | Redis DB: 1" -ForegroundColor Yellow
Write-Host ""

# Step 1: Check Docker Containers
Write-Header "Step 1: Docker Containers"
if (-not (Test-DockerContainers)) {
    Write-Host ""
    Write-Host "❌ Cannot proceed without Docker containers" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Check Port Availability
Write-Header "Step 2: Port Availability"
$backendPortFree = Stop-ProcessOnPort -Port $BACKEND_PORT -ServiceName "Backend"
$frontendPortFree = Stop-ProcessOnPort -Port $FRONTEND_PORT -ServiceName "Frontend"

if (-not $backendPortFree -or -not $frontendPortFree) {
    Write-Host ""
    Write-Host "❌ Cannot proceed with port conflicts" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Step "Ports $BACKEND_PORT and $FRONTEND_PORT are available" "OK"

# Step 3: Check Environments
Write-Header "Step 3: Environment Setup"
if (-not (Test-WSLEnvironment)) {
    Write-Host ""
    Write-Host "❌ WSL environment setup failed" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-FrontendDependencies)) {
    Write-Host ""
    Write-Host "❌ Frontend setup failed" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 4: Start Services
Write-Header "Step 4: Launching Services"
Start-Backend
Start-Sleep -Seconds 5
Start-Frontend
Start-Sleep -Seconds 2

# Step 5: Wait for Services
Write-Header "Step 5: Service Health Check"
$backendReady = Wait-ForService -Url "http://localhost:$BACKEND_PORT/docs" -Name "Backend API"
$frontendReady = Wait-ForService -Url "http://localhost:$FRONTEND_PORT" -Name "Frontend"

# Step 6: Summary
Write-Header "Application Status"

if ($backendReady -and $frontendReady) {
    Write-Host "  🎉 All services are running!" -ForegroundColor Green
} elseif ($backendReady) {
    Write-Host "  ⚠️  Backend is running, Frontend may still be starting..." -ForegroundColor Yellow
} else {
    Write-Host "  ⚠️  Services are starting, please check the terminal windows" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host " Access URLs:" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:       " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:$FRONTEND_PORT" -ForegroundColor White
Write-Host "  Backend API:    " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:$BACKEND_PORT" -ForegroundColor White
Write-Host "  API Docs:       " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:$BACKEND_PORT/docs" -ForegroundColor White
Write-Host "  API Redoc:      " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:$BACKEND_PORT/redoc" -ForegroundColor White
Write-Host ""
Write-Host "  Database:       rca_engine_final (isolated)" -ForegroundColor Cyan
Write-Host "  Redis DB:       1 (isolated)" -ForegroundColor Cyan
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Two terminal windows have been opened:" -ForegroundColor Yellow
Write-Host "  1. WSL Terminal    - Backend (FastAPI)" -ForegroundColor Yellow
Write-Host "  2. PowerShell      - Frontend (Next.js)" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop the application:" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C in each terminal window" -ForegroundColor Cyan
Write-Host ""

# Offer to open browser
$openBrowser = Read-Host "Open browser to http://localhost:$FRONTEND_PORT? (Y/n)"
if ($openBrowser -ne 'n' -and $openBrowser -ne 'N') {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:$FRONTEND_PORT"
}

Write-Host ""
Write-Host "Press Enter to close this launcher window..." -ForegroundColor Gray
Read-Host

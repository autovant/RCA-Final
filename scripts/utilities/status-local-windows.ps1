#Requires -Version 7.0
<#
.SYNOPSIS
    Check the status of all RCA Engine services

.DESCRIPTION
    Shows the current status of all services, ports, and processes

.EXAMPLE
    .\status-local-windows.ps1
#>

$CONFIG = @{
    PostgresPort = 5433
    RedisPort = 6380
    BackendPort = 8001
    FrontendPort = 3000
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
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

function Get-ServiceStatus {
    param([string]$Pattern)
    try {
        $service = Get-Service -Name $Pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($service) {
            return @{
                Found = $true
                Running = $service.Status -eq "Running"
                Name = $service.Name
            }
        }
    } catch {
        # Ignore
    }
    return @{ Found = $false; Running = $false }
}

function Get-ProcessByPort {
    param([int]$Port)
    try {
        $netstat = netstat -ano | Select-String ":$Port\s" | Select-Object -First 1
        if ($netstat) {
            $parts = $netstat.ToString() -split '\s+' | Where-Object { $_ }
            $processId = $parts[-1]
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                return @{
                    Found = $true
                    PID = $processId
                    Name = $process.ProcessName
                }
            }
        }
    } catch {
        # Ignore
    }
    return @{ Found = $false }
}

Write-Header "RCA Engine - Service Status"

# Check environment
Write-Host "Configuration:" -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✓ Environment file exists" -ForegroundColor Green
} else {
    Write-Host "  ✗ Environment file missing - run setup-local-windows.ps1" -ForegroundColor Red
}

if (Test-Path "venv") {
    Write-Host "  ✓ Python virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python virtual environment missing" -ForegroundColor Red
}

if (Test-Path "ui\node_modules") {
    Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  ✗ Frontend dependencies missing" -ForegroundColor Red
}

# Check PostgreSQL
Write-Host ""
Write-Host "PostgreSQL (Port $($CONFIG.PostgresPort)):" -ForegroundColor Yellow
$pgService = Get-ServiceStatus "postgresql*"
if ($pgService.Found) {
    if ($pgService.Running) {
        Write-Host "  ✓ Service: $($pgService.Name) is running" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Service: $($pgService.Name) is stopped" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ Service not found" -ForegroundColor Yellow
}

if (Test-PortListening $CONFIG.PostgresPort) {
    Write-Host "  ✓ Port $($CONFIG.PostgresPort) is listening" -ForegroundColor Green
    
    # Try to connect
    try {
        $env:PGPASSWORD = "rca_local_password"
        $null = & psql -h localhost -p $CONFIG.PostgresPort -U rca_user -d rca_engine -c "SELECT version();" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Database connection successful" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠ Database connection failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Port $($CONFIG.PostgresPort) is not listening" -ForegroundColor Red
}

# Check Redis
Write-Host ""
Write-Host "Redis (Port $($CONFIG.RedisPort)):" -ForegroundColor Yellow
$redisService = Get-ServiceStatus "Redis"
if ($redisService.Found) {
    if ($redisService.Running) {
        Write-Host "  ✓ Service: Redis is running" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Service: Redis is stopped" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ Service not found" -ForegroundColor Yellow
}

if (Test-PortListening $CONFIG.RedisPort) {
    Write-Host "  ✓ Port $($CONFIG.RedisPort) is listening" -ForegroundColor Green
    $process = Get-ProcessByPort $CONFIG.RedisPort
    if ($process.Found) {
        Write-Host "  ✓ Process: $($process.Name) (PID: $($process.PID))" -ForegroundColor Green
    }
} else {
    Write-Host "  ✗ Port $($CONFIG.RedisPort) is not listening" -ForegroundColor Red
}

# Check Backend
Write-Host ""
Write-Host "Backend API (Port $($CONFIG.BackendPort)):" -ForegroundColor Yellow
if (Test-PortListening $CONFIG.BackendPort) {
    Write-Host "  ✓ Port $($CONFIG.BackendPort) is listening" -ForegroundColor Green
    
    $process = Get-ProcessByPort $CONFIG.BackendPort
    if ($process.Found) {
        Write-Host "  ✓ Process: $($process.Name) (PID: $($process.PID))" -ForegroundColor Green
    }
    
    # Try to access health endpoint
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$($CONFIG.BackendPort)/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  ✓ Health check: OK" -ForegroundColor Green
        Write-Host "  ✓ API Docs: http://localhost:$($CONFIG.BackendPort)/docs" -ForegroundColor Cyan
    } catch {
        Write-Host "  ⚠ Health check failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Port $($CONFIG.BackendPort) is not listening" -ForegroundColor Red
    Write-Host "  ℹ Start with: .\start-local-windows.ps1" -ForegroundColor Gray
}

# Check Frontend
Write-Host ""
Write-Host "Frontend UI (Port $($CONFIG.FrontendPort)):" -ForegroundColor Yellow
if (Test-PortListening $CONFIG.FrontendPort) {
    Write-Host "  ✓ Port $($CONFIG.FrontendPort) is listening" -ForegroundColor Green
    
    $process = Get-ProcessByPort $CONFIG.FrontendPort
    if ($process.Found) {
        Write-Host "  ✓ Process: $($process.Name) (PID: $($process.PID))" -ForegroundColor Green
    }
    
    Write-Host "  ✓ Application: http://localhost:$($CONFIG.FrontendPort)" -ForegroundColor Cyan
} else {
    Write-Host "  ✗ Port $($CONFIG.FrontendPort) is not listening" -ForegroundColor Red
    Write-Host "  ℹ Start with: .\start-local-windows.ps1" -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

$pgRunning = Test-PortListening $CONFIG.PostgresPort
$redisRunning = Test-PortListening $CONFIG.RedisPort
$backendRunning = Test-PortListening $CONFIG.BackendPort
$frontendRunning = Test-PortListening $CONFIG.FrontendPort

$allRunning = $pgRunning -and $redisRunning -and $backendRunning -and $frontendRunning

if ($allRunning) {
    Write-Host " Status: All services running! ✓" -ForegroundColor Green
} elseif ($backendRunning -or $frontendRunning) {
    Write-Host " Status: Partially running" -ForegroundColor Yellow
} else {
    Write-Host " Status: Services not running" -ForegroundColor Red
}

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

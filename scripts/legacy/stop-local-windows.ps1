#Requires -Version 7.0
<#
.SYNOPSIS
    Stop all RCA Engine services running locally on Windows

.DESCRIPTION
    Stops all RCA Engine processes and optionally stops database services

.EXAMPLE
    .\stop-local-windows.ps1
    .\stop-local-windows.ps1 -StopServices
#>

param(
    [switch]$StopServices,
    [switch]$Force
)

function Write-Step {
    param([string]$Message, [string]$Status = "")
    if ($Status -eq "OK") {
        Write-Host "  ✓ $Message" -ForegroundColor Green
    } elseif ($Status -eq "WARN") {
        Write-Host "  ⚠ $Message" -ForegroundColor Yellow
    } else {
        Write-Host "  → $Message" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Stopping RCA Engine Services" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Stop tracked processes
if (Test-Path ".local-pids.json") {
    Write-Step "Stopping tracked processes..."
    $pids = Get-Content ".local-pids.json" | ConvertFrom-Json
    
    foreach ($prop in $pids.PSObject.Properties) {
        $name = $prop.Name
        $processId = $prop.Value
        
        try {
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $processId -Force:$Force
                Write-Step "$name (PID: $processId) stopped" "OK"
            } else {
                Write-Step "$name (PID: $processId) not running" "OK"
            }
        } catch {
            Write-Step "Could not stop $name (PID: $processId): $_" "WARN"
        }
    }
    
    Remove-Item ".local-pids.json" -Force
}

# Stop any other RCA-related processes
Write-Step "Checking for other RCA processes..."

# Stop uvicorn processes on port 8001
$uvicornProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*apps.api.main*"
}

foreach ($process in $uvicornProcesses) {
    try {
        Stop-Process -Id $process.Id -Force:$Force
        Write-Step "Stopped backend process (PID: $($process.Id))" "OK"
    } catch {
        Write-Step "Could not stop backend process: $_" "WARN"
    }
}

# Stop Node.js dev server
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*npm*dev*" -or $_.CommandLine -like "*next*dev*"
}

foreach ($process in $nodeProcesses) {
    try {
        Stop-Process -Id $process.Id -Force:$Force
        Write-Step "Stopped frontend process (PID: $($process.Id))" "OK"
    } catch {
        Write-Step "Could not stop frontend process: $_" "WARN"
    }
}

# Stop Redis if requested
if ($StopServices) {
    Write-Host ""
    Write-Step "Stopping services..."
    
    # Stop Redis service
    try {
        $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
        if ($redisService -and $redisService.Status -eq "Running") {
            Stop-Service -Name "Redis"
            Write-Step "Redis service stopped" "OK"
        }
    } catch {
        Write-Step "Could not stop Redis service: $_" "WARN"
    }
    
    # Stop Redis process if running manually
    $redisProcess = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
    if ($redisProcess) {
        Stop-Process -Name "redis-server" -Force:$Force
        Write-Step "Redis process stopped" "OK"
    }
    
    # Note: We don't stop PostgreSQL by default as it might be used by other applications
    Write-Host ""
    Write-Host "Note: PostgreSQL service was not stopped." -ForegroundColor Yellow
    Write-Host "      To stop it manually, run: Stop-Service postgresql*" -ForegroundColor Gray
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Services Stopped" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

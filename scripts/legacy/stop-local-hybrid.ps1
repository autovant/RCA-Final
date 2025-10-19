#Requires -Version 7.0
<#
.SYNOPSIS
    Stop all RCA Engine components

.DESCRIPTION
    Stops all running RCA Engine services started by start-local-hybrid-complete.ps1
#>

$ErrorActionPreference = 'Stop'

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
    } else {
        Write-Host "  → $Message" -ForegroundColor Cyan
    }
}

Write-Header "Stopping RCA Engine Services"

# Check for saved PIDs
if (Test-Path ".local-pids.json") {
    Write-Step "Reading saved process IDs..."
    $pids = Get-Content ".local-pids.json" | ConvertFrom-Json
    
    $stopped = 0
    $failed = 0
    
    foreach ($service in $pids.PSObject.Properties) {
        $serviceName = $service.Name
        $processId = $service.Value
        
        try {
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                Write-Step "Stopping $serviceName (PID: $processId)..."
                Stop-Process -Id $processId -Force -ErrorAction Stop
                $stopped++
                Write-Step "$serviceName stopped" "OK"
            } else {
                Write-Step "$serviceName not running (PID: $processId)" "WARN"
            }
        } catch {
            Write-Step "Failed to stop $serviceName (PID: $processId)" "WARN"
            $failed++
        }
    }
    
    # Remove PID file
    Remove-Item ".local-pids.json" -Force
    Write-Step "Cleaned up PID file" "OK"
    
    Write-Host ""
    Write-Host "Summary: Stopped $stopped service(s)" -ForegroundColor Green
    if ($failed -gt 0) {
        Write-Host "         Failed to stop $failed service(s)" -ForegroundColor Yellow
    }
} else {
    Write-Step "No saved process IDs found" "WARN"
    Write-Host ""
    Write-Host "Searching for RCA-related processes..." -ForegroundColor Yellow
    
    # Try to find and stop related processes
    $processesToStop = @()
    
    # Find Python processes (backend, watcher)
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | 
        Where-Object { $_.Path -like "*RCA-Final*venv*" }
    $processesToStop += $pythonProcesses
    
    # Find Node processes in our directory (frontend, copilot)
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue | 
        Where-Object { $_.Path -like "*RCA-Final*" }
    $processesToStop += $nodeProcesses
    
    if ($processesToStop.Count -gt 0) {
        Write-Host ""
        Write-Host "Found $($processesToStop.Count) RCA-related process(es):" -ForegroundColor Cyan
        foreach ($proc in $processesToStop) {
            Write-Host "  → $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "Stop these processes? (Y/N): " -ForegroundColor Yellow -NoNewline
        $response = Read-Host
        
        if ($response -eq 'Y' -or $response -eq 'y') {
            foreach ($proc in $processesToStop) {
                try {
                    Stop-Process -Id $proc.Id -Force
                    Write-Step "Stopped $($proc.ProcessName) (PID: $($proc.Id))" "OK"
                } catch {
                    Write-Step "Failed to stop $($proc.ProcessName) (PID: $($proc.Id))" "WARN"
                }
            }
        } else {
            Write-Host "Cancelled" -ForegroundColor Yellow
        }
    } else {
        Write-Step "No RCA-related processes found" "OK"
    }
}

# Check if user wants to stop Docker containers
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Stop Docker containers? (Y/N): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -eq 'Y' -or $response -eq 'y') {
    Write-Step "Stopping Docker containers..."
    wsl docker stop rca_db rca_redis 2>$null
    Write-Step "Docker containers stopped" "OK"
} else {
    Write-Host "  → Leaving Docker containers running" -ForegroundColor Cyan
    Write-Host "  → Use 'wsl docker stop rca_db rca_redis' to stop them manually" -ForegroundColor Gray
}

Write-Header "Services Stopped"

Write-Host "✅ RCA Engine services have been stopped" -ForegroundColor Green
Write-Host ""
Write-Host "To start again, run:" -ForegroundColor Cyan
Write-Host "  .\start-local-hybrid-complete.ps1" -ForegroundColor White
Write-Host ""

#Requires -Version 7.0
<#
.SYNOPSIS
    Stop all RCA Engine Docker containers

.DESCRIPTION
    Gracefully stops all Docker containers for the RCA Engine
#>

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Stopping RCA Engine (Docker)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$dockerPath = "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker"

Write-Host "→ Stopping Docker containers..." -ForegroundColor Yellow
wsl bash -c "cd '$dockerPath' && docker compose -f docker-compose.yml -f docker-compose.dev.yml down"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ All containers stopped successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to stop containers" -ForegroundColor Red
}

Write-Host ""
Write-Host "→ Stopping UI processes on port 3000..." -ForegroundColor Yellow
$uiProcesses = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($uiProcesses) {
    foreach ($pid in $uiProcesses) {
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $pid -Force
                Write-Host "✓ Stopped process $($process.Name) (PID: $pid)" -ForegroundColor Green
            }
        } catch {
            Write-Host "✗ Could not stop process PID: $pid" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  No UI processes found on port 3000" -ForegroundColor Gray
}

Write-Host ""

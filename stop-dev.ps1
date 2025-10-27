# Stop Development Environment
# Stops database containers and cleans up temp files

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Stop Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Get-PortListener {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
            $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
            if ($conn) {
                $proc = $null
                try { $proc = Get-Process -Id $conn.OwningProcess -ErrorAction Stop } catch {}
                return [PSCustomObject]@{
                    Port        = $Port
                    ProcessId   = $conn.OwningProcess
                    ProcessName = if ($proc) { $proc.ProcessName } else { $null }
                }
            }
        }
    } catch {}

    try {
        $netstatLine = netstat -ano | Select-String -Pattern "[:\.]$Port\s" | Select-Object -First 1
        if ($netstatLine) {
            $netstatPid = ($netstatLine.Line -split '\s+')[-1]
            $proc = $null
            try { $proc = Get-Process -Id $netstatPid -ErrorAction Stop } catch {}
            return [PSCustomObject]@{
                Port        = $Port
                ProcessId   = [int]$netstatPid
                ProcessName = if ($proc) { $proc.ProcessName } else { $null }
            }
        }
    } catch {}

    return $null
}

function Stop-PortListener {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Description
    )

    $listener = Get-PortListener -Port $Port
    if ($listener) {
        $owner = if ($listener.ProcessName) { "$($listener.ProcessName) (PID $($listener.ProcessId))" } else { "PID $($listener.ProcessId)" }
        Write-Host "Stopping $Description on port $Port ($owner)..." -ForegroundColor Yellow
        
        try {
            Stop-Process -Id $listener.ProcessId -Force -ErrorAction Stop
            Start-Sleep -Milliseconds 500
            Write-Host "  ✓ Process terminated" -ForegroundColor Green
        } catch {
            Write-Host "  WARNING: Could not terminate process: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "$Description (port $Port) - not running" -ForegroundColor Gray
    }
}

# Stop application processes
Write-Host "Stopping application processes..." -ForegroundColor Yellow
Stop-PortListener -Port 8000 -Description "Backend API"
Stop-PortListener -Port 3000 -Description "Frontend UI"
Stop-PortListener -Port 5001 -Description "Copilot Proxy"
Write-Host ""

# Stop database containers
Write-Host "Stopping database containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database containers stopped" -ForegroundColor Green
} else {
    Write-Host "WARNING: Some containers may still be running" -ForegroundColor Yellow
}

# Clean up temp files
Write-Host ""
Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
if (Test-Path "temp-start-backend.ps1") { Remove-Item "temp-start-backend.ps1" -Force }
if (Test-Path "temp-start-ui.ps1") { Remove-Item "temp-start-ui.ps1" -Force }

# Clean up any RCA temp launch scripts
$tempPath = [System.IO.Path]::GetTempPath()
Get-ChildItem -Path $tempPath -Filter "rca-*.ps1" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    } catch {}
}

Write-Host "✓ Cleanup complete" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Services Stopped" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

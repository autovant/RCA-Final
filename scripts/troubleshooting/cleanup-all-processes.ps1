#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Cleanup all RCA Engine processes
.DESCRIPTION
    Stops all Python, Node, and Docker processes related to RCA Engine.
    Use this to recover from orphaned processes or before a fresh start.
.EXAMPLE
    .\cleanup-all-processes.ps1
#>

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Process Cleanup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$cleaned = $false

# Kill Python processes (backend API, worker, Copilot proxy)
Write-Host "Stopping Python processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object {
        Write-Host "  Killing Python PID $($_.Id)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    $cleaned = $true
} else {
    Write-Host "  No Python processes found" -ForegroundColor Gray
}

# Kill Node processes (UI)
Write-Host "Stopping Node processes..." -ForegroundColor Yellow
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    $nodeProcesses | ForEach-Object {
        Write-Host "  Killing Node PID $($_.Id)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    $cleaned = $true
} else {
    Write-Host "  No Node processes found" -ForegroundColor Gray
}

# Check for Docker containers
Write-Host "Checking Docker containers..." -ForegroundColor Yellow
$dockerContainers = docker ps -q 2>$null
if ($dockerContainers) {
    Write-Host "  Found running Docker containers:" -ForegroundColor Gray
    docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"
    $response = Read-Host "  Stop Docker containers? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        docker stop $dockerContainers
        $cleaned = $true
    }
} else {
    Write-Host "  No Docker containers running" -ForegroundColor Gray
}

# Verify ports are free
Write-Host ""
Write-Host "Verifying ports..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$portsInUse = @()
$checkPorts = @(8000, 8001, 3000, 5001)
foreach ($port in $checkPorts) {
    $result = netstat -ano | findstr ":$port.*LISTENING"
    if ($result) {
        $portsInUse += $port
        Write-Host "  ⚠ Port $port still in use:" -ForegroundColor Yellow
        Write-Host "    $result" -ForegroundColor Gray
    }
}

if ($portsInUse.Count -eq 0) {
    Write-Host "  ✓ All RCA ports are free" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "WARNING: Some ports still in use: $($portsInUse -join ', ')" -ForegroundColor Yellow
    Write-Host "You may need to:" -ForegroundColor Yellow
    Write-Host "  1. Close any manual terminal windows" -ForegroundColor Gray
    Write-Host "  2. Wait a few seconds for ports to release" -ForegroundColor Gray
    Write-Host "  3. Run this script again" -ForegroundColor Gray
}

Write-Host ""
if ($cleaned) {
    Write-Host "✓ Cleanup complete! You can now run .\quick-start-dev.ps1" -ForegroundColor Green
} else {
    Write-Host "✓ No processes needed cleanup" -ForegroundColor Green
}
Write-Host ""

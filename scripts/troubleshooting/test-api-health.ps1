#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify RCA Engine API is running correctly
.DESCRIPTION
    Tests all critical API endpoints to ensure the backend is responding properly.
#>

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - API Health Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$apiBase = "http://localhost:8001"
$allPassed = $true

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200
    )
    
    Write-Host "Testing: $Name..." -NoNewline
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -ErrorAction Stop
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host " ✓ PASS ($($response.StatusCode))" -ForegroundColor Green
            return $true
        } else {
            Write-Host " ✗ FAIL (Expected $ExpectedStatus, got $($response.StatusCode))" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host " ✗ FAIL ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

# Test root endpoint
$allPassed = (Test-Endpoint "Root API" "$apiBase/api/") -and $allPassed

# Test health endpoint
$allPassed = (Test-Endpoint "Health Check" "$apiBase/api/health/live") -and $allPassed

# Test docs endpoint
$allPassed = (Test-Endpoint "API Documentation" "$apiBase/api/docs") -and $allPassed

# Verify API info
Write-Host ""
Write-Host "API Information:" -ForegroundColor Yellow
try {
    $apiInfo = Invoke-RestMethod -Uri "$apiBase/api/"
    Write-Host "  Title: $($apiInfo.message)" -ForegroundColor Gray
    Write-Host "  Version: $($apiInfo.version)" -ForegroundColor Gray
    Write-Host "  Status: $($apiInfo.status)" -ForegroundColor Gray
    
    if ($apiInfo.message -ne "RCA Engine") {
        Write-Host "  ⚠ WARNING: Unexpected API title" -ForegroundColor Yellow
        $allPassed = $false
    }
}
catch {
    Write-Host "  ✗ Failed to get API info" -ForegroundColor Red
    $allPassed = $false
}

# Check port conflicts
Write-Host ""
Write-Host "Port Status:" -ForegroundColor Yellow
$port8001 = netstat -ano | findstr ":8001.*LISTENING"
if ($port8001) {
    $processCount = ($port8001 | Measure-Object).Count
    if ($processCount -eq 1) {
        Write-Host "  ✓ Port 8001: Single process (good)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Port 8001: Multiple processes detected ($processCount)" -ForegroundColor Yellow
        Write-Host "    Run .\scripts\troubleshooting\cleanup-all-processes.ps1" -ForegroundColor Gray
        $allPassed = $false
    }
} else {
    Write-Host "  ✗ Port 8001: No process listening" -ForegroundColor Red
    $allPassed = $false
}

# Check if worker is running
Write-Host ""
Write-Host "Worker Status:" -ForegroundColor Yellow
$workerProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*apps.worker.main*"
}

if ($workerProcess) {
    Write-Host "  ✓ Worker process running (PID $($workerProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Worker process not found" -ForegroundColor Yellow
    Write-Host "    Uploads will queue but won't process automatically" -ForegroundColor Gray
    Write-Host "    Run: .\quick-start-dev.ps1 (without -NoWorker)" -ForegroundColor Gray
}

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allPassed -and $workerProcess) {
    Write-Host "  ✓ ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host "  Ready to accept uploads!" -ForegroundColor Green
} elseif ($allPassed) {
    Write-Host "  ⚠ API OK, but worker missing" -ForegroundColor Yellow
    Write-Host "  Files will upload but won't process" -ForegroundColor Yellow
} else {
    Write-Host "  ✗ ISSUES DETECTED" -ForegroundColor Red
    Write-Host "  Review errors above" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

exit $(if ($allPassed) { 0 } else { 1 })

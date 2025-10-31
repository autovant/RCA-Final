#Requires -Version 7.0
<#
.SYNOPSIS
    Verify port configuration is correct

.DESCRIPTION
    Checks all configuration files to ensure they use port 8001 for the backend API
#>

$ErrorActionPreference = 'Stop'

function Write-Check {
    param([string]$Message, [bool]$Pass)
    if ($Pass) {
        Write-Host "  ✓ $Message" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Message" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Port Configuration Verification" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check UI .env.local
Write-Host "Checking UI Environment..." -ForegroundColor Yellow
if (Test-Path "ui\.env.local") {
    $content = Get-Content "ui\.env.local" -Raw
    $hasCorrectPort = $content -match "localhost:8001"
    $hasWrongPort = $content -match "localhost:8000"
    
    if ($hasCorrectPort -and -not $hasWrongPort) {
        Write-Check "ui\.env.local uses port 8001" $true
    } else {
        Write-Check "ui\.env.local has wrong port" $false
        $allGood = $false
        Write-Host "    Fix: echo 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8001' | Out-File ui\.env.local -Encoding UTF8" -ForegroundColor Yellow
    }
} else {
    Write-Check "ui\.env.local exists" $false
    $allGood = $false
    Write-Host "    Fix: Run .\start-local-hybrid.ps1 to create it" -ForegroundColor Yellow
}

# Check jobsPreview.ts
Write-Host ""
Write-Host "Checking Source Files..." -ForegroundColor Yellow
if (Test-Path "ui\src\data\jobsPreview.ts") {
    $content = Get-Content "ui\src\data\jobsPreview.ts" -Raw
    $hasCorrectPort = $content -match 'localhost:8001'
    $hasWrongPort = $content -match 'localhost:8000'
    
    if ($hasCorrectPort -and -not $hasWrongPort) {
        Write-Check "jobsPreview.ts uses port 8001" $true
    } else {
        Write-Check "jobsPreview.ts has wrong port" $false
        $allGood = $false
    }
} else {
    Write-Check "jobsPreview.ts not found" $false
    $allGood = $false
}

# Check if backend is running
Write-Host ""
Write-Host "Checking Running Services..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing 2>$null
    Write-Check "Backend responding on port 8001" $true
} catch {
    Write-Check "Backend not running on port 8001" $false
    Write-Host "    This is OK if you haven't started it yet" -ForegroundColor Gray
}

# Check if anything is on port 8000 (shouldn't be)
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing 2>$null
    Write-Check "Nothing running on old port 8000" $false
    Write-Host "    Warning: Something is still using port 8000" -ForegroundColor Yellow
} catch {
    Write-Check "Nothing running on old port 8000" $true
}

# Check frontend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 2 -UseBasicParsing 2>$null
    Write-Check "Frontend responding on port 3000" $true
} catch {
    Write-Check "Frontend not running on port 3000" $false
    Write-Host "    This is OK if you haven't started it yet" -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($allGood) {
    Write-Host " ✓ All configuration files are correct!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now start the application:" -ForegroundColor Cyan
    Write-Host "  .\start-local-hybrid.ps1" -ForegroundColor White
} else {
    Write-Host " ✗ Some configuration issues found" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Quick fix:" -ForegroundColor Yellow
    Write-Host "  .\start-local-hybrid.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "The startup script will automatically fix configuration issues." -ForegroundColor Gray
}
Write-Host ""

# RCA Engine - Port Forwarding Launcher
# This script will launch the admin script with elevated privileges

$scriptPath = Join-Path $PSScriptRoot "setup-ports-admin.ps1"

Write-Host "`n🚀 RCA Engine - Port Forwarding Setup" -ForegroundColor Cyan
Write-Host "=====================================`n" -ForegroundColor Cyan

if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Error: Could not find setup-ports-admin.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "This will open an Administrator PowerShell window..." -ForegroundColor Yellow
Write-Host "Please approve the UAC prompt to continue.`n" -ForegroundColor Yellow

Start-Sleep -Seconds 2

# Launch elevated PowerShell with the admin script
Start-Process powershell.exe -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$scriptPath`"" -Verb RunAs

Write-Host "✓ Admin script launched!`n" -ForegroundColor Green
Write-Host "Follow the instructions in the Administrator window.`n" -ForegroundColor Cyan

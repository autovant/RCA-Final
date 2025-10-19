#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Update port forwarding for backend (port 8001) with current WSL IP
#>

$ErrorActionPreference = 'Stop'

Write-Host "`n╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Update Port Forwarding for Backend (8001)        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get current WSL IP
Write-Host "Getting current WSL IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Trim().Split()[0]
Write-Host "  Current WSL IP: $wslIP" -ForegroundColor Cyan

# Check existing rule
Write-Host "`nChecking existing port forwarding..." -ForegroundColor Yellow
$existing = netsh interface portproxy show all | Select-String "8001"
if ($existing) {
    Write-Host "  Existing rule found:" -ForegroundColor Gray
    Write-Host "  $existing" -ForegroundColor Gray
}

# Remove existing rule
Write-Host "`nRemoving old port forwarding rule..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0 2>$null | Out-Null
Write-Host "  ✓ Old rule removed" -ForegroundColor Green

# Add new rule with current IP
Write-Host "`nAdding new port forwarding rule..." -ForegroundColor Yellow
Write-Host "  localhost:8001 -> ${wslIP}:8001" -ForegroundColor Gray
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP
Write-Host "  ✓ Port forwarding updated" -ForegroundColor Green

# Ensure firewall rule exists
Write-Host "`nEnsuring firewall rule exists..." -ForegroundColor Yellow
$ruleName = "RCA-Backend-8001"
$existingFirewallRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existingFirewallRule) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow | Out-Null
    Write-Host "  ✓ Firewall rule created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Firewall rule already exists" -ForegroundColor Green
}

# Verify rule
Write-Host "`nVerifying port forwarding..." -ForegroundColor Yellow
$verified = netsh interface portproxy show all | Select-String "8001"
Write-Host "  Current rule: $verified" -ForegroundColor Cyan

# Test connection
Write-Host "`nTesting connection..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/jobs" -UseBasicParsing -TimeoutSec 5
    Write-Host "`n╔════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✓ SUCCESS! Backend is accessible!                ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host "`n  URL: http://localhost:8001" -ForegroundColor Cyan
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Cyan
    Write-Host "`n🎉 Now refresh your browser at http://localhost:3000" -ForegroundColor Yellow
} catch {
    Write-Host "`n⚠️  Backend not responding yet" -ForegroundColor Yellow
    Write-Host "   Error: $_" -ForegroundColor Gray
    Write-Host "`n   This is normal if:" -ForegroundColor Cyan
    Write-Host "   - Backend is still starting up in WSL" -ForegroundColor Cyan
    Write-Host "   - Backend crashed or needs to be restarted" -ForegroundColor Cyan
    Write-Host "`n   Check the WSL terminal where backend is running" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"

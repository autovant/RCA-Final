#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Setup port forwarding for backend (port 8001) from WSL to Windows
#>

$ErrorActionPreference = 'Stop'

Write-Host "`n╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Setup Port Forwarding for Backend (8001)         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get WSL IP
Write-Host "Getting WSL IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Trim().Split()[0]
Write-Host "  WSL IP: $wslIP" -ForegroundColor Cyan

# Remove existing rule
Write-Host "`nRemoving existing port forwarding..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0 2>$null | Out-Null
Write-Host "  ✓ Cleaned up" -ForegroundColor Green

# Add new rule
Write-Host "`nAdding port forwarding rule..." -ForegroundColor Yellow
Write-Host "  localhost:8001 -> $wslIP:8001" -ForegroundColor Gray
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP
Write-Host "  ✓ Port forwarding configured" -ForegroundColor Green

# Add firewall rule
Write-Host "`nConfiguring firewall..." -ForegroundColor Yellow
$ruleName = "RCA-Backend-8001"
Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow | Out-Null
Write-Host "  ✓ Firewall rule added" -ForegroundColor Green

# Test connection
Write-Host "`nTesting connection..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/jobs" -UseBasicParsing -TimeoutSec 5
    Write-Host "  ✓ Backend is accessible at http://localhost:8001" -ForegroundColor Green
    Write-Host "  Status Code: $($response.StatusCode)" -ForegroundColor Cyan
} catch {
    Write-Host "  ✗ Backend not responding yet" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Gray
    Write-Host "`n  Note: Make sure backend is running in WSL terminal" -ForegroundColor Yellow
}

Write-Host "`n╔════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Port Forwarding Setup Complete                    ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Backend should now be accessible at: http://localhost:8001" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"

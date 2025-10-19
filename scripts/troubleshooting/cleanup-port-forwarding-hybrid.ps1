#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Remove unnecessary port forwarding rules for hybrid deployment

.DESCRIPTION
    When running backend and frontend natively on Windows, we don't need
    port forwarding for ports 8001 (backend) and 3000 (frontend).
    This script removes those rules while keeping database port forwarding.
#>

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Cleanup Port Forwarding for Hybrid Deployment" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Remove port 8001 (backend - now running natively on Windows)
Write-Host "→ Removing port 8001 forwarding..." -ForegroundColor Yellow
try {
    netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0 2>$null
    Write-Host "✓ Port 8001 forwarding removed" -ForegroundColor Green
} catch {
    Write-Host "  (Port 8001 forwarding may not exist)" -ForegroundColor DarkGray
}

# Remove port 3000 (frontend - now running natively on Windows)
Write-Host "→ Removing port 3000 forwarding..." -ForegroundColor Yellow
try {
    netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0 2>$null
    Write-Host "✓ Port 3000 forwarding removed" -ForegroundColor Green
} catch {
    Write-Host "  (Port 3000 forwarding may not exist)" -ForegroundColor DarkGray
}

# Show remaining rules
Write-Host ""
Write-Host "Remaining port forwarding rules (databases only):" -ForegroundColor Cyan
netsh interface portproxy show v4tov4

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Done!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now start the hybrid deployment:" -ForegroundColor White
Write-Host "  .\start-local-hybrid.ps1" -ForegroundColor Cyan
Write-Host ""

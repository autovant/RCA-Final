# Enable Network Access from Windows to WSL
# Run this as Administrator ONCE after starting Docker

Write-Host "Setting up network access..." -ForegroundColor Cyan

# Check if admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: Must run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell → 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "Then run: .\ENABLE-NETWORK-ACCESS.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Or run these commands in Admin PowerShell:" -ForegroundColor Yellow
    Write-Host '  $wslIP = (wsl hostname -I).Split()[0].Trim()' -ForegroundColor White
    Write-Host '  netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP' -ForegroundColor White
    Write-Host '  New-NetFirewallRule -DisplayName "WSL Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow' -ForegroundColor White
    exit 1
}

# Get WSL IP
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "WSL IP: $wslIP" -ForegroundColor Green

# Remove old rules
Write-Host "Cleaning up old rules..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null
Remove-NetFirewallRule -DisplayName "WSL Backend*" -ErrorAction SilentlyContinue

# Add port forwarding
Write-Host "Setting up port forwarding..." -ForegroundColor Yellow
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Port forwarding: localhost:8000 → ${wslIP}:8000" -ForegroundColor Green
}

# Add firewall rule
Write-Host "Adding firewall rule..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "WSL Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow | Out-Null

if ($?) {
    Write-Host "✓ Firewall rule added" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Network Access Enabled!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now access the backend at:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "Test it:" -ForegroundColor Yellow
Write-Host "  curl http://localhost:8000/api/health/live" -ForegroundColor White
Write-Host ""
Write-Host "Note: Run this script again if WSL restarts" -ForegroundColor Gray
Write-Host ""

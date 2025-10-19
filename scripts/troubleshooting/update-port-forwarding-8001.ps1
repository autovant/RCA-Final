# Quick update to switch from port 8000 to 8001
# Run as Administrator

Write-Host "Updating port forwarding from 8000 to 8001..." -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run these commands in an Admin PowerShell:" -ForegroundColor Yellow
    Write-Host '  $wslIP = (wsl hostname -I).Split()[0].Trim()' -ForegroundColor White
    Write-Host '  netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0' -ForegroundColor White
    Write-Host '  netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP' -ForegroundColor White
    Write-Host ""
    exit 1
}

# Get WSL2 IP address
$wslIP = (wsl hostname -I).Split()[0].Trim()

if ([string]::IsNullOrWhiteSpace($wslIP)) {
    Write-Host "ERROR: Could not get WSL2 IP address" -ForegroundColor Red
    exit 1
}

Write-Host "WSL2 IP: $wslIP" -ForegroundColor Green

# Remove old port 8000 forwarding
Write-Host "Removing port 8000 forwarding..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=127.0.0.1 2>$null

# Add new port 8001 forwarding
Write-Host "Adding port 8001 forwarding..." -ForegroundColor Yellow
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Port 8001 forwarded successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to forward port 8001" -ForegroundColor Red
}

Write-Host ""
Write-Host "Current port forwarding:" -ForegroundColor Cyan
netsh interface portproxy show v4tov4

Write-Host ""
Write-Host "✓ Done! Backend is now on port 8001" -ForegroundColor Green
Write-Host "  API: http://localhost:8001" -ForegroundColor White

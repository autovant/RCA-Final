# Fix WSL2 Port Forwarding for Docker
# This script sets up port forwarding from Windows to WSL2 Docker containers
# Run as Administrator

Write-Host "WSL2 Docker Port Forwarding Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Get WSL2 IP address
Write-Host "Getting WSL2 IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Split()[0].Trim()

if ([string]::IsNullOrWhiteSpace($wslIP)) {
    Write-Host "ERROR: Could not get WSL2 IP address" -ForegroundColor Red
    exit 1
}

Write-Host "WSL2 IP: $wslIP" -ForegroundColor Green
Write-Host ""

# Define ports to forward
$ports = @(3000, 8001, 8002, 15432)
$portNames = @{
    3000 = "UI (Next.js)"
    8001 = "API (FastAPI)"
    8002 = "Metrics"
    15432 = "PostgreSQL"
}

# Remove existing port proxies
Write-Host "Removing existing port proxies..." -ForegroundColor Yellow
foreach ($port in $ports) {
    try {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=127.0.0.1 2>$null
    } catch {
        # Ignore errors if proxy doesn't exist
    }
}

# Add new port proxies
Write-Host "Setting up port forwarding..." -ForegroundColor Yellow
foreach ($port in $ports) {
    $serviceName = $portNames[$port]
    Write-Host "  Port $port - $serviceName" -ForegroundColor Cyan
    
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIP
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Forwarded successfully" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Failed to forward" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Current port forwarding configuration:" -ForegroundColor Cyan
netsh interface portproxy show v4tov4

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now access your application at:" -ForegroundColor Yellow
Write-Host "  UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8001" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8001/docs" -ForegroundColor White
Write-Host ""
Write-Host "Note: If WSL2 restarts, you'll need to run this script again" -ForegroundColor Yellow
Write-Host "      (WSL2 IP addresses can change on restart)" -ForegroundColor Yellow

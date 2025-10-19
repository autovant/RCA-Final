# RCA Engine - Quick Fix Port Forwarding
# This script MUST be run as Administrator

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RCA Engine - Port Forwarding Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ ERROR: This script must be run as Administrator!`n" -ForegroundColor Red
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell" -ForegroundColor White
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "3. Navigate to this directory and run:" -ForegroundColor White
    Write-Host "   .\setup-ports-admin.ps1`n" -ForegroundColor Gray
    Read-Host "Press Enter to exit"
    exit 1
}

# Get WSL2 IP address
Write-Host "Getting WSL2 IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Split()[0].Trim()

if ([string]::IsNullOrWhiteSpace($wslIP)) {
    Write-Host "❌ ERROR: Could not get WSL2 IP address" -ForegroundColor Red
    Write-Host "Make sure WSL is running" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ WSL2 IP: $wslIP`n" -ForegroundColor Green

# Remove old port proxies
Write-Host "Removing old port forwarding rules..." -ForegroundColor Yellow
$ports = @(3000, 8000, 8001, 15432, 16379)
foreach ($port in $ports) {
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null | Out-Null
}

# Add new port proxies
Write-Host "Setting up port forwarding...`n" -ForegroundColor Yellow

$portNames = @{
    3000 = "UI (Next.js)"
    8000 = "API (FastAPI)"
    8001 = "Metrics"
    15432 = "PostgreSQL"
    16379 = "Redis"
}

foreach ($port in $ports) {
    $serviceName = $portNames[$port]
    Write-Host "  Port $port - $serviceName" -ForegroundColor Cyan
    
    $result = netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIP 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Forwarded successfully" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Failed: $result" -ForegroundColor Red
    }
}

# Add Windows Firewall rules
Write-Host "`nConfiguring Windows Firewall..." -ForegroundColor Yellow

$firewallRules = @(
    @{Name="RCA Engine UI"; Port=3000},
    @{Name="RCA Engine API"; Port=8000},
    @{Name="RCA Engine Metrics"; Port=8001},
    @{Name="RCA Engine DB"; Port=15432},
    @{Name="RCA Engine Redis"; Port=16379}
)

foreach ($rule in $firewallRules) {
    # Remove old rule
    netsh advfirewall firewall delete rule name="$($rule.Name)" 2>$null | Out-Null
    
    # Add new rule
    $result = netsh advfirewall firewall add rule name="$($rule.Name)" dir=in action=allow protocol=TCP localport=$($rule.Port) 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Firewall rule added: $($rule.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to add firewall rule: $($rule.Name)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Current Port Forwarding Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
netsh interface portproxy show v4tov4

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "You can now access your application at:`n" -ForegroundColor Yellow
Write-Host "  UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs`n" -ForegroundColor White

Write-Host "⚠️  Note: If WSL2 restarts, you'll need to run this script again" -ForegroundColor Yellow
Write-Host "    (WSL2 IP addresses can change on restart)`n" -ForegroundColor Yellow

# Test connectivity
Write-Host "Testing connectivity..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ UI is accessible! Opening browser...`n" -ForegroundColor Green
    Start-Process "http://localhost:3000"
    Start-Process "http://localhost:8000/docs"
} catch {
    Write-Host "⚠️  Could not connect yet. Please wait 10 seconds for Docker containers to fully start`n" -ForegroundColor Yellow
}

Read-Host "Press Enter to close"

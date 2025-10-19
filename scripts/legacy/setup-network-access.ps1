# RCA Engine - Network Access Setup Script
# This script sets up port forwarding and firewall rules to access WSL containers from Windows
# Must be run as Administrator

param(
    [switch]$Remove
)

$ErrorActionPreference = "Continue"

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "`n ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "`nPlease right-click PowerShell and select 'Run as Administrator', then run this script again.`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== RCA Engine Network Access Setup ===" -ForegroundColor Cyan
Write-Host "Running as Administrator`n" -ForegroundColor Green

# Get WSL IP address
Write-Host "Getting WSL IP address..." -ForegroundColor Yellow
try {
    $wslIP = (wsl hostname -I).Split()[0].Trim()
    if (-not $wslIP -or $wslIP -eq "") {
        throw "Could not get WSL IP address"
    }
    Write-Host "  WSL IP: $wslIP`n" -ForegroundColor Green
}
catch {
    Write-Host "  Failed to get WSL IP: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Make sure WSL is running.`n" -ForegroundColor Yellow
    exit 1
}

if ($Remove) {
    Write-Host "Removing port forwarding rules..." -ForegroundColor Yellow
    
    # Remove port forwarding
    netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0 2>$null
    netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null
    netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0 2>$null
    Write-Host "  Port forwarding rules removed" -ForegroundColor Green
    
    Write-Host "`nRemoving firewall rules..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "RCA Engine UI" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "RCA Engine API" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "RCA Engine Metrics" -ErrorAction SilentlyContinue
    Write-Host "  Firewall rules removed`n" -ForegroundColor Green
    
    Write-Host "Network access cleanup complete!`n" -ForegroundColor Green
    exit 0
}

# Configure port forwarding
Write-Host "Configuring port forwarding..." -ForegroundColor Yellow

$ports = @(
    @{Port=3000; Service="UI"},
    @{Port=8000; Service="API"},
    @{Port=8001; Service="Metrics"}
)

foreach ($p in $ports) {
    try {
        # Remove existing rule if present
        netsh interface portproxy delete v4tov4 listenport=$($p.Port) listenaddress=0.0.0.0 2>$null | Out-Null
        
        # Add new rule
        $result = netsh interface portproxy add v4tov4 listenport=$($p.Port) listenaddress=0.0.0.0 connectport=$($p.Port) connectaddress=$wslIP
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Port $($p.Port) ($($p.Service)) forwarded to WSL" -ForegroundColor Green
        }
        else {
            Write-Host "  Port $($p.Port) ($($p.Service)) may already be configured" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  Failed to forward port $($p.Port): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nCurrent port forwarding rules:" -ForegroundColor Cyan
netsh interface portproxy show all

# Configure Windows Firewall
Write-Host "`nConfiguring Windows Firewall..." -ForegroundColor Yellow

$firewallRules = @(
    @{Name="RCA Engine UI"; Port=3000; Description="Allow inbound traffic to RCA Engine UI"},
    @{Name="RCA Engine API"; Port=8000; Description="Allow inbound traffic to RCA Engine API"},
    @{Name="RCA Engine Metrics"; Port=8001; Description="Allow inbound traffic to RCA Engine Metrics"}
)

foreach ($rule in $firewallRules) {
    try {
        # Remove existing rule if present
        Remove-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue | Out-Null
        
        # Add new rule
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $rule.Port -Description $rule.Description -ErrorAction Stop | Out-Null
        
        Write-Host "  Firewall rule added: $($rule.Name) (port $($rule.Port))" -ForegroundColor Green
    }
    catch {
        Write-Host "  Failed to add firewall rule $($rule.Name): $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test connectivity
Write-Host "`nTesting connectivity..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$testResults = @()

# Test API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health/live" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "  API accessible at http://localhost:8000 (Status: $($response.StatusCode))" -ForegroundColor Green
    $testResults += @{Service="API"; Success=$true; URL="http://localhost:8000"}
}
catch {
    Write-Host "  API not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Service="API"; Success=$false; URL="http://localhost:8000"}
}

# Test UI
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "  UI accessible at http://localhost:3000 (Status: $($response.StatusCode))" -ForegroundColor Green
    $testResults += @{Service="UI"; Success=$true; URL="http://localhost:3000"}
}
catch {
    Write-Host "  UI not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Service="UI"; Success=$false; URL="http://localhost:3000"}
}

# Summary
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan

$successCount = ($testResults | Where-Object { $_.Success }).Count
if ($successCount -eq $testResults.Count) {
    Write-Host "`nAll services are accessible!" -ForegroundColor Green
    Write-Host "`nYou can now access:" -ForegroundColor Cyan
    Write-Host "  UI:      http://localhost:3000" -ForegroundColor White
    Write-Host "  API:     http://localhost:8000" -ForegroundColor White
    Write-Host "  Docs:    http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  Metrics: http://localhost:8001/metrics" -ForegroundColor White
    
    Write-Host "`nOpening in browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:3000"
    Start-Process "http://localhost:8000/docs"
}
else {
    Write-Host "`nSome services are not accessible yet." -ForegroundColor Yellow
    Write-Host "`nPossible reasons:" -ForegroundColor Cyan
    Write-Host "  - Docker containers are still starting up" -ForegroundColor White
    Write-Host "  - Containers are unhealthy or restarting" -ForegroundColor White
    Write-Host "  - WSL IP address changed (re-run this script)" -ForegroundColor White
    
    Write-Host "`nTroubleshooting commands:" -ForegroundColor Cyan
    Write-Host "  Check container status:" -ForegroundColor Gray
    Write-Host "  wsl bash -c ""cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml ps""" -ForegroundColor Gray
    Write-Host "`n  Check logs:" -ForegroundColor Gray
    Write-Host "  wsl bash -c ""cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml logs --tail=50""" -ForegroundColor Gray
    Write-Host "`n  Remove and re-run this script:" -ForegroundColor Gray
    Write-Host "  .\setup-network-access.ps1 -Remove" -ForegroundColor Gray
    Write-Host "  .\setup-network-access.ps1" -ForegroundColor Gray
}

Write-Host "`nTo remove these settings later, run:" -ForegroundColor Cyan
Write-Host "  .\setup-network-access.ps1 -Remove`n" -ForegroundColor Gray

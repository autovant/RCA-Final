# FIX-FIREWALL-WSL.ps1
# MUST RUN AS ADMINISTRATOR
# Creates comprehensive firewall rules for WSL backend connectivity

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  WSL FIREWALL RULES CONFIGURATION" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run:" -ForegroundColor Yellow
    Write-Host "  .\FIX-FIREWALL-WSL.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Get WSL IP
Write-Host "1. Getting WSL IP address..." -ForegroundColor Cyan
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "   WSL IP: $wslIP" -ForegroundColor Green
Write-Host ""

# Remove old rules
Write-Host "2. Removing old firewall rules..." -ForegroundColor Cyan
$oldRules = @(
    "WSL Backend",
    "WSL Backend - Port 8000",
    "WSL Backend - Outbound",
    "WSL vEthernet - Port 8000"
)

foreach ($ruleName in $oldRules) {
    $rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($rule) {
        Remove-NetFirewallRule -DisplayName $ruleName
        Write-Host "   ✓ Removed: $ruleName" -ForegroundColor Yellow
    }
}
Write-Host ""

# Create comprehensive inbound rules
Write-Host "3. Creating new firewall rules..." -ForegroundColor Cyan

# Rule 1: Inbound TCP on port 8000 for any address
Write-Host "   Creating: Inbound TCP 8000 (Any)" -ForegroundColor White
New-NetFirewallRule -DisplayName "WSL Backend - Port 8000 Inbound" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -Action Allow `
    -Profile Any `
    -Enabled True `
    -Description "Allow inbound connections to WSL backend on port 8000"
Write-Host "   ✓ Created" -ForegroundColor Green

# Rule 2: Outbound TCP on port 8000 for any address
Write-Host "   Creating: Outbound TCP 8000 (Any)" -ForegroundColor White
New-NetFirewallRule -DisplayName "WSL Backend - Port 8000 Outbound" `
    -Direction Outbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -Action Allow `
    -Profile Any `
    -Enabled True `
    -Description "Allow outbound connections from WSL backend on port 8000"
Write-Host "   ✓ Created" -ForegroundColor Green

# Rule 3: Inbound for WSL IP range
Write-Host "   Creating: Inbound for WSL IP $wslIP" -ForegroundColor White
New-NetFirewallRule -DisplayName "WSL Backend - WSL IP Inbound" `
    -Direction Inbound `
    -Protocol TCP `
    -RemoteAddress $wslIP `
    -Action Allow `
    -Profile Any `
    -Enabled True `
    -Description "Allow inbound connections from WSL IP $wslIP"
Write-Host "   ✓ Created" -ForegroundColor Green

# Rule 4: Localhost loopback rule
Write-Host "   Creating: Localhost loopback rule" -ForegroundColor White
New-NetFirewallRule -DisplayName "WSL Backend - Localhost 8000" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -LocalAddress 127.0.0.1 `
    -Action Allow `
    -Profile Any `
    -Enabled True `
    -Description "Allow localhost connections to port 8000"
Write-Host "   ✓ Created" -ForegroundColor Green

Write-Host ""
Write-Host "4. Verifying rules..." -ForegroundColor Cyan
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "WSL Backend*" } | 
    Select-Object DisplayName, Enabled, Direction, Action | 
    Format-Table -AutoSize

Write-Host ""
Write-Host "5. Testing connectivity..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

Write-Host "   Test 1: localhost:8000" -ForegroundColor White
try {
    $response = curl.exe http://localhost:8000/api/health/live --max-time 10 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ SUCCESS: $response" -ForegroundColor Green
    } else {
        Write-Host "   ❌ FAILED: $response" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ FAILED: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "   Test 2: WSL IP ($wslIP:8000)" -ForegroundColor White
try {
    $response = curl.exe http://${wslIP}:8000/api/health/live --max-time 10 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ SUCCESS: $response" -ForegroundColor Green
    } else {
        Write-Host "   ❌ FAILED: $response" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ FAILED: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  CONFIGURATION COMPLETE" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If tests still fail, the issue is likely:" -ForegroundColor Yellow
Write-Host "  • WSL2 networking architecture limitation" -ForegroundColor White
Write-Host "  • Windows network isolation policies" -ForegroundColor White
Write-Host "  • Need to switch to WSL mirrored networking or run backend natively" -ForegroundColor White
Write-Host ""

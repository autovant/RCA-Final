# Add Windows Firewall Rule for Port 8001
# Run as Administrator

Write-Host "Adding Windows Firewall rule for port 8001..." -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Or run this command in an Admin PowerShell:" -ForegroundColor Yellow
    Write-Host '  New-NetFirewallRule -DisplayName "WSL Backend 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow' -ForegroundColor White
    Write-Host ""
    exit 1
}

# Remove old rule if it exists
Write-Host "Removing old firewall rules..." -ForegroundColor Yellow
Remove-NetFirewallRule -DisplayName "WSL Backend 8001" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "WSL Backend" -ErrorAction SilentlyContinue

# Add new rule for port 8001
Write-Host "Adding firewall rule for port 8001..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "WSL Backend 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow

if ($?) {
    Write-Host "✓ Firewall rule added successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to add firewall rule" -ForegroundColor Red
}

Write-Host ""
Write-Host "Current firewall rules for WSL:" -ForegroundColor Cyan
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*WSL*"} | Select-Object DisplayName, Enabled, Direction, Action | Format-Table -AutoSize

Write-Host ""
Write-Host "✓ Done! Port 8001 should now be accessible" -ForegroundColor Green

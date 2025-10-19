# Fix Windows Firewall for WSL2 Mirrored Networking
# This creates proper firewall rules for WSL2 with mirrored networking mode
# Run as Administrator

#Requires -RunAsAdministrator

Write-Host "WSL2 Mirrored Networking Firewall Fix" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Remove old conflicting rules
Write-Host "[1/3] Removing old firewall rules..." -ForegroundColor Yellow
$oldRules = @(
    "WSL Docker Postgres",
    "WSL Docker Redis",
    "WSL Port 15432",
    "WSL Port 16379",
    "RCA PostgreSQL",
    "RCA Redis"
)

foreach ($ruleName in $oldRules) {
    try {
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        Write-Host "  Removed: $ruleName" -ForegroundColor Gray
    } catch {
        # Rule doesn't exist, ignore
    }
}

# Create new comprehensive rules for WSL with mirrored networking
Write-Host ""
Write-Host "[2/3] Creating new firewall rules..." -ForegroundColor Yellow

# Rule 1: Allow all WSL inbound connections (mirrored mode)
$rule1Params = @{
    DisplayName = "WSL Mirrored Network - Inbound"
    Description = "Allow all inbound connections for WSL2 mirrored networking mode"
    Direction = "Inbound"
    Action = "Allow"
    Protocol = "TCP"
    LocalPort = @(3000, 8000, 8001, 8002, 15432, 16379, 11434)
    Profile = "Any"
    Enabled = "True"
}

try {
    New-NetFirewallRule @rule1Params -ErrorAction Stop | Out-Null
    Write-Host "  ✓ Created: WSL Mirrored Network - Inbound" -ForegroundColor Green
} catch {
    Write-Host "  ! Error creating inbound rule: $_" -ForegroundColor Red
}

# Rule 2: Allow WSL outbound connections
$rule2Params = @{
    DisplayName = "WSL Mirrored Network - Outbound"
    Description = "Allow all outbound connections for WSL2 mirrored networking mode"
    Direction = "Outbound"
    Action = "Allow"
    Protocol = "TCP"
    RemotePort = @(3000, 8000, 8001, 8002, 15432, 16379, 11434)
    Profile = "Any"
    Enabled = "True"
}

try {
    New-NetFirewallRule @rule2Params -ErrorAction Stop | Out-Null
    Write-Host "  ✓ Created: WSL Mirrored Network - Outbound" -ForegroundColor Green
} catch {
    Write-Host "  ! Error creating outbound rule: $_" -ForegroundColor Red
}

# Rule 3: Specific rule for localhost connections to WSL services
$rule3Params = @{
    DisplayName = "WSL Localhost Services"
    Description = "Allow localhost connections to WSL2 services (mirrored mode)"
    Direction = "Inbound"
    Action = "Allow"
    Protocol = "TCP"
    LocalAddress = "127.0.0.1"
    Profile = "Any"
    Enabled = "True"
}

try {
    New-NetFirewallRule @rule3Params -ErrorAction Stop | Out-Null
    Write-Host "  ✓ Created: WSL Localhost Services" -ForegroundColor Green
} catch {
    Write-Host "  ! Error creating localhost rule: $_" -ForegroundColor Red
}

# Verify rules were created
Write-Host ""
Write-Host "[3/3] Verifying firewall rules..." -ForegroundColor Yellow
$createdRules = Get-NetFirewallRule -DisplayName "WSL*" | Where-Object { $_.Enabled -eq $true }

if ($createdRules.Count -gt 0) {
    Write-Host "  ✓ Active WSL firewall rules:" -ForegroundColor Green
    foreach ($rule in $createdRules) {
        Write-Host "    - $($rule.DisplayName) ($($rule.Direction))" -ForegroundColor Cyan
    }
} else {
    Write-Host "  ! No active WSL rules found" -ForegroundColor Red
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Firewall Configuration Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Additional troubleshooting if issues persist:" -ForegroundColor Yellow
Write-Host "  1. Disable VPN if active" -ForegroundColor White
Write-Host "  2. Check antivirus software isn't blocking connections" -ForegroundColor White
Write-Host "  3. Verify .wslconfig has networkingMode=mirrored" -ForegroundColor White
Write-Host "  4. Run: wsl --shutdown (then restart containers)" -ForegroundColor White
Write-Host ""

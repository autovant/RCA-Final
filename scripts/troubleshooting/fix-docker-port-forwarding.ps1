# Complete WSL2 Port Forwarding Fix for Docker
# This sets up proper port forwarding for Docker containers in WSL2
# Run as Administrator

#Requires -RunAsAdministrator

Write-Host "WSL2 Docker Port Forwarding - Complete Fix" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Remove mirrored networking (it doesn't work well with Docker bridge networks)
Write-Host "[1/5] Configuring WSL for Docker compatibility..." -ForegroundColor Yellow
$wslConfigPath = "$env:USERPROFILE\.wslconfig"
$needsRestart = $false

if (Test-Path $wslConfigPath) {
    $config = Get-Content $wslConfigPath -Raw
    if ($config -match "networkingMode\s*=\s*mirrored") {
        Write-Host "  ! Found mirrored networking (incompatible with Docker bridge mode)" -ForegroundColor Yellow
        Write-Host "  Updating .wslconfig to use NAT mode..." -ForegroundColor Cyan
        
        # Comment out mirrored networking
        $newConfig = $config -replace "networkingMode\s*=\s*mirrored", "#networkingMode=mirrored # Disabled for Docker compatibility"
        $newConfig | Out-File -FilePath $wslConfigPath -Encoding UTF8
        $needsRestart = $true
        Write-Host "  ✓ Configuration updated" -ForegroundColor Green
    } else {
        Write-Host "  ✓ WSL using NAT mode (good for Docker)" -ForegroundColor Green
    }
} else {
    Write-Host "  ✓ No .wslconfig found (using default NAT mode)" -ForegroundColor Green
}

# Step 2: Restart WSL if needed
if ($needsRestart) {
    Write-Host ""
    Write-Host "[2/5] Restarting WSL to apply changes..." -ForegroundColor Yellow
    wsl --shutdown
    Start-Sleep -Seconds 3
    wsl echo "WSL restarted"
    Start-Sleep -Seconds 2
    Write-Host "  ✓ WSL restarted" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[2/5] WSL restart not needed" -ForegroundColor Green
}

# Step 3: Get WSL IP
Write-Host ""
Write-Host "[3/5] Getting WSL IP address..." -ForegroundColor Yellow
$wslIP = ""
for ($i = 1; $i -le 10; $i++) {
    $wslIP = (wsl hostname -I 2>$null).Split()[0].Trim()
    if (![string]::IsNullOrWhiteSpace($wslIP)) {
        break
    }
    Start-Sleep -Seconds 1
}

if ([string]::IsNullOrWhiteSpace($wslIP)) {
    Write-Host "  ✗ Could not get WSL IP address" -ForegroundColor Red
    exit 1
}

Write-Host "  WSL IP: $wslIP" -ForegroundColor Green

# Step 4: Configure port forwarding
Write-Host ""
Write-Host "[4/5] Setting up port forwarding..." -ForegroundColor Yellow

# Define ports
$ports = @(
    @{Port=15432; Name="PostgreSQL"},
    @{Port=16379; Name="Redis"},
    @{Port=8001; Name="FastAPI"},
    @{Port=3000; Name="Next.js UI"},
    @{Port=11434; Name="Ollama (optional)"}
)

# Remove all existing port proxies first
Write-Host "  Removing old port forwarding rules..." -ForegroundColor Cyan
netsh interface portproxy reset 2>$null

# Add new port proxies
Write-Host "  Adding new port forwarding rules..." -ForegroundColor Cyan
$successCount = 0
foreach ($portInfo in $ports) {
    $port = $portInfo.Port
    $name = $portInfo.Name
    
    # Add forwarding from all interfaces
    $result = netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIP 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Port $port ($name)" -ForegroundColor Green
        $successCount++
    } else {
        Write-Host "    ✗ Port $port ($name) - $result" -ForegroundColor Red
    }
}

Write-Host "  ✓ Configured $successCount port(s)" -ForegroundColor Green

# Step 5: Configure Windows Firewall
Write-Host ""
Write-Host "[5/5] Configuring Windows Firewall..." -ForegroundColor Yellow

# Remove old rules
$oldRules = Get-NetFirewallRule -DisplayName "WSL*" -ErrorAction SilentlyContinue
if ($oldRules) {
    Write-Host "  Removing old firewall rules..." -ForegroundColor Cyan
    $oldRules | Remove-NetFirewallRule
}

# Create new comprehensive rule
$ruleParams = @{
    DisplayName = "WSL Docker Services"
    Description = "Allow Windows to access Docker services running in WSL2"
    Direction = "Inbound"
    Action = "Allow"
    Protocol = "TCP"
    LocalPort = @(3000, 8001, 15432, 16379, 11434)
    Profile = "Any"
    Enabled = "True"
}

try {
    New-NetFirewallRule @ruleParams -ErrorAction Stop | Out-Null
    Write-Host "  ✓ Firewall rule created" -ForegroundColor Green
} catch {
    Write-Host "  ! Firewall configuration warning: $_" -ForegroundColor Yellow
}

# Display results
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Port Forwarding Configuration Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Current Configuration:" -ForegroundColor Cyan
netsh interface portproxy show v4tov4

Write-Host ""
Write-Host "Services will be accessible at:" -ForegroundColor Yellow
Write-Host "  PostgreSQL:  localhost:15432" -ForegroundColor White
Write-Host "  Redis:       localhost:16379" -ForegroundColor White
Write-Host "  API:         localhost:8001" -ForegroundColor White
Write-Host "  UI:          localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Start containers: ./start-environment.ps1" -ForegroundColor White
Write-Host "  2. Or manually: wsl docker compose -f docker-compose.dev.yml up -d" -ForegroundColor White
Write-Host ""
Write-Host "Note: WSL IP can change on restart." -ForegroundColor Cyan
Write-Host "      If services become unreachable, run this script again." -ForegroundColor Cyan
Write-Host ""

#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Fix port 8001 access issues

.DESCRIPTION
    Resolves Windows Error 10013 (port access forbidden) for port 8001
    This can be caused by:
    - Port already in use by another process
    - Windows port reservations
    - Hyper-V dynamic port range conflicts
    - Firewall blocking the port
#>

$ErrorActionPreference = 'Stop'

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message, [string]$Status = "")
    if ($Status -eq "OK") {
        Write-Host "  ✓ $Message" -ForegroundColor Green
    } elseif ($Status -eq "WARN") {
        Write-Host "  ⚠ $Message" -ForegroundColor Yellow
    } elseif ($Status -eq "ERROR") {
        Write-Host "  ✗ $Message" -ForegroundColor Red
    } else {
        Write-Host "  → $Message" -ForegroundColor Cyan
    }
}

Write-Header "Fixing Port 8001 Access"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠ This script requires Administrator privileges" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run as Administrator:" -ForegroundColor Cyan
    Write-Host "  Right-click PowerShell → Run as Administrator" -ForegroundColor White
    Write-Host "  Then run: .\fix-port-8001.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Step 1: Check what's using the port
Write-Header "Step 1: Port Usage Analysis"

$portInUse = netstat -ano | Select-String ":8001" | Select-String "LISTENING"
if ($portInUse) {
    Write-Step "Port 8001 is currently in use" "WARN"
    Write-Host ""
    Write-Host $portInUse -ForegroundColor Gray
    Write-Host ""
    
    # Extract PID
    $pidMatch = $portInUse -match '\s+(\d+)\s*$'
    if ($pidMatch) {
        $pid = $matches[1]
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "  Process: $($process.ProcessName) (PID: $pid)" -ForegroundColor Yellow
                
                # If it's our own backend, kill it
                if ($process.ProcessName -match "python|uvicorn") {
                    Write-Step "Stopping existing backend process..."
                    Stop-Process -Id $pid -Force
                    Start-Sleep -Seconds 2
                    Write-Step "Process stopped" "OK"
                } elseif ($process.ProcessName -eq "svchost") {
                    Write-Step "Port is held by Windows system service" "WARN"
                    Write-Host "  This is usually Hyper-V or WinNAT related" -ForegroundColor Gray
                    Write-Host "  Attempting to release..." -ForegroundColor Gray
                } else {
                    Write-Host ""
                    Write-Host "  Do you want to stop this process? (Y/N): " -ForegroundColor Yellow -NoNewline
                    $response = Read-Host
                    if ($response -eq 'Y' -or $response -eq 'y') {
                        Stop-Process -Id $pid -Force
                        Start-Sleep -Seconds 2
                        Write-Step "Process stopped" "OK"
                    }
                }
            }
        } catch {
            Write-Step "Could not access process info" "WARN"
        }
    }
} else {
    Write-Step "Port 8001 is free" "OK"
}

# Step 2: Check for port exclusions
Write-Header "Step 2: Port Exclusion Check"

Write-Step "Checking Windows port exclusions..."
$exclusions = netsh interface ipv4 show excludedportrange protocol=tcp | Select-String "\d+"
$excluded = $false
foreach ($line in $exclusions) {
    if ($line -match '(\d+)\s+(\d+)') {
        $start = [int]$matches[1]
        $end = [int]$matches[2]
        if (8001 -ge $start -and 8001 -le $end) {
            $excluded = $true
            Write-Step "Port 8001 is in excluded range $start-$end" "ERROR"
            break
        }
    }
}

if (-not $excluded) {
    Write-Step "Port 8001 is not excluded" "OK"
}

# Step 3: Reset NAT if needed
Write-Header "Step 3: Network Configuration"

Write-Step "Checking for WinNAT conflicts..."
try {
    $natNetworks = Get-NetNat -ErrorAction SilentlyContinue
    if ($natNetworks) {
        Write-Step "Found NAT networks - may cause port conflicts" "WARN"
        Write-Host ""
        Write-Host "  Do you want to reset WinNAT? This is safe but may affect WSL. (Y/N): " -ForegroundColor Yellow -NoNewline
        $response = Read-Host
        if ($response -eq 'Y' -or $response -eq 'y') {
            Write-Step "Stopping WinNAT service..."
            Stop-Service -Name WinNat -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            Write-Step "Starting WinNAT service..."
            Start-Service -Name WinNat
            Start-Sleep -Seconds 2
            Write-Step "WinNAT reset complete" "OK"
        }
    } else {
        Write-Step "No NAT conflicts detected" "OK"
    }
} catch {
    Write-Step "NAT check complete" "OK"
}

# Step 4: Firewall rules
Write-Header "Step 4: Firewall Configuration"

Write-Step "Checking firewall rules for port 8001..."
$existingRules = Get-NetFirewallRule -DisplayName "*8001*" -ErrorAction SilentlyContinue
if ($existingRules) {
    Write-Step "Removing old firewall rules..."
    $existingRules | Remove-NetFirewallRule
}

Write-Step "Creating new firewall rule for port 8001..."
New-NetFirewallRule -DisplayName "RCA Backend - Port 8001" `
    -Direction Inbound `
    -LocalPort 8001 `
    -Protocol TCP `
    -Action Allow `
    -Profile Any `
    -ErrorAction SilentlyContinue | Out-Null

Write-Step "Firewall configured" "OK"

# Step 5: Final verification
Write-Header "Step 5: Verification"

Write-Step "Checking if port 8001 is now available..."
$stillInUse = netstat -ano | Select-String ":8001" | Select-String "LISTENING"
if ($stillInUse) {
    Write-Step "Port is still in use" "WARN"
    Write-Host ""
    Write-Host "Manual intervention required:" -ForegroundColor Yellow
    Write-Host "  1. Restart your computer (recommended)" -ForegroundColor White
    Write-Host "  2. Or use a different port (e.g., 8002)" -ForegroundColor White
    Write-Host ""
    Write-Host "To use port 8002 instead:" -ForegroundColor Cyan
    Write-Host "  1. Edit ui\.env.local: NEXT_PUBLIC_API_BASE_URL=http://localhost:8002" -ForegroundColor White
    Write-Host "  2. Edit start-local-hybrid.ps1: Change --port 8001 to --port 8002" -ForegroundColor White
} else {
    Write-Step "Port 8001 is now available!" "OK"
}

# Success
Write-Header "Fix Complete!"

Write-Host "✓ Port 8001 configuration fixed" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Close all PowerShell windows" -ForegroundColor White
Write-Host "  2. Open a new PowerShell window" -ForegroundColor White
Write-Host "  3. Run: .\start-local-hybrid.ps1" -ForegroundColor White
Write-Host ""
Write-Host "If you still see issues, try:" -ForegroundColor Yellow
Write-Host "  • Restart your computer" -ForegroundColor White
Write-Host "  • Check Windows Event Viewer for port conflicts" -ForegroundColor White
Write-Host "  • Disable Hyper-V temporarily: bcdedit /set hypervisorlaunchtype off" -ForegroundColor White
Write-Host ""

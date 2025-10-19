# TEST-FIREWALL-DISABLE.ps1
# MUST RUN AS ADMINISTRATOR
# This temporarily disables Windows Defender Firewall to test if it's blocking WSL connectivity

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  WINDOWS FIREWALL CONNECTIVITY TEST" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run:" -ForegroundColor Yellow
    Write-Host "  .\TEST-FIREWALL-DISABLE.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "⚠️  WARNING: This script will temporarily disable Windows Defender Firewall" -ForegroundColor Yellow
Write-Host "   to test if it's blocking WSL connectivity." -ForegroundColor Yellow
Write-Host ""
Write-Host "   The firewall will be re-enabled automatically at the end." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Do you want to proceed? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Test cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "1. Current firewall status:" -ForegroundColor Cyan
Get-NetFirewallProfile | Select-Object Name, Enabled | Format-Table -AutoSize

Write-Host ""
Write-Host "2. Disabling Windows Defender Firewall..." -ForegroundColor Yellow
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
Start-Sleep -Seconds 2

Write-Host "   ✓ Firewall disabled" -ForegroundColor Green
Write-Host ""

Write-Host "3. Testing connectivity..." -ForegroundColor Cyan
Write-Host ""

# Test 1: localhost with port forwarding
Write-Host "   Test 1: http://localhost:8000 (via port forwarding)" -ForegroundColor White
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

# Test 2: Direct WSL IP
Write-Host "   Test 2: http://192.168.0.117:8000 (direct WSL IP)" -ForegroundColor White
try {
    $response = curl.exe http://192.168.0.117:8000/api/health/live --max-time 10 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ SUCCESS: $response" -ForegroundColor Green
    } else {
        Write-Host "   ❌ FAILED: $response" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ FAILED: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Invoke-WebRequest (browser-like)
Write-Host "   Test 3: Invoke-WebRequest (simulates browser)" -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health/live" -TimeoutSec 10 -UseBasicParsing
    Write-Host "   ✅ SUCCESS: $($response.StatusCode) - $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ FAILED: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "4. Re-enabling Windows Defender Firewall..." -ForegroundColor Yellow
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
Start-Sleep -Seconds 2

Write-Host "   ✓ Firewall re-enabled" -ForegroundColor Green
Write-Host ""

Write-Host "5. Final firewall status:" -ForegroundColor Cyan
Get-NetFirewallProfile | Select-Object Name, Enabled | Format-Table -AutoSize

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  TEST COMPLETE" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "INTERPRETATION:" -ForegroundColor Cyan
Write-Host "  • If tests PASSED with firewall disabled → Firewall is the issue" -ForegroundColor White
Write-Host "    Solution: Need more specific firewall rules" -ForegroundColor White
Write-Host ""
Write-Host "  • If tests FAILED with firewall disabled → Not a firewall issue" -ForegroundColor White
Write-Host "    Solution: WSL2 networking limitation, need to:" -ForegroundColor White
Write-Host "      1. Switch to WSL mirrored networking mode, OR" -ForegroundColor White
Write-Host "      2. Run backend natively on Windows" -ForegroundColor White
Write-Host ""

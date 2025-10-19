# Test Network Connectivity
# This script tests various ways to reach the backend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Network Connectivity Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get WSL IP
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "WSL IP: $wslIP" -ForegroundColor Yellow
Write-Host ""

# Test 1: Backend in WSL
Write-Host "Test 1: Backend in WSL (localhost:8000)" -ForegroundColor Cyan
$test1 = wsl bash -c "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/health/live" 2>$null
if ($test1 -eq "200") {
    Write-Host "  ✓ Backend is running in WSL" -ForegroundColor Green
} else {
    Write-Host "  ✗ Backend not responding in WSL (Status: $test1)" -ForegroundColor Red
}
Write-Host ""

# Test 2: WSL IP from Windows (curl)
Write-Host "Test 2: WSL IP from Windows using curl" -ForegroundColor Cyan
try {
    $test2 = curl -s "http://${wslIP}:8000/api/health/live" 2>$null
    if ($test2 -like "*ok*") {
        Write-Host "  ✓ Can reach WSL IP directly" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Cannot reach WSL IP" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✗ Cannot reach WSL IP: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Localhost from Windows (curl)
Write-Host "Test 3: localhost:8000 from Windows using curl" -ForegroundColor Cyan
try {
    $test3 = curl -s "http://localhost:8000/api/health/live" 2>$null
    if ($test3 -like "*ok*") {
        Write-Host "  ✓ Port forwarding works (curl)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Port forwarding failed (curl)" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✗ Port forwarding failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 4: Localhost from Windows (Invoke-WebRequest = browser-like)
Write-Host "Test 4: localhost:8000 from Windows using Invoke-WebRequest (browser-like)" -ForegroundColor Cyan
try {
    $test4 = Invoke-WebRequest -Uri "http://localhost:8000/api/health/live" -UseBasicParsing -TimeoutSec 5
    if ($test4.StatusCode -eq 200) {
        Write-Host "  ✓ Browser-like connection works" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Browser-like connection failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✗ Browser-like connection failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 5: Check port forwarding
Write-Host "Test 5: Port forwarding configuration" -ForegroundColor Cyan
$portProxy = netsh interface portproxy show v4tov4 | Select-String "0.0.0.0.*8000"
if ($portProxy) {
    Write-Host "  ✓ Port forwarding is configured" -ForegroundColor Green
    Write-Host "    $portProxy" -ForegroundColor Gray
} else {
    Write-Host "  ✗ Port forwarding not configured" -ForegroundColor Red
}
Write-Host ""

# Test 6: Check firewall
Write-Host "Test 6: Firewall rule" -ForegroundColor Cyan
$fwRule = Get-NetFirewallRule -DisplayName "WSL Backend*" -ErrorAction SilentlyContinue
if ($fwRule -and $fwRule.Enabled) {
    Write-Host "  ✓ Firewall rule exists and is enabled" -ForegroundColor Green
} else {
    Write-Host "  ✗ Firewall rule missing or disabled" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Recommendations" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($test1 -ne "200") {
    Write-Host "❌ Backend not running - Start with: .\START-SIMPLE.ps1" -ForegroundColor Red
} elseif ($test3 -notlike "*ok*") {
    Write-Host "❌ Port forwarding issue - Run as Admin: .\ENABLE-NETWORK-ACCESS.ps1" -ForegroundColor Red
} elseif ($test4.StatusCode -ne 200) {
    Write-Host "⚠️  Browser connections blocked - Try:" -ForegroundColor Yellow
    Write-Host "   Option 1: Disable Windows Defender Firewall temporarily" -ForegroundColor White
    Write-Host "   Option 2: Use WSL IP directly in UI config:" -ForegroundColor White
    Write-Host "      Edit ui\.env.local and change to:" -ForegroundColor Gray
    Write-Host "      NEXT_PUBLIC_API_BASE_URL=http://${wslIP}:8000" -ForegroundColor Gray
} else {
    Write-Host "✅ Everything looks good!" -ForegroundColor Green
    Write-Host "   If browser still can't connect, try:" -ForegroundColor Yellow
    Write-Host "   1. Clear browser cache (Ctrl+Shift+Delete)" -ForegroundColor White
    Write-Host "   2. Try a different browser" -ForegroundColor White
    Write-Host "   3. Check browser extensions (disable ad blockers)" -ForegroundColor White
}
Write-Host ""

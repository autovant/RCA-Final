# ULTRA-SIMPLE Demo Startup
# Everything in Docker through WSL except UI (which needs fast hot reload)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Simple Demo Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get WSL IP for later access
Write-Host "Getting WSL IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Split()[0].Trim()
if ([string]::IsNullOrWhiteSpace($wslIP)) {
    Write-Host "ERROR: Could not get WSL IP address" -ForegroundColor Red
    Write-Host "Make sure WSL is running" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ WSL IP: $wslIP" -ForegroundColor Green
Write-Host ""

Write-Host "Starting backend services in Docker (through WSL)..." -ForegroundColor Yellow
Write-Host "(This takes ~20 seconds)" -ForegroundColor Gray
Write-Host ""

# Stop any existing containers
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f deploy/docker/docker-compose.yml down" 2>$null

# Start containers in WSL
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f deploy/docker/docker-compose.yml up -d"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start Docker containers" -ForegroundColor Red
    Write-Host "Make sure Docker is installed in WSL" -ForegroundColor Yellow
    Write-Host "Run: wsl bash -c 'docker ps' to test" -ForegroundColor White
    exit 1
}

Write-Host "✓ Backend services started in WSL" -ForegroundColor Green
Write-Host ""

# Setup port forwarding so Windows can access WSL backend
Write-Host "Setting up network access from Windows to WSL..." -ForegroundColor Yellow

# Remove old port forwarding
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null

# Add port forwarding
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Port forwarding configured (8000 → ${wslIP}:8000)" -ForegroundColor Green
} else {
    Write-Host "⚠ Port forwarding failed (may need Administrator)" -ForegroundColor Yellow
    Write-Host "  UI will try to connect directly to WSL IP" -ForegroundColor Gray
}

# Update UI config to use localhost (which forwards to WSL)
Write-Host "Updating UI configuration..." -ForegroundColor Yellow
$envContent = "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000"
$envContent | Out-File -FilePath "ui\.env.local" -Encoding UTF8 -Force
Write-Host "✓ UI will connect to: http://localhost:8000" -ForegroundColor Green
Write-Host ""

# Wait for backend to be healthy
Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        $response = wsl bash -c "curl -s http://localhost:8000/api/health/live" 2>$null
        if ($response -like "*ok*") {
            Write-Host "✓ Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {}
    Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "Starting UI..." -ForegroundColor Yellow

# Start UI in new window
$uiScript = @"
Write-Host 'RCA Engine - Frontend UI' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
cd '$PWD\ui'
npm run dev
"@
$uiScript | Out-File -FilePath "temp-start-ui.ps1" -Encoding UTF8
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "temp-start-ui.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Demo Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application URLs:" -ForegroundColor Yellow
Write-Host "  UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "UI will be ready in ~10 seconds..." -ForegroundColor Gray
Write-Host ""

# Wait then open browser
Start-Sleep -Seconds 12
Start-Process "http://localhost:3000"

Write-Host "✓ Browser opened!" -ForegroundColor Green
Write-Host ""
Write-Host "To stop: Close the UI window and run .\stop-simple.ps1" -ForegroundColor Gray
Write-Host ""

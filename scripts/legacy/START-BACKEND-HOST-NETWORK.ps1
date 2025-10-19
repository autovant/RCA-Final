# START-BACKEND-HOST-NETWORK.ps1
# Starts backend with host networking mode to work with WSL mirrored networking
# This makes the backend directly accessible on Windows localhost

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  START BACKEND WITH HOST NETWORKING" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Stopping existing rca_core container..." -ForegroundColor Yellow
wsl bash -c "docker stop rca_core 2>/dev/null || true"
wsl bash -c "docker rm rca_core 2>/dev/null || true"
Start-Sleep -Seconds 3
Write-Host "   ✓ Stopped" -ForegroundColor Green
Write-Host ""

Write-Host "2. Starting backend with host network mode..." -ForegroundColor Cyan
Write-Host "   (This allows Windows to access backend via localhost:8000)" -ForegroundColor White
Write-Host ""

$startCommand = @"
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && \
docker run -d \
  --name rca_core \
  --network host \
  --restart unless-stopped \
  --env-file deploy/docker/.env \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_PORT=15432 \
  -e ENVIRONMENT=development \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  -v \$(pwd)/deploy/uploads:/app/uploads \
  -v \$(pwd)/deploy/reports:/app/reports \
  -v \$(pwd)/deploy/logs:/app/logs \
  docker-rca_core
"@

wsl bash -c $startCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Failed to start backend" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Try building the image first:" -ForegroundColor Yellow
    Write-Host "   wsl bash -c 'cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml build rca_core'" -ForegroundColor Cyan
    exit 1
}

Write-Host "   ✓ Backend container started with host networking" -ForegroundColor Green
Write-Host ""

Write-Host "3. Waiting for backend to be ready..." -ForegroundColor Yellow
$attempts = 0
$maxAttempts = 20

while ($attempts -lt $maxAttempts) {
    Start-Sleep -Seconds 3
    $attempts++
    
    $result = wsl bash -c "curl -s http://localhost:8000/api/health/live 2>&1"
    if ($result -like "*ok*") {
        Write-Host "   ✓ Backend is ready!" -ForegroundColor Green
        break
    } else {
        Write-Host "   Attempt $attempts/$maxAttempts..." -ForegroundColor Gray
    }
}

if ($attempts -eq $maxAttempts) {
    Write-Host "   ⚠️  Backend didn't respond in time. Checking logs..." -ForegroundColor Yellow
    wsl bash -c "docker logs rca_core --tail 20"
    exit 1
}

Write-Host ""
Write-Host "4. Testing connectivity from Windows..." -ForegroundColor Cyan
Write-Host ""

Write-Host "   Test 1: curl from Windows" -ForegroundColor White
try {
    $response = curl.exe http://localhost:8000/api/health/live --max-time 5 2>&1
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
Write-Host "  BACKEND STARTED" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend is running at: http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Make sure UI .env.local has: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" -ForegroundColor White
Write-Host "2. Start UI: cd ui && npm run dev" -ForegroundColor White
Write-Host "3. Open browser: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "To stop: wsl bash -c 'docker stop rca_core'" -ForegroundColor Gray
Write-Host "To view logs: wsl bash -c 'docker logs -f rca_core'" -ForegroundColor Gray
Write-Host ""

# START-ALL-STABLE.ps1
# Complete startup script with stable networking configuration

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  RCA ENGINE - STABLE STARTUP" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop and clean up existing containers
Write-Host "1. Cleaning up existing containers..." -ForegroundColor Yellow
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f deploy/docker/docker-compose.yml down" 2>$null
Start-Sleep -Seconds 3
Write-Host "   ✓ Cleanup complete" -ForegroundColor Green
Write-Host ""

# Step 2: Start all containers
Write-Host "2. Starting Docker containers..." -ForegroundColor Cyan
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f deploy/docker/docker-compose.yml up -d"
Write-Host ""

# Step 3: Wait for backend to be ready
Write-Host "3. Waiting for backend to be ready..." -ForegroundColor Yellow
$maxAttempts = 40
$attempts = 0
$backendReady = $false

while ($attempts -lt $maxAttempts) {
    Start-Sleep -Seconds 3
    $attempts++
    
    # Test from within WSL first
    $result = wsl bash -c "curl -s http://localhost:8000/api/health/live 2>&1"
    if ($result -like "*ok*") {
        Write-Host "   ✓ Backend responding in WSL (attempt $attempts)" -ForegroundColor Green
        
        # Now test from Windows
        Start-Sleep -Seconds 2
        try {
            $winResult = curl.exe http://localhost:8000/api/health/live --max-time 5 2>&1
            if ($winResult -like "*ok*") {
                Write-Host "   ✓ Backend accessible from Windows!" -ForegroundColor Green
                $backendReady = $true
                break
            } else {
                Write-Host "   ⚠️  Backend works in WSL but not from Windows yet..." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "   ⚠️  Windows connection failed, retrying..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "   Waiting... (attempt $attempts/$maxAttempts)" -ForegroundColor Gray
    }
}

if (-not $backendReady) {
    Write-Host ""
    Write-Host "   ❌ Backend did not become accessible from Windows" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Checking logs..." -ForegroundColor Yellow
    wsl bash -c "docker logs rca_core --tail 30"
    Write-Host ""
    Write-Host "   Try manually:" -ForegroundColor Yellow
    Write-Host "   1. wsl bash -c 'docker logs -f rca_core'" -ForegroundColor Cyan
    Write-Host "   2. Check if backend is working in WSL: wsl bash -c 'curl http://localhost:8000/api/health/live'" -ForegroundColor Cyan
    exit 1
}

Write-Host ""

# Step 4: Kill any existing UI processes
Write-Host "4. Stopping existing UI instances..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force 2>$null
Start-Sleep -Seconds 3
Write-Host "   ✓ UI processes stopped" -ForegroundColor Green
Write-Host ""

# Step 5: Verify .env.local configuration
Write-Host "5. Verifying UI configuration..." -ForegroundColor Cyan
$envFile = "ui\.env.local"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile | Select-String "NEXT_PUBLIC_API_BASE_URL"
    Write-Host "   $envContent" -ForegroundColor White
    
    if ($envContent -notlike "*localhost:8000*") {
        Write-Host "   ⚠️  Updating .env.local to use localhost:8000..." -ForegroundColor Yellow
        (Get-Content $envFile) -replace 'NEXT_PUBLIC_API_BASE_URL=.*', 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8000' | Set-Content $envFile
        Write-Host "   ✓ Updated" -ForegroundColor Green
    } else {
        Write-Host "   ✓ Configuration correct" -ForegroundColor Green
    }
} else {
    Write-Host "   ❌ .env.local not found!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Start UI in new window
Write-Host "6. Starting UI..." -ForegroundColor Cyan
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PWD\ui'; Write-Host 'Starting RCA Engine UI...' -ForegroundColor Cyan; npm run dev"
Start-Sleep -Seconds 5
Write-Host "   ✓ UI starting in new window" -ForegroundColor Green
Write-Host ""

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  STARTUP COMPLETE!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Backend: http://localhost:8000" -ForegroundColor Green
Write-Host "✅ UI: http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Open browser to http://localhost:3000" -ForegroundColor White
Write-Host "   2. Click 'Sign Up' to create an account" -ForegroundColor White
Write-Host "   3. Fill in your details and register" -ForegroundColor White
Write-Host ""
Write-Host "🔍 If registration fails:" -ForegroundColor Yellow
Write-Host "   1. Press F12 in browser to open DevTools" -ForegroundColor White
Write-Host "   2. Go to Console tab to see error details" -ForegroundColor White
Write-Host "   3. Go to Network tab to see the API request" -ForegroundColor White
Write-Host "   4. Try: curl http://localhost:8000/api/health/live" -ForegroundColor Cyan
Write-Host ""
Write-Host "🛑 To stop everything:" -ForegroundColor Yellow
Write-Host "   wsl bash -c 'cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\\ -\\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml down'" -ForegroundColor Cyan
Write-Host ""

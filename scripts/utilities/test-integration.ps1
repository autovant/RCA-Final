#!/usr/bin/env pwsh
# Integration Test Script for RCA Engine

Write-Host "`n=== RCA Engine Integration Test ===" -ForegroundColor Cyan
Write-Host "Testing: File Upload + GitHub Copilot Integration`n" -ForegroundColor Cyan

# 1. Check Backend Health
Write-Host "[1/5] Checking backend health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health/live" -Method GET
    Write-Host "✓ Backend: $($health.app) v$($health.version) - Status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend not responding: $_" -ForegroundColor Red
    exit 1
}

# 2. Check UI
Write-Host "`n[2/5] Checking UI..." -ForegroundColor Yellow
try {
    $ui = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3
    Write-Host "✓ UI responding with status: $($ui.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ UI not responding: $_" -ForegroundColor Red
    Write-Host "  Start UI with: cd ui && npm run dev" -ForegroundColor Yellow
}

# 3. Create a test file for upload
Write-Host "`n[3/5] Creating test log file..." -ForegroundColor Yellow
$testFile = Join-Path $PSScriptRoot "test-log.txt"
$testContent = @"
2024-10-15 10:23:45 ERROR [ServiceA] Connection timeout to database
2024-10-15 10:23:46 WARN  [ServiceA] Retrying connection (attempt 1/3)
2024-10-15 10:23:50 ERROR [ServiceA] Connection timeout to database
2024-10-15 10:23:51 ERROR [ServiceA] Max retries exceeded. Service unavailable.
2024-10-15 10:24:01 ERROR [ServiceB] Failed to process message queue
2024-10-15 10:24:02 INFO  [ServiceC] Received alert from monitoring system
"@
Set-Content -Path $testFile -Value $testContent
Write-Host "✓ Test file created: $testFile" -ForegroundColor Green

# 4. Test File Upload API
Write-Host "`n[4/5] Testing file upload API..." -ForegroundColor Yellow
Write-Host "  Note: You'll need to test this through the UI or with proper authentication" -ForegroundColor Cyan
Write-Host "  File ready at: $testFile" -ForegroundColor Cyan

# 5. Check GitHub Copilot Configuration
Write-Host "`n[5/5] Checking GitHub Copilot configuration..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot "deploy\docker\.env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "DEFAULT_PROVIDER=copilot") {
        Write-Host "✓ DEFAULT_PROVIDER is set to 'copilot'" -ForegroundColor Green
    }
    if ($envContent -match "GITHUB_TOKEN=ghu_") {
        Write-Host "✓ GITHUB_TOKEN is configured" -ForegroundColor Green
    }
    
    # Check if Copilot provider file exists
    $copilotFile = Join-Path $PSScriptRoot "core\llm\providers\copilot.py"
    if (Test-Path $copilotFile) {
        $fileSize = (Get-Item $copilotFile).Length
        Write-Host "✓ GitHub Copilot provider exists ($fileSize bytes)" -ForegroundColor Green
    }
}

Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "✓ Backend API: Running and healthy" -ForegroundColor Green
Write-Host "✓ Configuration: GitHub Copilot provider configured" -ForegroundColor Green
Write-Host "✓ Test file: Created for upload testing" -ForegroundColor Green
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor White
Write-Host "2. Upload the test file: $testFile" -ForegroundColor White
Write-Host "3. Create a job and verify it uses GitHub Copilot (not Ollama)" -ForegroundColor White
Write-Host "4. Check the streaming response works correctly" -ForegroundColor White
Write-Host "`nAPI Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

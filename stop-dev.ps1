# Stop Development Environment
# Stops database containers and cleans up temp files

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Stop Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop database containers
Write-Host "Stopping database containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database containers stopped" -ForegroundColor Green
} else {
    Write-Host "WARNING: Some containers may still be running" -ForegroundColor Yellow
}

# Clean up temp files
Write-Host ""
Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
if (Test-Path "temp-start-backend.ps1") { Remove-Item "temp-start-backend.ps1" -Force }
if (Test-Path "temp-start-ui.ps1") { Remove-Item "temp-start-ui.ps1" -Force }
Write-Host "✓ Cleanup complete" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Services Stopped" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Backend and UI processes in other terminals" -ForegroundColor Yellow
Write-Host "need to be stopped manually (Ctrl+C)" -ForegroundColor Yellow
Write-Host ""

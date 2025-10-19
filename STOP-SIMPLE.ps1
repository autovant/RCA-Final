# Stop Simple Demo

Write-Host "Stopping services..." -ForegroundColor Yellow

# Stop Docker containers
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f deploy/docker/docker-compose.yml down"

# Clean up temp files
if (Test-Path "temp-start-ui.ps1") { Remove-Item "temp-start-ui.ps1" -Force }

Write-Host "✓ All services stopped" -ForegroundColor Green
Write-Host "Remember to close the UI terminal window (Ctrl+C)" -ForegroundColor Yellow

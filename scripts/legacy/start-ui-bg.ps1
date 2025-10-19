# Start UI in background
Set-Location "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\ui"

Write-Host "`n===================================`nStarting RCA Engine UI`n===================================`n" -ForegroundColor Cyan
Write-Host "The UI will be available at: http://localhost:3000" -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000`n" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

npm run dev

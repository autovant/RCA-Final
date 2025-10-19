@echo off
:: Quick fix: Restart Docker networking and start services

echo.
echo Restarting Docker to clear port bindings...
echo.

wsl bash -c "docker restart $(docker ps -aq) 2>/dev/null || true"
timeout /t 5 /nobreak >nul

echo.
echo Starting backend services...
echo.

wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d db redis ollama"

timeout /t 10 /nobreak >nul

echo.
echo Attempting to start API...
echo.

wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d rca_core"

if %errorLevel% equ 0 (
    echo.
    echo Backend services started successfully!
    echo API will be at: http://localhost:8000
    echo.
) else (
    echo.
    echo Could not bind port 8000. Port may still be in use.
    echo.
    echo Quick fixes:
    echo 1. Restart your computer ^(clears all port bindings^)
    echo 2. Run: wsl --shutdown  ^(then run this script again^)
    echo 3. Change API port to 8080 in docker-compose.yml
    echo.
)

echo.
echo To start the UI in Windows, run: start-ui-windows.bat
echo.
pause

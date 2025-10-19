@echo off
:: Start Backend Services Only (no UI)
:: Use this when running the UI in Windows

echo.
echo ===================================
echo Starting Backend Services
echo ===================================
echo.
echo This will start:
echo   - PostgreSQL Database (port 15432)
echo   - Redis (port 6379)
echo   - Ollama LLM (port 11434)
echo   - API Backend (port 8000)
echo.
echo The UI will NOT be started - run it separately in Windows
echo.

wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d rca_core rca_db redis ollama"

if %errorLevel% equ 0 (
    echo.
    echo ===================================
    echo Backend Services Started!
    echo ===================================
    echo.
    echo Services:
    echo   - API:      http://localhost:8000
    echo   - API Docs: http://localhost:8000/docs
    echo   - Database: localhost:15432
    echo.
    echo Now start the UI in Windows:
    echo   1. Open a new terminal
    echo   2. Run: start-ui-windows.bat
    echo.
) else (
    echo.
    echo ERROR: Failed to start backend services
    echo.
    pause
    exit /b 1
)

pause

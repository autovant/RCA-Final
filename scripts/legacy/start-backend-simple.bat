@echo off
echo ============================================================
echo   RCA-Final Backend Server
echo   Starting on http://localhost:8001
echo   Press Ctrl+C to stop
echo ============================================================
echo.
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && source venv-wsl/bin/activate && python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload"

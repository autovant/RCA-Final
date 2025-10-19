@echo off
REM Quick Port Forwarding Script for RCA Engine
REM Run this as Administrator to enable localhost access

echo.
echo ========================================
echo RCA Engine - Port Forwarding Setup
echo ========================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script requires Administrator privileges!
    echo.
    echo Please right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Getting WSL2 IP address...
for /f "tokens=1" %%i in ('wsl hostname -I') do set WSL_IP=%%i

if "%WSL_IP%"=="" (
    echo ERROR: Could not get WSL2 IP address
    echo Make sure WSL is running
    pause
    exit /b 1
)

echo WSL2 IP: %WSL_IP%
echo.

echo Removing old port forwarding rules...
netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0 2>nul
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>nul
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0 2>nul
netsh interface portproxy delete v4tov4 listenport=15432 listenaddress=0.0.0.0 2>nul

echo.
echo Setting up port forwarding...
echo   Port 3000 - UI (Next.js)
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=%WSL_IP%

echo   Port 8000 - API (FastAPI)
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=%WSL_IP%

echo   Port 8001 - Metrics
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=%WSL_IP%

echo   Port 15432 - PostgreSQL
netsh interface portproxy add v4tov4 listenport=15432 listenaddress=0.0.0.0 connectport=15432 connectaddress=%WSL_IP%

echo.
echo Adding Windows Firewall rules...
netsh advfirewall firewall delete rule name="RCA Engine UI" >nul 2>&1
netsh advfirewall firewall delete rule name="RCA Engine API" >nul 2>&1
netsh advfirewall firewall delete rule name="RCA Engine Metrics" >nul 2>&1
netsh advfirewall firewall delete rule name="RCA Engine DB" >nul 2>&1

netsh advfirewall firewall add rule name="RCA Engine UI" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="RCA Engine API" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="RCA Engine Metrics" dir=in action=allow protocol=TCP localport=8001
netsh advfirewall firewall add rule name="RCA Engine DB" dir=in action=allow protocol=TCP localport=15432

echo.
echo ========================================
echo Current port forwarding configuration:
echo ========================================
netsh interface portproxy show v4tov4

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo You can now access your application at:
echo   UI:       http://localhost:3000
echo   API:      http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo Note: If WSL2 restarts, you'll need to run this again
echo       (WSL2 IP addresses can change on restart)
echo.
pause

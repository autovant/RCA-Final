@echo off
:: RCA Engine - Network Access Setup
:: Run this as Administrator

echo.
echo ===================================
echo RCA Engine Network Access Setup
echo ===================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo.
    echo Right-click on this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Running as Administrator...
echo.

:: Get WSL IP address
echo Getting WSL IP address...
for /f "tokens=1" %%i in ('wsl hostname -I') do set WSL_IP=%%i
echo WSL IP: %WSL_IP%
echo.

:: Remove old rules first
echo Removing old port forwarding rules...
netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0 >nul 2>&1
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 >nul 2>&1
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0 >nul 2>&1
echo Done.
echo.

:: Set up port forwarding
echo Setting up port forwarding...
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=%WSL_IP%
if %errorLevel% equ 0 (
    echo [OK] Port 3000 ^(UI^) forwarded to WSL
) else (
    echo [WARN] Port 3000 may already be configured
)

netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=%WSL_IP%
if %errorLevel% equ 0 (
    echo [OK] Port 8000 ^(API^) forwarded to WSL
) else (
    echo [WARN] Port 8000 may already be configured
)

netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=%WSL_IP%
if %errorLevel% equ 0 (
    echo [OK] Port 8001 ^(Metrics^) forwarded to WSL
) else (
    echo [WARN] Port 8001 may already be configured
)
echo.

:: Show current rules
echo Current port forwarding rules:
netsh interface portproxy show all
echo.

:: Set up firewall rules
echo Setting up firewall rules...
netsh advfirewall firewall delete rule name="RCA Engine UI" >nul 2>&1
netsh advfirewall firewall delete rule name="RCA Engine API" >nul 2>&1
netsh advfirewall firewall delete rule name="RCA Engine Metrics" >nul 2>&1

netsh advfirewall firewall add rule name="RCA Engine UI" dir=in action=allow protocol=TCP localport=3000 >nul
if %errorLevel% equ 0 (
    echo [OK] Firewall rule added for UI ^(port 3000^)
) else (
    echo [ERROR] Failed to add firewall rule for UI
)

netsh advfirewall firewall add rule name="RCA Engine API" dir=in action=allow protocol=TCP localport=8000 >nul
if %errorLevel% equ 0 (
    echo [OK] Firewall rule added for API ^(port 8000^)
) else (
    echo [ERROR] Failed to add firewall rule for API
)

netsh advfirewall firewall add rule name="RCA Engine Metrics" dir=in action=allow protocol=TCP localport=8001 >nul
if %errorLevel% equ 0 (
    echo [OK] Firewall rule added for Metrics ^(port 8001^)
) else (
    echo [ERROR] Failed to add firewall rule for Metrics
)
echo.

:: Test connectivity
echo Testing connectivity...
timeout /t 2 /nobreak >nul

curl -s -o nul -w "API Status: %%{http_code}\n" http://localhost:8000/api/health/live
curl -s -o nul -w "UI Status: %%{http_code}\n" http://localhost:3000/

echo.
echo ===================================
echo Setup Complete!
echo ===================================
echo.
echo You can now access:
echo   UI:      http://localhost:3000
echo   API:     http://localhost:8000
echo   Docs:    http://localhost:8000/docs
echo   Metrics: http://localhost:8001/metrics
echo.
echo Opening in browser...
start http://localhost:3000
start http://localhost:8000/docs
echo.
echo To remove these settings later, run: cleanup-network.bat
echo.
pause

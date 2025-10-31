@echo off
:: RCA Engine - Network Access Cleanup
:: Run this as Administrator to remove port forwarding and firewall rules

echo.
echo ===================================
echo RCA Engine Network Access Cleanup
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

:: Remove port forwarding rules
echo Removing port forwarding rules...
netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0
echo Done.
echo.

:: Remove firewall rules
echo Removing firewall rules...
netsh advfirewall firewall delete rule name="RCA Engine UI"
netsh advfirewall firewall delete rule name="RCA Engine API"
netsh advfirewall firewall delete rule name="RCA Engine Metrics"
echo Done.
echo.

echo ===================================
echo Cleanup Complete!
echo ===================================
echo.
pause

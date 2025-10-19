@echo off
:: RCA Engine UI - Windows Setup and Start
:: This script sets up and runs the UI in Windows (not Docker)

echo.
echo ===================================
echo RCA Engine UI - Windows Setup
echo ===================================
echo.

cd /d "%~dp0ui"

:: Check if node_modules exists
if not exist "node_modules\" (
    echo Installing dependencies...
    echo This may take a few minutes on first run...
    echo.
    call npm install
    if %errorLevel% neq 0 (
        echo.
        echo ERROR: npm install failed
        echo Make sure Node.js is installed: https://nodejs.org/
        echo.
        pause
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully!
    echo.
) else (
    echo Dependencies already installed.
    echo.
)

:: Check if .env.local exists
if not exist ".env.local" (
    echo Creating .env.local configuration...
    (
        echo NEXT_PUBLIC_API_URL=http://localhost:8000
        echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
        echo NODE_ENV=development
    ) > .env.local
    echo Configuration created!
    echo.
)

echo ===================================
echo Starting UI Development Server
echo ===================================
echo.
echo The UI will be available at:
echo   http://localhost:3000
echo.
echo Make sure the backend API is running:
echo   Backend: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

:: Start the dev server
call npm run dev

#!/usr/bin/env pwsh
#Requires -Version 7

<#
.SYNOPSIS
    Restart just the backend server
.DESCRIPTION
    Stops the currently running backend and starts it fresh to pick up new .env changes
#>

param()

$ErrorActionPreference = "Stop"

Write-Host "`n═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " 🔄 Restarting RCA Backend" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Check if PID file exists
$pidFile = Join-Path $PSScriptRoot ".local-pids.json"
if (Test-Path $pidFile) {
    try {
        $pids = Get-Content $pidFile | ConvertFrom-Json
        if ($pids.backend) {
            Write-Host "⏹️  Stopping existing backend (PID: $($pids.backend))..." -ForegroundColor Yellow
            try {
                Stop-Process -Id $pids.backend -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
                Write-Host "✅ Backend stopped" -ForegroundColor Green
            }
            catch {
                Write-Host "⚠️  Backend process may have already stopped" -ForegroundColor Yellow
            }
        }
    }
    catch {
        Write-Host "⚠️  Could not read PID file, continuing..." -ForegroundColor Yellow
    }
}
else {
    Write-Host "⚠️  No PID file found, will start fresh backend" -ForegroundColor Yellow
}

# Check if venv exists
$venvPath = Join-Path $PSScriptRoot "venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "❌ Virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "🚀 Starting backend on port 8002..." -ForegroundColor Cyan

# Start backend in a new terminal window
$backendCmd = "& `"$pythonExe`" -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8002 --reload"

$startParams = @{
    FilePath     = "wt.exe"
    ArgumentList = "-w 0 nt --title `"RCA Backend - Port 8002`" pwsh.exe -NoExit -Command `"cd '$PSScriptRoot'; Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan; Write-Host ' 🚀 RCA Backend API - Port 8002' -ForegroundColor Cyan; Write-Host '═══════════════════════════════════════════════════════' -ForegroundColor Cyan; Write-Host ''; Write-Host '📍 API Docs:  http://localhost:8002/docs' -ForegroundColor Green; Write-Host '❤️  Health:    http://localhost:8002/health' -ForegroundColor Green; Write-Host '🔄 Hot-reload: Enabled' -ForegroundColor Green; Write-Host ''; Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow; Write-Host ''; $backendCmd`""
    PassThru     = $true
}

try {
    $process = Start-Process @startParams
    Start-Sleep -Seconds 2
    
    # Try to find the Python process (it's a child of the terminal)
    $pythonProcess = Get-Process python -ErrorAction SilentlyContinue | 
                     Where-Object { $_.CommandLine -like "*uvicorn*apps.api.main*8002*" } |
                     Select-Object -First 1
    
    if ($pythonProcess) {
        # Update PID file
        if (Test-Path $pidFile) {
            $pids = Get-Content $pidFile | ConvertFrom-Json
            $pids.backend = $pythonProcess.Id
            $pids | ConvertTo-Json | Set-Content $pidFile
            Write-Host "✅ Backend restarted (PID: $($pythonProcess.Id))" -ForegroundColor Green
        }
    }
    else {
        Write-Host "✅ Backend terminal launched (PID may not be immediately available)" -ForegroundColor Green
    }
    
    Write-Host "`n📡 Backend should start in a few seconds..." -ForegroundColor Cyan
    Write-Host "📍 Check: http://localhost:8002/docs" -ForegroundColor Green
    Write-Host "❤️  Health: http://localhost:8002/health" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to start backend: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Backend restart complete!" -ForegroundColor Green

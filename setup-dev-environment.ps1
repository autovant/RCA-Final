# Setup Development Environment for Windows
# This creates a Python virtual environment and installs dependencies
# Run this ONCE after cloning the repo

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Dev Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green

# Check if Python version is 3.11+
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "WARNING: Python 3.11+ is recommended. You have Python $major.$minor" -ForegroundColor Yellow
    }
}

# Check Node.js installation
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Node.js is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Found: Node.js $nodeVersion" -ForegroundColor Green

# Create Python virtual environment
Write-Host ""
Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists. Skipping..." -ForegroundColor Yellow
} else {
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment and install dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes..." -ForegroundColor Gray

& "venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "venv\Scripts\pip.exe" install -r requirements.txt --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to install Python dependencies" -ForegroundColor Red
    Write-Host "Try running manually:" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\activate" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# Install UI dependencies
Write-Host ""
Write-Host "Installing UI dependencies..." -ForegroundColor Yellow
Write-Host "This may take 1-2 minutes..." -ForegroundColor Gray

Push-Location ui
npm install --silent
$npmResult = $LASTEXITCODE
Pop-Location

if ($npmResult -eq 0) {
    Write-Host "✓ UI dependencies installed" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to install UI dependencies" -ForegroundColor Red
    exit 1
}

# Check Docker (via WSL)
Write-Host ""
Write-Host "Checking WSL Docker setup..." -ForegroundColor Yellow

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: WSL is not available on this machine" -ForegroundColor Red
    Write-Host "Please enable Windows Subsystem for Linux and install a distro with Docker Engine" -ForegroundColor Yellow
    Write-Host "Guide: https://learn.microsoft.com/windows/wsl/install" -ForegroundColor White
    exit 1
}

$dockerVersion = & wsl.exe -e docker --version 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker CLI is not available inside WSL" -ForegroundColor Red
    Write-Host "Ensure your WSL distribution has Docker Engine running and accessible" -ForegroundColor Yellow
    Write-Host "Example (Ubuntu): sudo service docker start" -ForegroundColor White
    Write-Host "Verify with: wsl.exe -e docker ps" -ForegroundColor White
    exit 1
}

Write-Host "✓ WSL Docker detected: $dockerVersion" -ForegroundColor Green

# Create .env file if it doesn't exist
Write-Host ""
Write-Host "Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    @"
# Database Configuration
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine
POSTGRES_HOST=localhost
POSTGRES_PORT=15432

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-min-32-chars

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
DEFAULT_PROVIDER=copilot
GITHUB_TOKEN=your_github_pat_with_copilot_scope

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Redis (optional)
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=16379

# Feature Flags
RELATED_INCIDENTS_ENABLED=true
PLATFORM_DETECTION_ENABLED=true
ARCHIVE_EXPANDED_FORMATS_ENABLED=true
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✓ .env file created (edit for your settings)" -ForegroundColor Green
} else {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete! ✓" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review .env file and update if needed" -ForegroundColor White
Write-Host "  2. Start development: .\start-dev.ps1" -ForegroundColor White
Write-Host ""
Write-Host "For demos/presentations: .\start-demo.ps1" -ForegroundColor White
Write-Host ""

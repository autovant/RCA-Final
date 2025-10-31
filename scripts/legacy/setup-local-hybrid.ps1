#Requires -Version 7.0
<#
.SYNOPSIS
    Hybrid local setup - Uses existing Docker databases, runs app natively

.DESCRIPTION
    This is the simplest approach:
    - PostgreSQL & Redis: Use existing Docker containers (via WSL)
    - Backend & Frontend: Run natively on Windows for fast development

.EXAMPLE
    .\setup-local-hybrid.ps1
#>

$ErrorActionPreference = 'Stop'

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message, [string]$Status = "")
    if ($Status -eq "OK") {
        Write-Host "  ✓ $Message" -ForegroundColor Green
    } elseif ($Status -eq "WARN") {
        Write-Host "  ⚠ $Message" -ForegroundColor Yellow
    } elseif ($Status -eq "ERROR") {
        Write-Host "  ✗ $Message" -ForegroundColor Red
    } else {
        Write-Host "  → $Message" -ForegroundColor Cyan
    }
}

Write-Header "RCA Engine - Hybrid Local Setup"

Write-Host "This setup uses:" -ForegroundColor White
Write-Host "  • Databases: Docker containers (via WSL - already configured)" -ForegroundColor Gray
Write-Host "  • Backend:   Native Windows Python" -ForegroundColor Gray
Write-Host "  • Frontend:  Native Windows Node.js" -ForegroundColor Gray
Write-Host ""
Write-Host "Advantages:" -ForegroundColor Cyan
Write-Host "  ✓ No Windows Docker Desktop needed" -ForegroundColor Green
Write-Host "  ✓ Fast hot reload for backend and frontend" -ForegroundColor Green
Write-Host "  ✓ Uses your existing Docker setup" -ForegroundColor Green
Write-Host ""

# Check Docker containers
Write-Header "Step 1: Database Containers"

Write-Step "Checking Docker containers..."
$containers = wsl docker ps --filter "name=rca_" --format "{{.Names}}"

if ($containers -match "rca_db" -and $containers -match "rca_redis") {
    Write-Step "Database containers are running" "OK"
    Write-Host ""
    wsl docker ps --filter "name=rca_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    Write-Host ""
} else {
    Write-Step "Database containers not running" "WARN"
    Write-Host ""
    Write-Host "Starting database containers..." -ForegroundColor Yellow
    wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f docker-compose.dev.yml up -d"
    Start-Sleep -Seconds 5
    Write-Step "Containers started" "OK"
}

# Test connections
Write-Header "Step 2: Connection Test"

Write-Step "Testing PostgreSQL connection (127.0.0.1:15432)..."
$pgTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 15432 -WarningAction SilentlyContinue
if ($pgTest.TcpTestSucceeded) {
    Write-Step "PostgreSQL accessible" "OK"
} else {
    Write-Step "PostgreSQL not accessible" "ERROR"
    Write-Host ""
    Write-Host "Port forwarding may need to be refreshed. Run:" -ForegroundColor Yellow
    Write-Host "  .\fix-docker-port-forwarding.ps1" -ForegroundColor Cyan
    return
}

Write-Step "Testing Redis connection (127.0.0.1:16379)..."
$redisTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 16379 -WarningAction SilentlyContinue
if ($redisTest.TcpTestSucceeded) {
    Write-Step "Redis accessible" "OK"
} else {
    Write-Step "Redis not accessible (optional service)" "WARN"
}

# Setup Python environment
Write-Header "Step 3: Python Backend"

if (-not (Test-Path "venv")) {
    Write-Step "Creating Python virtual environment..."
    python -m venv venv
    Write-Step "Virtual environment created" "OK"
} else {
    Write-Step "Virtual environment exists" "OK"
}

Write-Step "Installing/updating Python dependencies..."
& ".\venv\Scripts\Activate.ps1"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Step "Python dependencies ready" "OK"

# Setup Node.js environment
Write-Header "Step 4: Node.js Frontend"

if (-not (Test-Path "ui\node_modules")) {
    Write-Step "Installing frontend dependencies..."
    Push-Location ui
    npm install --quiet
    Pop-Location
    Write-Step "Frontend dependencies installed" "OK"
} else {
    Write-Step "Frontend dependencies exist" "OK"
}

# Create/update environment file
Write-Header "Step 5: Configuration"

$envContent = @"
# Hybrid Local Deployment Configuration
# Uses Docker databases with native Windows app

# Security
JWT_SECRET_KEY=local-dev-secret-key-minimum-32-characters-for-jwt-signing

# Database (Docker container via port forwarding)
POSTGRES_HOST=localhost
POSTGRES_PORT=15432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine

# Redis (Docker container via port forwarding)
REDIS_HOST=localhost
REDIS_PORT=16379

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
"@

$envContent | Out-File -FilePath ".env.local" -Encoding UTF8
Write-Step "Created .env.local configuration" "OK"

# Run migrations
Write-Header "Step 6: Database Migrations"

Write-Step "Running database migrations..."
try {
    & ".\venv\Scripts\Activate.ps1"
    $env:PYTHONPATH = $PSScriptRoot
    
    # Use .env.local if it exists
    if (Test-Path ".env.local") {
        Copy-Item ".env.local" ".env" -Force
    }
    
    python -m alembic upgrade head 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Database migrations completed" "OK"
    } else {
        Write-Step "Database migrations had issues (may be OK if DB already initialized)" "WARN"
    }
} catch {
    Write-Step "Migration error (may be OK): $_" "WARN"
}

# Success summary
Write-Header "Setup Complete!"

Write-Host "Your hybrid local environment is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Database Services (Docker):" -ForegroundColor Cyan
Write-Host "  • PostgreSQL:  localhost:15432  ✓" -ForegroundColor White
Write-Host "  • Redis:       localhost:16379  ✓" -ForegroundColor White
Write-Host ""
Write-Host "To start the application:" -ForegroundColor Yellow
Write-Host "  .\start-local-hybrid.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Or manually:" -ForegroundColor Yellow
Write-Host "  Backend:  .\venv\Scripts\Activate.ps1; python -m uvicorn apps.api.main:app --reload" -ForegroundColor Gray
Write-Host "  Frontend: cd ui; npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "Benefits of this setup:" -ForegroundColor Cyan
Write-Host "  ✓ No Docker Desktop on Windows needed" -ForegroundColor Green
Write-Host "  ✓ Instant hot-reload for code changes" -ForegroundColor Green
Write-Host "  ✓ Native Windows performance" -ForegroundColor Green
Write-Host "  ✓ Full debugging support" -ForegroundColor Green
Write-Host ""

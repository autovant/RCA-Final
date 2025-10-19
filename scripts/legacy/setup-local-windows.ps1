#Requires -Version 7.0
<#
.SYNOPSIS
    Complete local Windows setup for RCA Engine (No Docker Required)

.DESCRIPTION
    This script sets up a complete local development environment on Windows:
    - PostgreSQL with pgvector
    - Redis (Windows port)
    - Python backend with all dependencies
    - Node.js frontend
    All services run natively on Windows for maximum performance.

.EXAMPLE
    .\setup-local-windows.ps1
#>

param(
    [switch]$SkipPackageInstall,
    [switch]$ResetDatabase,
    [string]$PostgresPort = "5433",
    [string]$RedisPort = "6380"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Add Chocolatey to PATH immediately if it exists
$ChocolateyPath = "C:\ProgramData\chocolatey\bin"
if (Test-Path $ChocolateyPath) {
    if ($env:Path -notlike "*$ChocolateyPath*") {
        $env:Path = "$ChocolateyPath;$env:Path"
        Write-Host "  → Added Chocolatey to current session PATH" -ForegroundColor Yellow
    }
}

# Configuration
$CONFIG = @{
    PostgresVersion = "15"
    PostgresPort = $PostgresPort
    PostgresUser = "rca_user"
    PostgresPassword = "rca_local_password"
    PostgresDB = "rca_engine"
    RedisPort = $RedisPort
    PythonMinVersion = "3.10"
    NodeMinVersion = "18"
    DataDir = "$PSScriptRoot\local-data"
    LogDir = "$PSScriptRoot\local-logs"
    BackendPort = "8001"
    FrontendPort = "3000"
}

# Helper Functions
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

function Test-Command {
    param([string]$Command)
    return $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Get-InstalledVersion {
    param([string]$Command, [string]$VersionArg = "--version")
    try {
        $output = & $Command $VersionArg 2>&1 | Select-Object -First 1
        return $output.ToString().Trim()
    } catch {
        return $null
    }
}

function Install-Chocolatey {
    # First, try to refresh PATH in case Chocolatey is installed but not in current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (-not (Test-Command "choco")) {
        Write-Step "Installing Chocolatey package manager..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Step "Chocolatey installed" "OK"
    } else {
        Write-Step "Chocolatey already installed" "OK"
    }
}

function Install-PostgreSQL {
    Write-Step "Checking PostgreSQL installation..."
    
    if (Test-Command "psql") {
        $version = Get-InstalledVersion "psql" "--version"
        Write-Step "PostgreSQL already installed: $version" "OK"
        return $true
    }

    if ($SkipPackageInstall) {
        Write-Step "Skipping PostgreSQL installation (use -SkipPackageInstall:$false to install)" "WARN"
        return $false
    }

    Write-Step "Installing PostgreSQL $($CONFIG.PostgresVersion)..."
    try {
        $chocoCmd = "C:\ProgramData\chocolatey\bin\choco.exe"
        & $chocoCmd install postgresql$($CONFIG.PostgresVersion) -y --params "/Password:$($CONFIG.PostgresPassword) /Port:$($CONFIG.PostgresPort)"
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Step "PostgreSQL installed successfully" "OK"
        return $true
    } catch {
        Write-Step "Failed to install PostgreSQL: $_" "ERROR"
        return $false
    }
}

function Install-Redis {
    Write-Step "Checking Redis installation..."
    
    # Check if Redis is installed
    $redisExe = "C:\Program Files\Redis\redis-server.exe"
    if (Test-Path $redisExe) {
        Write-Step "Redis already installed" "OK"
        return $true
    }

    if ($SkipPackageInstall) {
        Write-Step "Skipping Redis installation (use -SkipPackageInstall:$false to install)" "WARN"
        return $false
    }

    Write-Step "Installing Redis for Windows..."
    try {
        # Redis for Windows is available via Chocolatey
        $chocoCmd = "C:\ProgramData\chocolatey\bin\choco.exe"
        & $chocoCmd install redis-64 -y
        
        Write-Step "Redis installed successfully" "OK"
        return $true
    } catch {
        Write-Step "Failed to install Redis: $_" "ERROR"
        return $false
    }
}

function Test-PostgresConnection {
    param([int]$MaxRetries = 5)
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $env:PGPASSWORD = $CONFIG.PostgresPassword
            $result = & psql -h localhost -p $CONFIG.PostgresPort -U postgres -d postgres -c "SELECT 1;" 2>&1
            if ($LASTEXITCODE -eq 0) {
                return $true
            }
        } catch {
            # Ignore
        }
        
        if ($i -lt $MaxRetries) {
            Write-Step "Waiting for PostgreSQL to start (attempt $i/$MaxRetries)..."
            Start-Sleep -Seconds 3
        }
    }
    
    return $false
}

function Setup-PostgresDatabase {
    Write-Step "Setting up PostgreSQL database..."
    
    $env:PGPASSWORD = $CONFIG.PostgresPassword
    
    # Create user
    Write-Step "Creating database user..."
    $createUser = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$($CONFIG.PostgresUser)') THEN
        CREATE USER $($CONFIG.PostgresUser) WITH PASSWORD '$($CONFIG.PostgresPassword)';
    END IF;
END
`$`$;
"@
    
    $createUser | & psql -h localhost -p $CONFIG.PostgresPort -U postgres -d postgres 2>&1 | Out-Null
    
    # Create database
    Write-Step "Creating database..."
    if ($ResetDatabase) {
        & psql -h localhost -p $CONFIG.PostgresPort -U postgres -d postgres -c "DROP DATABASE IF EXISTS $($CONFIG.PostgresDB);" 2>&1 | Out-Null
    }
    
    & psql -h localhost -p $CONFIG.PostgresPort -U postgres -d postgres -c "CREATE DATABASE $($CONFIG.PostgresDB) OWNER $($CONFIG.PostgresUser);" 2>&1 | Out-Null
    
    # Create pgvector extension
    Write-Step "Installing pgvector extension..."
    $env:PGPASSWORD = $CONFIG.PostgresPassword
    & psql -h localhost -p $CONFIG.PostgresPort -U $CONFIG.PostgresUser -d $CONFIG.PostgresDB -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 | Out-Null
    
    Write-Step "Database setup complete" "OK"
}

function Setup-PythonEnvironment {
    Write-Step "Setting up Python environment..."
    
    # Check Python
    if (-not (Test-Command "python")) {
        Write-Step "Python not found! Please install Python $($CONFIG.PythonMinVersion) or higher" "ERROR"
        return $false
    }
    
    $pythonVersion = python --version 2>&1
    Write-Step "Python version: $pythonVersion" "OK"
    
    # Create virtual environment
    if (-not (Test-Path "venv")) {
        Write-Step "Creating virtual environment..."
        python -m venv venv
    } else {
        Write-Step "Virtual environment already exists" "OK"
    }
    
    # Activate and install dependencies
    Write-Step "Installing Python dependencies..."
    & ".\venv\Scripts\Activate.ps1"
    
    # Upgrade pip
    python -m pip install --upgrade pip --quiet
    
    # Install requirements
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt --quiet
        Write-Step "Python dependencies installed" "OK"
    }
    
    return $true
}

function Setup-NodeEnvironment {
    Write-Step "Setting up Node.js environment..."
    
    # Check Node.js
    if (-not (Test-Command "node")) {
        Write-Step "Node.js not found! Please install Node.js $($CONFIG.NodeMinVersion) or higher" "ERROR"
        return $false
    }
    
    $nodeVersion = node --version
    Write-Step "Node.js version: $nodeVersion" "OK"
    
    # Install frontend dependencies
    if (Test-Path "ui/package.json") {
        Write-Step "Installing frontend dependencies..."
        Push-Location ui
        try {
            npm install --quiet 2>&1 | Out-Null
            Write-Step "Frontend dependencies installed" "OK"
        } finally {
            Pop-Location
        }
    }
    
    return $true
}

function Create-EnvironmentFile {
    Write-Step "Creating environment configuration..."

    $devToken = $null
    if (Test-Path ".env") {
        $tokenLine = Get-Content ".env" | Where-Object { $_ -match '^LOCAL_DEV_AUTH_TOKEN=' } | Select-Object -First 1
        if ($tokenLine) {
            $devToken = ($tokenLine -split "=", 2)[1].Trim('"')
        }
    }

    if (-not $devToken) {
        $devToken = ([guid]::NewGuid()).ToString("N")
    }
    
    $backendPort = if ($CONFIG.BackendPort) { $CONFIG.BackendPort } else { "8001" }
    $frontendPort = if ($CONFIG.FrontendPort) { $CONFIG.FrontendPort } else { "3000" }

    $envContent = @"
# Local Windows Deployment Configuration
# Generated on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Security
JWT_SECRET_KEY=local-development-secret-key-change-in-production-32chars-minimum

# Database Configuration (Local PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=$($CONFIG.PostgresPort)
POSTGRES_USER=$($CONFIG.PostgresUser)
POSTGRES_PASSWORD=$($CONFIG.PostgresPassword)
POSTGRES_DB=$($CONFIG.PostgresDB)

# Redis Configuration (Local Redis)
REDIS_HOST=localhost
REDIS_PORT=$($CONFIG.RedisPort)

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# CORS Configuration
CORS_ALLOW_ORIGINS=["http://localhost:$frontendPort","http://localhost:$backendPort"]

# Local development auth helper
LOCAL_DEV_AUTH_TOKEN=$devToken
LOCAL_DEV_USER_EMAIL=local.dev@localhost
LOCAL_DEV_USER_USERNAME=local-dev
LOCAL_DEV_USER_FULL_NAME=Local Development
"@

    $envContent | Out-File -FilePath ".env" -Encoding UTF8 -Force
    Write-Step "Environment file created" "OK"

    $uiEnvContent = @"
NEXT_PUBLIC_API_BASE_URL=http://localhost:$backendPort
NEXT_PUBLIC_API_AUTH_TOKEN=$devToken
"@

    $uiEnvPath = Join-Path "ui" ".env.local"
    $uiEnvContent | Out-File -FilePath $uiEnvPath -Encoding UTF8 -Force
    Write-Step "Updated ui/.env.local with API configuration" "OK"
}

function Start-PostgresService {
    Write-Step "Starting PostgreSQL service..."
    
    try {
        $services = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if (-not $services) {
            Write-Step "PostgreSQL service not found - may need manual start" "WARN"
            return $false
        }

        if (-not ($services -is [System.Array])) {
            $services = @($services)
        }

        $preference = @("postgresql-x64-15", "postgresql-x64-16", "postgresql-x64-14")
        $services = $services | Sort-Object {
            $name = $_.Name.ToLower()
            $index = $preference.IndexOf($name)
            if ($index -eq -1) { return 999 }
            return $index
        }, Name

        foreach ($svc in $services) {
            if ($svc.Status -eq "Running") {
                Write-Step "PostgreSQL service running ($($svc.Name))" "OK"
                return $true
            }

            try {
                Write-Step "Starting PostgreSQL service ($($svc.Name))..."
                Start-Service -Name $svc.Name -ErrorAction Stop
                Start-Sleep -Seconds 2

                $refreshed = Get-Service -Name $svc.Name -ErrorAction Stop
                if ($refreshed.Status -eq "Running") {
                    Write-Step "PostgreSQL service running ($($svc.Name))" "OK"
                    return $true
                }
            } catch {
                $message = $_.Exception.Message
                if ($message -match "Cannot open" -or $message -match "Access is denied") {
                    Write-Step "Insufficient permissions to control PostgreSQL service ($($svc.Name)). Run this setup script in an elevated PowerShell session if service control is required." "WARN"
                } else {
                    Write-Step "Failed to start PostgreSQL service ($($svc.Name)): $_" "WARN"
                }
            }
        }

        Write-Step "PostgreSQL service found but not running" "WARN"
        return $false
    } catch {
        Write-Step "Could not start PostgreSQL service: $_" "WARN"
        return $false
    }
}

function Start-RedisService {
    Write-Step "Starting Redis service..."
    
    try {
        $service = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
        if ($service) {
            if ($service.Status -ne "Running") {
                Start-Service $service.Name
                Start-Sleep -Seconds 2
            }
            Write-Step "Redis service running" "OK"
            return $true
        } else {
            Write-Step "Redis service not found - will start manually" "WARN"
            
            # Try to start Redis manually
            $redisExe = "C:\Program Files\Redis\redis-server.exe"
            if (Test-Path $redisExe) {
                Start-Process -FilePath $redisExe -ArgumentList "--port $($CONFIG.RedisPort)" -WindowStyle Hidden
                Start-Sleep -Seconds 2
                Write-Step "Redis started manually on port $($CONFIG.RedisPort)" "OK"
                return $true
            }
            return $false
        }
    } catch {
        Write-Step "Could not start Redis service: $_" "WARN"
        return $false
    }
}

function Initialize-Database {
    Write-Step "Running database migrations..."
    
    try {
        & ".\venv\Scripts\Activate.ps1"
        $env:PYTHONPATH = $PSScriptRoot
        python -m alembic upgrade head
        
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Database migrations completed" "OK"
            return $true
        } else {
            Write-Step "Database migrations failed" "ERROR"
            return $false
        }
    } catch {
        Write-Step "Error running migrations: $_" "ERROR"
        return $false
    }
}

function Test-ServiceHealth {
    param([string]$Url, [string]$Name)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Step "$Name is healthy" "OK"
        return $true
    } catch {
        Write-Step "$Name is not responding" "WARN"
        return $false
    }
}

# Main Installation Process
function Main {
    Write-Header "RCA Engine - Local Windows Setup"
    
    Write-Host "This script will set up a complete local development environment:" -ForegroundColor White
    Write-Host "  • PostgreSQL (native Windows service)" -ForegroundColor Gray
    Write-Host "  • Redis (native Windows service)" -ForegroundColor Gray
    Write-Host "  • Python backend (FastAPI)" -ForegroundColor Gray
    Write-Host "  • Node.js frontend (Next.js)" -ForegroundColor Gray
    Write-Host ""
    
    # Create directories
    Write-Step "Creating directories..."
    @($CONFIG.DataDir, $CONFIG.LogDir) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }
    }
    Write-Step "Directories created" "OK"
    
    # Step 1: Install Chocolatey
    Write-Header "Step 1: Package Manager"
    if (-not $SkipPackageInstall) {
        Install-Chocolatey
    } else {
        Write-Step "Skipping package manager setup" "WARN"
    }
    
    # Step 2: Install PostgreSQL
    Write-Header "Step 2: PostgreSQL Database"
    $postgresInstalled = Install-PostgreSQL
    
    if ($postgresInstalled) {
        Start-PostgresService
        
        if (Test-PostgresConnection) {
            Write-Step "PostgreSQL connection verified" "OK"
            Setup-PostgresDatabase
        } else {
            Write-Step "Could not connect to PostgreSQL" "ERROR"
            Write-Host ""
            Write-Host "Please ensure PostgreSQL is running and try again." -ForegroundColor Yellow
            Write-Host "You may need to restart this script or start PostgreSQL manually." -ForegroundColor Yellow
            return
        }
    }
    
    # Step 3: Install Redis
    Write-Header "Step 3: Redis Cache"
    $redisInstalled = Install-Redis
    
    if ($redisInstalled) {
        Start-RedisService
    }
    
    # Step 4: Python Environment
    Write-Header "Step 4: Python Backend"
    $pythonSetup = Setup-PythonEnvironment
    
    if (-not $pythonSetup) {
        Write-Host ""
        Write-Host "Python setup failed. Please install Python and try again." -ForegroundColor Red
        return
    }
    
    # Step 5: Node.js Environment
    Write-Header "Step 5: Node.js Frontend"
    $nodeSetup = Setup-NodeEnvironment
    
    if (-not $nodeSetup) {
        Write-Host ""
        Write-Host "Node.js setup failed. Please install Node.js and try again." -ForegroundColor Red
        return
    }
    
    # Step 6: Environment Configuration
    Write-Header "Step 6: Configuration"
    Create-EnvironmentFile
    
    # Step 7: Database Migrations
    Write-Header "Step 7: Database Initialization"
    Initialize-Database
    
    # Summary
    Write-Header "Setup Complete!"
    
    Write-Host "Your local Windows environment is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services configured:" -ForegroundColor Cyan
    Write-Host "  • PostgreSQL: localhost:$($CONFIG.PostgresPort)" -ForegroundColor White
    Write-Host "  • Redis:      localhost:$($CONFIG.RedisPort)" -ForegroundColor White
    Write-Host ""
    Write-Host "To start the application, run:" -ForegroundColor Yellow
    Write-Host "  .\start-local-windows.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or start services individually:" -ForegroundColor Yellow
    Write-Host "  Backend:  .\venv\Scripts\Activate.ps1; python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor Gray
    Write-Host "  Frontend: cd ui; npm run dev" -ForegroundColor Gray
    Write-Host ""
}

# Run main installation
Main

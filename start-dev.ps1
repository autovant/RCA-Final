# Start Development Environment
# Runs backend natively on Windows for fast development

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Development Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: WSL is not available on this machine." -ForegroundColor Red
    Write-Host "Enable Windows Subsystem for Linux and ensure Docker is installed inside it." -ForegroundColor Yellow
    exit 1
}

$script:RepoPath = (Get-Location).ProviderPath
$script:WslRepoPath = (& wsl.exe wslpath -a "$script:RepoPath" 2>$null).Trim()

if (-not $script:WslRepoPath) {
    Write-Host "ERROR: Unable to translate repository path into WSL." -ForegroundColor Red
    Write-Host "Ensure your WSL distribution can access the Windows filesystem (check /mnt/c mount)." -ForegroundColor Yellow
    exit 1
}

function Get-PortListener {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
            $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
            if ($conn) {
                $proc = $null
                try { $proc = Get-Process -Id $conn.OwningProcess -ErrorAction Stop } catch {}
                return [PSCustomObject]@{
                    Port        = $Port
                    ProcessId   = $conn.OwningProcess
                    ProcessName = if ($proc) { $proc.ProcessName } else { $null }
                }
            }
        }
    } catch {}

    try {
        $netstatLine = netstat -ano | Select-String -Pattern "[:\.]$Port\s" | Select-Object -First 1
        if ($netstatLine) {
            $netstatPid = ($netstatLine.Line -split '\s+')[-1]
            $proc = $null
            try { $proc = Get-Process -Id $netstatPid -ErrorAction Stop } catch {}
            return [PSCustomObject]@{
                Port        = $Port
                ProcessId   = [int]$netstatPid
                ProcessName = if ($proc) { $proc.ProcessName } else { $null }
            }
        }
    } catch {}

    return $null
}

function Assert-PortFree {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Description
    )

    $listener = Get-PortListener -Port $Port
    if ($listener) {
        $owner = if ($listener.ProcessName) { "${($listener.ProcessName)} (PID $($listener.ProcessId))" } else { "PID $($listener.ProcessId)" }
        Write-Host "ERROR: $Description requires port $Port, but it is currently in use by $owner." -ForegroundColor Red
        Write-Host "Stop the conflicting process or adjust your configuration, then rerun this script." -ForegroundColor Yellow
        exit 1
    }
}

function Get-WslComposeBinary {
    if ($script:ComposeBinary) {
        return $script:ComposeBinary
    }

    $probe = & wsl.exe bash -lc "if docker compose version >/dev/null 2>&1; then echo 'docker compose'; elif command -v docker-compose >/dev/null 2>&1; then echo 'docker-compose'; else echo ''; fi"
    $candidate = $probe.Trim()

    if ([string]::IsNullOrWhiteSpace($candidate)) {
        Write-Host "ERROR: docker compose is not available inside WSL." -ForegroundColor Red
        Write-Host "Make sure Docker Desktop integration is enabled or install docker-compose." -ForegroundColor Yellow
        exit 1
    }

    $script:ComposeBinary = $candidate
    return $script:ComposeBinary
}

function Invoke-WslRepoCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    & wsl.exe bash -lc "cd '$script:WslRepoPath' && $Command"
}

function Invoke-WslCompose {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Arguments
    )

    $binary = Get-WslComposeBinary
    Invoke-WslRepoCommand "$binary $Arguments"
}

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: .\setup-dev-environment.ps1" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please run: .\setup-dev-environment.ps1" -ForegroundColor Yellow
    exit 1
}

# Validate WSL Docker access
Write-Host "Validating WSL Docker access..." -ForegroundColor Yellow
Invoke-WslRepoCommand "docker ps >/dev/null 2>&1" | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Unable to reach Docker daemon inside WSL" -ForegroundColor Red
    Write-Host "Start Docker inside your WSL distribution (e.g., sudo service docker start)" -ForegroundColor Yellow
    Write-Host "Test manually with: wsl.exe -e docker ps" -ForegroundColor White
    exit 1
}

Write-Host "✓ WSL Docker daemon reachable" -ForegroundColor Green

# Ensure previous containers are stopped to avoid naming conflicts
Write-Host "Cleaning up existing database containers..." -ForegroundColor Yellow
Invoke-WslCompose "-f docker-compose.dev.yml down --remove-orphans" | Out-Null

# `docker compose down` returns non-zero when services have never been started; treat that as informational
if ($LASTEXITCODE -ne 0) {
    Write-Host "No prior containers to remove (or cleanup already handled)." -ForegroundColor Gray
}

# Force-remove containers in case they were created outside docker compose scope
Invoke-WslRepoCommand "docker rm -f rca_db rca_redis >/dev/null 2>&1" | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Removed lingering containers (rca_db, rca_redis)." -ForegroundColor Gray
}

$portChecks = @(
    @{ Port = 15432; Description = "PostgreSQL development container" },
    @{ Port = 16379; Description = "Redis development container" }
)

Start-Sleep -Seconds 2

foreach ($check in $portChecks) {
    Assert-PortFree -Port $check.Port -Description $check.Description
}

# Optionally reset persistent data if credentials changed
if ($env:RESET_DB_STATE -eq "true") {
    Write-Host "RESET_DB_STATE=true detected; removing persistent Postgres/Redis volumes." -ForegroundColor Yellow
    Invoke-WslRepoCommand "docker volume rm rca-final_postgres_data >/dev/null 2>&1" | Out-Null
    Invoke-WslRepoCommand "docker volume rm rca-final_redis_data >/dev/null 2>&1" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Volumes already removed or not present." -ForegroundColor Gray
    } else {
        Write-Host "✓ Persistent volumes cleared" -ForegroundColor Green
    }
}

# Start database containers
Write-Host "Starting database containers..." -ForegroundColor Yellow
Invoke-WslCompose "-f docker-compose.dev.yml up -d db redis" | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start database containers" -ForegroundColor Red
    Write-Host "Ensure the WSL Docker daemon is running and has access to images" -ForegroundColor Yellow
    Write-Host "Check status with: wsl.exe -e docker ps" -ForegroundColor White
    exit 1
}

Write-Host "✓ Database containers started" -ForegroundColor Green

# Wait for database to be ready
Write-Host ""
Write-Host "Waiting for database to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$dbReady = $false

while (-not $dbReady -and $attempt -lt $maxAttempts) {
    $attempt++
    $healthCheck = Invoke-WslRepoCommand "docker inspect --format='{{.State.Health.Status}}' rca_db 2>/dev/null"
    if ($LASTEXITCODE -eq 0 -and $healthCheck.Trim() -eq "healthy") {
        $dbReady = $true
        Write-Host "✓ Database is ready!" -ForegroundColor Green
    } else {
        Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

if (-not $dbReady) {
    Write-Host "WARNING: Database health check timeout. Continuing anyway..." -ForegroundColor Yellow
}

# Run database migrations
Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Yellow

$venvPythonPath = Resolve-Path "venv\Scripts\python.exe" -ErrorAction SilentlyContinue

if (-not $venvPythonPath) {
    Write-Host "ERROR: Unable to locate virtualenv python executable" -ForegroundColor Red
    Write-Host "Expected at: venv\\Scripts\\python.exe" -ForegroundColor Yellow
    Write-Host "Please rerun .\\setup-dev-environment.ps1" -ForegroundColor Yellow
    exit 1
}

$wslVenvPython = (& wsl.exe wslpath -a $venvPythonPath 2>$null).Trim()

if (-not $wslVenvPython) {
    Write-Host "ERROR: Failed to map virtualenv python into WSL" -ForegroundColor Red
    Write-Host "Ensure WSL has interop enabled (wsl.exe --help) and rerun the script" -ForegroundColor Yellow
    exit 1
}

Invoke-WslRepoCommand "'$wslVenvPython' -m alembic upgrade head"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database migrations completed" -ForegroundColor Green
} else {
    Write-Host "WARNING: Migration issues detected (may be OK if DB is already migrated)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ready to Start Services!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open 3 separate terminals and run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Terminal 1 - Backend API:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\activate" -ForegroundColor White
Write-Host "  python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor White
Write-Host ""
Write-Host "Terminal 2 - Frontend UI:" -ForegroundColor Cyan
Write-Host "  cd ui" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Terminal 3 - Worker (Optional):" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\activate" -ForegroundColor White
Write-Host "  python -m apps.worker.main" -ForegroundColor White
Write-Host ""
Write-Host "Or use the quick start script: .\quick-start-dev.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Access your application:" -ForegroundColor Cyan
Write-Host "  UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""

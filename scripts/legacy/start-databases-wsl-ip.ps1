# Quick Fix: Start RCA with Direct WSL IP Connection
# This bypasses localhost issues by connecting directly to WSL IP
# No administrator rights needed

Write-Host "RCA Quick Start (Direct WSL IP Mode)" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Get WSL IP
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "WSL IP: $wslIP" -ForegroundColor Green

# Get current directory in WSL format
$currentDir = (Get-Location).Path
$wslDir = (wsl wslpath -a "$currentDir").Trim()

# Stop any existing containers
Write-Host ""
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
wsl bash -c "cd '$wslDir' && docker compose -f docker-compose.dev.yml down" 2>$null

# Start containers
Write-Host "Starting database containers..." -ForegroundColor Yellow
wsl bash -c "cd '$wslDir' && docker compose -f docker-compose.dev.yml up -d"

# Wait for containers to be healthy
Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$dbReady = $false
for ($i = 1; $i -le 30; $i++) {
    $healthStatus = wsl docker inspect --format='{{.State.Health.Status}}' rca_db 2>$null
    if ($healthStatus -eq 'healthy') {
        $dbReady = $true
        break
    }
    Write-Host "  Waiting for PostgreSQL... ($i/30)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if ($dbReady) {
    Write-Host "  ✓ PostgreSQL is healthy" -ForegroundColor Green
} else {
    Write-Host "  ! PostgreSQL health check timeout" -ForegroundColor Yellow
}

# Create/update .env file with WSL IP
Write-Host ""
Write-Host "Configuring environment variables..." -ForegroundColor Yellow

$envContent = @"
# Database Configuration (using WSL IP for Windows compatibility)
DATABASE_URL=postgresql://rca_user:rca_password_change_in_production@${wslIP}:15432/rca_engine
POSTGRES_HOST=${wslIP}
POSTGRES_PORT=15432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine

# Redis Configuration
REDIS_URL=redis://${wslIP}:16379/0
REDIS_HOST=${wslIP}
REDIS_PORT=16379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001

# Frontend Configuration  
NEXT_PUBLIC_API_URL=http://localhost:8001
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "  ✓ Created .env with WSL IP: $wslIP" -ForegroundColor Green

# Test connection
Write-Host ""
Write-Host "Testing database connection..." -ForegroundColor Yellow
$testConnection = wsl bash -c "PGPASSWORD=rca_password_change_in_production psql -h $wslIP -p 15432 -U rca_user -d rca_engine -c 'SELECT 1;' 2>&1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Database connection successful!" -ForegroundColor Green
} else {
    Write-Host "  ! Database connection test failed" -ForegroundColor Yellow
    Write-Host "    This is normal if psql is not installed in WSL" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Database Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Services are accessible at:" -ForegroundColor Yellow
Write-Host "  PostgreSQL: $wslIP:15432" -ForegroundColor White
Write-Host "  Redis:      $wslIP:16379" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run the backend: python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor White
Write-Host "  2. Run the UI: cd ui && npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Note: Your .env file has been updated to use WSL IP ($wslIP)" -ForegroundColor Cyan
Write-Host "      If WSL restarts, run this script again to update the IP" -ForegroundColor Cyan
Write-Host ""

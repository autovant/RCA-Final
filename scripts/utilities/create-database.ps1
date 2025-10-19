# Create RCA-Final Database
# This script creates the isolated database for RCA-Final app

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  RCA-Final Database Setup                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$psqlPath = "C:\Program Files\PostgreSQL\16\bin\psql.exe"

Write-Host "This script will create:" -ForegroundColor Yellow
Write-Host "  • Database: rca_engine_final" -ForegroundColor Cyan
Write-Host "  • User: rca_user (if doesn't exist)" -ForegroundColor Cyan
Write-Host "  • Extension: pgvector" -ForegroundColor Cyan
Write-Host ""

# Prompt for postgres password
$postgresPassword = Read-Host "Enter password for PostgreSQL 'postgres' user" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($postgresPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$env:PGPASSWORD = $plainPassword

try {
    Write-Host "→ Testing connection..." -ForegroundColor Cyan
    $result = & $psqlPath -h localhost -U postgres -d postgres -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to connect to PostgreSQL" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Connected to PostgreSQL" -ForegroundColor Green
    Write-Host ""

    # Create user if doesn't exist
    Write-Host "→ Creating user 'rca_user'..." -ForegroundColor Cyan
    $createUserSQL = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'rca_user') THEN
        CREATE USER rca_user WITH PASSWORD 'rca_local_password';
        RAISE NOTICE 'User rca_user created';
    ELSE
        RAISE NOTICE 'User rca_user already exists';
    END IF;
END
`$`$;
"@
    & $psqlPath -h localhost -U postgres -d postgres -c $createUserSQL
    Write-Host "✓ User ready" -ForegroundColor Green
    Write-Host ""

    # Create database if doesn't exist
    Write-Host "→ Creating database 'rca_engine_final'..." -ForegroundColor Cyan
    $createDbSQL = @"
SELECT 'CREATE DATABASE rca_engine_final OWNER rca_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rca_engine_final')\gexec
"@
    & $psqlPath -h localhost -U postgres -d postgres -c $createDbSQL
    Write-Host "✓ Database created" -ForegroundColor Green
    Write-Host ""

    # Grant privileges
    Write-Host "→ Granting privileges..." -ForegroundColor Cyan
    & $psqlPath -h localhost -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE rca_engine_final TO rca_user;"
    Write-Host "✓ Privileges granted" -ForegroundColor Green
    Write-Host ""

    # Install pgvector extension
    Write-Host "→ Installing pgvector extension..." -ForegroundColor Cyan
    & $psqlPath -h localhost -U postgres -d rca_engine_final -c "CREATE EXTENSION IF NOT EXISTS vector;"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ pgvector extension installed" -ForegroundColor Green
    } else {
        Write-Host "! pgvector extension not available (optional)" -ForegroundColor Yellow
    }
    Write-Host ""

    Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  Database Setup Complete!                              ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Database: rca_engine_final" -ForegroundColor Cyan
    Write-Host "User:     rca_user" -ForegroundColor Cyan
    Write-Host "Password: rca_local_password" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next step: Run database migrations" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "  python -m alembic upgrade head" -ForegroundColor Cyan
    Write-Host ""

} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
    exit 1
} finally {
    $env:PGPASSWORD = $null
}

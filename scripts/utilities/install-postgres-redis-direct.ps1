#Requires -RunAsAdministrator
#Requires -Version 7.0

<#
.SYNOPSIS
    Direct installation of PostgreSQL and Redis (No Chocolatey Required)

.DESCRIPTION
    This script downloads and installs PostgreSQL and Redis directly from official sources,
    bypassing the broken Chocolatey installation.
#>

param(
    [string]$PostgresPort = "5433",
    [string]$RedisPort = "6380"
)

$ErrorActionPreference = 'Stop'

# Configuration
$CONFIG = @{
    PostgresVersion = "15.8-1"
    PostgresPort = $PostgresPort
    PostgresPassword = "rca_local_password"
    RedisPort = $RedisPort
    DownloadDir = "$env:TEMP\rca-installers"
}

function Write-Step {
    param([string]$Message, [string]$Status = "INFO")
    $color = switch ($Status) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        default { "Cyan" }
    }
    $symbol = switch ($Status) {
        "OK" { "✓" }
        "WARN" { "!" }
        "ERROR" { "✗" }
        default { "→" }
    }
    Write-Host "  $symbol $Message" -ForegroundColor $color
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

# Create download directory
if (!(Test-Path $CONFIG.DownloadDir)) {
    New-Item -ItemType Directory -Path $CONFIG.DownloadDir -Force | Out-Null
}

Write-Header "Direct Installation of PostgreSQL and Redis"

# Install PostgreSQL
Write-Header "Step 1: PostgreSQL 15"

$pgInstalled = Get-Command psql -ErrorAction SilentlyContinue
if ($pgInstalled) {
    Write-Step "PostgreSQL already installed" "OK"
} else {
    Write-Step "Downloading PostgreSQL 15..."
    $pgUrl = "https://get.enterprisedb.com/postgresql/postgresql-$($CONFIG.PostgresVersion)-windows-x64.exe"
    $pgInstaller = Join-Path $CONFIG.DownloadDir "postgresql-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $pgUrl -OutFile $pgInstaller -UseBasicParsing
        Write-Step "Downloaded PostgreSQL installer" "OK"
        
        Write-Step "Installing PostgreSQL (this may take a few minutes)..."
        Write-Host "  Password for postgres user will be: $($CONFIG.PostgresPassword)" -ForegroundColor Yellow
        
        # Silent installation arguments
        $pgPrefix = "C:\Program Files\PostgreSQL\15"
        $pgDataDir = Join-Path $pgPrefix "data"

        $pgArgs = @(
            "--mode", "unattended",
            "--unattendedmodeui", "minimal",
            "--prefix", "`"$pgPrefix`"",
            "--datadir", "`"$pgDataDir`"",
            "--serverport", $CONFIG.PostgresPort,
            "--superpassword", $CONFIG.PostgresPassword,
            "--servicename", "postgresql-x64-15",
            "--install_runtimes", "0"
        )
        
        Start-Process -FilePath $pgInstaller -ArgumentList $pgArgs -Wait -NoNewWindow
        
        # Add PostgreSQL to PATH
    $pgBinPath = Join-Path $pgPrefix "bin"
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($machinePath -notlike "*$pgBinPath*") {
            [System.Environment]::SetEnvironmentVariable("Path", "$machinePath;$pgBinPath", "Machine")
            $env:Path = "$env:Path;$pgBinPath"
        }
        
        Write-Step "PostgreSQL installed successfully" "OK"
    } catch {
        Write-Step "Failed to install PostgreSQL: $_" "ERROR"
        exit 1
    }
}

# Install Redis
Write-Header "Step 2: Redis for Windows"

$redisExe = "C:\Program Files\Redis\redis-server.exe"
if (Test-Path $redisExe) {
    Write-Step "Redis already installed" "OK"
} else {
    Write-Step "Downloading Redis for Windows..."
    $redisUrl = "https://github.com/microsoftarchive/redis/releases/download/win-3.2.100/Redis-x64-3.2.100.msi"
    $redisInstaller = Join-Path $CONFIG.DownloadDir "redis-installer.msi"
    
    try {
        Invoke-WebRequest -Uri $redisUrl -OutFile $redisInstaller -UseBasicParsing
        Write-Step "Downloaded Redis installer" "OK"
        
        Write-Step "Installing Redis..."
        $msiArgs = @(
            "/i", "`"$redisInstaller`"",
            "/qn",
            "/norestart",
            "INSTALLFOLDER=`"C:\Program Files\Redis`""
        )
        
        Start-Process -FilePath "msiexec.exe" -ArgumentList $msiArgs -Wait -NoNewWindow
        
        # Configure Redis port
        $redisConf = "C:\Program Files\Redis\redis.windows-service.conf"
        if (Test-Path $redisConf) {
            (Get-Content $redisConf) -replace '^port 6379', "port $($CONFIG.RedisPort)" | Set-Content $redisConf
        }
        
        # Restart Redis service
        $redisService = Get-Service -Name Redis -ErrorAction SilentlyContinue
        if ($redisService) {
            Restart-Service -Name Redis -Force
            Write-Step "Redis service restarted on port $($CONFIG.RedisPort)" "OK"
        }
        
        Write-Step "Redis installed successfully" "OK"
    } catch {
        Write-Step "Failed to install Redis: $_" "ERROR"
        Write-Step "You can install manually from: https://github.com/microsoftarchive/redis/releases" "WARN"
    }
}

Write-Header "Installation Complete!"
Write-Host ""
Write-Host "Services installed:" -ForegroundColor Green
Write-Host "  • PostgreSQL 15 on port $($CONFIG.PostgresPort)" -ForegroundColor Cyan
Write-Host "  • Redis on port $($CONFIG.RedisPort)" -ForegroundColor Cyan
Write-Host ""
Write-Host "PostgreSQL superuser password: $($CONFIG.PostgresPassword)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Close and reopen PowerShell to refresh PATH" -ForegroundColor Cyan
Write-Host "  2. Run: .\setup-local-windows.ps1" -ForegroundColor Cyan
Write-Host ""

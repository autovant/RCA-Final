#!/usr/bin/env pwsh
# Quick script to restart just the backend containers

Write-Host '🔄 Restarting RCA Backend Containers...' -ForegroundColor Cyan

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
	Write-Host 'ERROR: WSL is not available on this system.' -ForegroundColor Red
	Write-Host 'Enable Windows Subsystem for Linux and ensure Docker is accessible inside it.' -ForegroundColor Yellow
	exit 1
}

$repoPath = (Get-Location).ProviderPath
$wslPath = (& wsl.exe wslpath -a "$repoPath" 2>$null).Trim()

if (-not $wslPath) {
	Write-Host 'ERROR: Unable to map repository path into WSL.' -ForegroundColor Red
	Write-Host 'Verify WSL integration and rerun the script.' -ForegroundColor Yellow
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
		Write-Host 'Stop the conflicting process or adjust your configuration, then rerun.' -ForegroundColor Yellow
		exit 1
	}
}

$dockerComposePath = 'deploy/docker/docker-compose.yml'

$composeBinary = wsl.exe bash -lc "if docker compose version >/dev/null 2>&1; then echo 'docker compose'; elif command -v docker-compose >/dev/null 2>&1; then echo 'docker-compose'; else echo ''; fi" | Out-String
$composeBinary = $composeBinary.Trim()

if ([string]::IsNullOrWhiteSpace($composeBinary)) {
	Write-Host 'ERROR: docker compose is not available inside WSL.' -ForegroundColor Red
	Write-Host 'Install Docker Compose or enable Docker Desktop WSL integration.' -ForegroundColor Yellow
	exit 1
}

$composeCommand = "cd '$wslPath' && $composeBinary -f '$dockerComposePath' up -d rca_db rca_core"

Write-Host '📦 Starting containers...' -ForegroundColor Yellow
wsl.exe bash -lc "cd '$wslPath' && $composeBinary -f '$dockerComposePath' stop rca_core rca_db" | Out-Null

Start-Sleep -Seconds 2

Assert-PortFree -Port 8000 -Description 'RCA API container'
Assert-PortFree -Port 8001 -Description 'RCA metrics container'
Assert-PortFree -Port 15432 -Description 'RCA PostgreSQL container'

wsl.exe bash -lc "$composeCommand"
if ($LASTEXITCODE -ne 0) {
	Write-Host 'ERROR: Failed to start backend containers via docker compose.' -ForegroundColor Red
	exit $LASTEXITCODE
}

Write-Host "`n⏳ Waiting for backend to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$status = wsl.exe bash -lc "docker ps --filter 'name=rca_core' --format '{{.Status}}'"
if ($LASTEXITCODE -ne 0) {
	Write-Host 'WARNING: Unable to query container status.' -ForegroundColor Yellow
	$status = 'unknown'
}
Write-Host "Backend status: $status" -ForegroundColor Green

Write-Host "`n✅ Testing backend health..." -ForegroundColor Yellow

if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
	$health = curl.exe -s http://localhost:8000/api/health/live
} else {
	$response = Invoke-WebRequest -Uri 'http://localhost:8000/api/health/live' -UseBasicParsing -Method Get -ErrorAction SilentlyContinue
	$health = if ($response) { $response.Content } else { 'unreachable' }
}

Write-Host "Health check: $health" -ForegroundColor Green

Write-Host "`n🎉 Backend restarted!" -ForegroundColor Green
Write-Host '   - Backend API: http://localhost:8000' -ForegroundColor Cyan
Write-Host '   - UI (if running): http://localhost:3000' -ForegroundColor Cyan
Write-Host "`n💡 Tip: Hard refresh your browser (Ctrl+Shift+R) to clear cache" -ForegroundColor Yellow
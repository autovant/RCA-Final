param(
	[switch]$IncludeWorker,
	[switch]$ResetData,
	[switch]$RunPlaywrightSmoke,
	[switch]$SkipDependencyInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Banner {
	param([string]$Message)

	Write-Host "" # spacer
	Write-Host $Message -ForegroundColor Cyan
	Write-Host ('=' * $Message.Length) -ForegroundColor Cyan
	Write-Host ""
}

function Write-Step {
	param(
		[string]$Message,
		[ConsoleColor]$Color = [ConsoleColor]::Yellow
	)

	Write-Host $Message -ForegroundColor $Color
}

function Ensure-Command {
	param(
		[Parameter(Mandatory = $true)][string]$Command,
		[string]$InstallHint = ""
	)

	if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
		if ($InstallHint) {
			throw "Required command '$Command' not found. $InstallHint"
		}

		throw "Required command '$Command' not found on PATH."
	}
}

function Invoke-WslRepoCommand {
	param(
		[Parameter(Mandatory = $true)][string]$Command
	)

	$repoPath = (Get-Location).Path
	$wslPath = (& wsl.exe wslpath -a "$repoPath" 2>$null).Trim()

	if (-not $wslPath) {
		throw "Unable to resolve repository path inside WSL. Ensure WSL is installed and accessible."
	}

	$output = & wsl.exe bash -lc "cd '$wslPath' && $Command"
	$exitCode = $LASTEXITCODE

	return [pscustomobject]@{
		Output = $output
		ExitCode = $exitCode
	}
}

function Ensure-Port-Free {
	param(
		[Parameter(Mandatory = $true)][int]$Port,
		[Parameter(Mandatory = $true)][string]$ServiceName
	)

	try {
		$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
	} catch {
		Write-Step "  Unable to inspect port $Port automatically (Get-NetTCPConnection not available)." ([ConsoleColor]::DarkYellow)
		return
	}

	if (-not $connections) {
		Write-Step "  ✓ Port $Port free for $ServiceName" ([ConsoleColor]::Green)
		return
	}

	$listenerPids = $connections | Select-Object -ExpandProperty OwningProcess -Unique

	foreach ($listenerPid in $listenerPids) {
		try {
			$proc = Get-Process -Id $listenerPid -ErrorAction Stop
			Write-Step "  Terminating process $($proc.ProcessName) (PID $listenerPid) using port $Port for $ServiceName" ([ConsoleColor]::Yellow)
			Stop-Process -Id $listenerPid -Force
		} catch {
			Write-Step "  Unable to terminate PID $listenerPid on port $Port. Try running PowerShell as Administrator." ([ConsoleColor]::Red)
		}
	}
}

function Get-DotEnvValue {
	param(
		[Parameter(Mandatory = $true)][string]$Key,
		[string]$Default = ""
	)

	if (-not (Test-Path ".env")) {
		return $Default
	}

	$line = Get-Content ".env" | Where-Object { $_ -match "^\s*${Key}\s*=" } | Select-Object -First 1
	if (-not $line) {
		return $Default
	}

	$value = $line -replace "^\s*${Key}\s*=\s*", ""
	$value = $value.Trim()

	if ($value.StartsWith('"') -and $value.EndsWith('"')) {
		$value = $value.Trim('"')
	}

	if ($value.StartsWith("'") -and $value.EndsWith("'")) {
		$value = $value.Trim("'")
	}

	if ([string]::IsNullOrWhiteSpace($value)) {
		return $Default
	}

	return $value
}

function Wait-For-ContainerHealthy {
	param(
		[Parameter(Mandatory = $true)][string]$ContainerName,
		[int]$TimeoutSeconds = 120
	)

	$elapsed = 0
	while ($elapsed -lt $TimeoutSeconds) {
		$result = Invoke-WslRepoCommand "docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>/dev/null"

		if ($result.ExitCode -eq 0 -and $result.Output.Trim() -eq 'healthy') {
			return $true
		}

		Start-Sleep -Seconds 3
		$elapsed += 3
	}

	return $false
}

function Wait-For-HttpEndpoint {
	param(
		[Parameter(Mandatory = $true)][string]$Url,
		[string]$Description,
		[int]$TimeoutSeconds = 90
	)

	$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

	while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
		try {
			$response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
			if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
				return $true
			}
		} catch {
			Start-Sleep -Seconds 3
		}
	}

	Write-Step "  WARNING: $Description did not respond within ${TimeoutSeconds}s." ([ConsoleColor]::DarkYellow)
	return $false
}

function Wait-For-TcpPort {
	param(
		[Parameter(Mandatory = $true)][string]$TargetHost,
		[Parameter(Mandatory = $true)][int]$TargetPort,
		[int]$TimeoutSeconds = 90
	)

	$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

	while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
		$client = [System.Net.Sockets.TcpClient]::new()
		try {
			$connectTask = $client.ConnectAsync($TargetHost, $TargetPort)
			if ($connectTask.Wait(2000) -and $client.Connected) {
				$client.Dispose()
				return $true
			}
		} catch {
			# ignore and retry
		} finally {
			$client.Dispose()
		}

		Start-Sleep -Seconds 2
	}

	Write-Step "  WARNING: TCP port $($TargetHost):$TargetPort not reachable within ${TimeoutSeconds}s." ([ConsoleColor]::DarkYellow)
	return $false
}

function Ensure-WindowsPortProxy {
	param(
		[Parameter(Mandatory = $true)][int]$Port,
		[Parameter(Mandatory = $true)][string]$ServiceName
	)

	if (-not (Get-Command Test-NetConnection -ErrorAction SilentlyContinue)) {
		return
	}

	try {
		$portTest = Test-NetConnection -ComputerName 'localhost' -Port $Port -WarningAction SilentlyContinue
	} catch {
		return
	}

	if ($portTest.TcpTestSucceeded) {
		return
	}

	Write-Step "Attempting automatic Windows port proxy repair for $ServiceName..." ([ConsoleColor]::Yellow)

	$scriptCandidates = @('setup-ports-admin.ps1', 'fix-wsl-port-forwarding.ps1')
	$scriptPath = $null

	foreach ($candidate in $scriptCandidates) {
		$fullPath = Join-Path (Get-Location) $candidate
		if (Test-Path $fullPath) {
			$scriptPath = $fullPath
			break
		}
	}

	if (-not $scriptPath) {
		Write-Step "  Unable to locate an automated port forwarding script. Please run setup-ports-admin.ps1 manually." ([ConsoleColor]::Red)
		return
	}

	try {
		$process = Start-Process -FilePath 'pwsh' -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath) -Verb RunAs -Wait -PassThru
	} catch {
		Write-Step "  Port proxy repair cancelled or failed to launch. Administrator approval is required." ([ConsoleColor]::Red)
		return
	}

	if ($process.ExitCode -ne 0) {
		Write-Step "  Port forwarding script exited with code $($process.ExitCode)." ([ConsoleColor]::Red)
		return
	}

	Start-Sleep -Seconds 2

	try {
		$retryTest = Test-NetConnection -ComputerName 'localhost' -Port $Port -WarningAction SilentlyContinue
	} catch {
		return
	}

	if ($retryTest.TcpTestSucceeded) {
		Write-Step "  ✓ Windows port proxy refreshed for $ServiceName" ([ConsoleColor]::Green)
	}
}

function New-DetachedScript {
	param([string[]]$Lines)

	$tempFile = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), '.ps1')
	Set-Content -Path $tempFile -Value ($Lines -join [Environment]::NewLine) -Encoding UTF8
	return $tempFile
}

function Launch-DetachedProcess {
	param(
		[Parameter(Mandatory = $true)][string]$Title,
		[Parameter(Mandatory = $true)][string[]]$BodyLines
	)

	$scriptLines = @(
		"Write-Host '$Title' -ForegroundColor Cyan",
		"Write-Host 'Press Ctrl+C to stop this service window.' -ForegroundColor Yellow",
		"Write-Host ''"
	) + $BodyLines

	$scriptPath = New-DetachedScript -Lines $scriptLines
	$process = Start-Process pwsh -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath -PassThru
	return $process
}

function Ensure-NpmDependencies {
	param(
		[Parameter(Mandatory = $true)][string]$Folder,
		[Parameter(Mandatory = $true)][string]$Description
	)

	$nodeModulesPath = Join-Path $Folder 'node_modules'
	if (Test-Path $nodeModulesPath) {
		Write-Step "  ✓ npm dependencies ready for $Description" ([ConsoleColor]::Green)
		return
	}

	if ($SkipDependencyInstall) {
		Write-Step "  Skipping npm install for $Description (SkipDependencyInstall set)." ([ConsoleColor]::DarkYellow)
		return
	}

	Write-Step "  Installing npm dependencies for $Description..." ([ConsoleColor]::Yellow)
	Push-Location $Folder
	npm install | Out-Host
	if ($LASTEXITCODE -ne 0) {
		Pop-Location
		throw "npm install failed for $Description."
	}
	Pop-Location
}

function Ensure-PlaywrightDependencies {
	$playwrightFolder = Join-Path (Get-Location) 'tests\playwright'
	if (-not (Test-Path $playwrightFolder)) {
		throw "Playwright workspace not found at tests\playwright."
	}

	Ensure-NpmDependencies -Folder $playwrightFolder -Description 'Playwright E2E tests'
}

function Run-PlaywrightSmokeSuite {
	Write-Step "Running Playwright smoke tests..." ([ConsoleColor]::Yellow)

	Ensure-PlaywrightDependencies

	$playwrightFolder = Join-Path (Get-Location) 'tests\playwright'
	Push-Location $playwrightFolder

	$originalBaseUrl = $env:PLAYWRIGHT_BASE_URL
	$env:PLAYWRIGHT_BASE_URL = 'http://localhost:3000'

	npm test | Out-Host
	$exitCode = $LASTEXITCODE

	if ($null -ne $originalBaseUrl) {
		$env:PLAYWRIGHT_BASE_URL = $originalBaseUrl
	} else {
		Remove-Item Env:PLAYWRIGHT_BASE_URL -ErrorAction SilentlyContinue
	}

	Pop-Location

	if ($exitCode -ne 0) {
		throw "Playwright smoke tests failed."
	}

	Write-Step "  ✓ Playwright smoke suite passed" ([ConsoleColor]::Green)
}

trap {
	Write-Step "Startup orchestration failed: $($_.Exception.Message)" ([ConsoleColor]::Red)
	exit 1
}

Write-Banner "RCA Insight Engine - Unified Startup"

Ensure-Command -Command 'wsl.exe' -InstallHint 'Install Windows Subsystem for Linux and restart your shell.'
Ensure-Command -Command 'npm' -InstallHint 'Install Node.js 18+ from https://nodejs.org/.'

if (-not (Test-Path 'venv\Scripts\activate.ps1')) {
	throw "Virtual environment not found. Run .\setup-dev-environment.ps1 first."
}

if (-not (Test-Path '.env')) {
	throw ".env file missing. Run .\setup-dev-environment.ps1 to generate it."
}

Write-Step "Validating Docker daemon inside WSL..." ([ConsoleColor]::Yellow)
$dockerCheck = Invoke-WslRepoCommand "docker ps >/dev/null 2>&1"
if ($dockerCheck.ExitCode -ne 0) {
	throw "Unable to reach Docker daemon inside WSL. Start Docker Desktop or enable the WSL Docker service."
}
Write-Step "  ✓ Docker daemon reachable" ([ConsoleColor]::Green)

Write-Step "Resolving port conflicts..." ([ConsoleColor]::Yellow)
Ensure-Port-Free -Port 8000 -ServiceName 'Backend API'
Ensure-Port-Free -Port 3000 -ServiceName 'Frontend UI'
Ensure-Port-Free -Port 15432 -ServiceName 'Postgres (dev)'

Write-Step "Stopping existing containers..." ([ConsoleColor]::Yellow)
Invoke-WslRepoCommand "docker compose -f docker-compose.dev.yml down --remove-orphans >/dev/null 2>&1" | Out-Null
Invoke-WslRepoCommand "docker compose -f deploy/docker/docker-compose.yml down --remove-orphans >/dev/null 2>&1" | Out-Null
Invoke-WslRepoCommand "docker rm -f rca_db rca_redis rca_ollama >/dev/null 2>&1" | Out-Null

if ($ResetData) {
	Write-Step "Removing persistent volumes (ResetData switch provided)..." ([ConsoleColor]::Yellow)
	Invoke-WslRepoCommand "docker volume rm rca-final_postgres_data >/dev/null 2>&1" | Out-Null
	Invoke-WslRepoCommand "docker volume rm rca-final_redis_data >/dev/null 2>&1" | Out-Null
}

$pgUser = Get-DotEnvValue -Key 'POSTGRES_USER' -Default 'rca_user'
$pgPassword = Get-DotEnvValue -Key 'POSTGRES_PASSWORD' -Default 'rca_password_change_in_production'
$pgDatabase = Get-DotEnvValue -Key 'POSTGRES_DB' -Default 'rca_engine'
$pgHost = Get-DotEnvValue -Key 'POSTGRES_HOST' -Default '127.0.0.1'
$pgPort = Get-DotEnvValue -Key 'POSTGRES_PORT' -Default '15432'

Write-Step "Starting database containers..." ([ConsoleColor]::Yellow)
$composeCommand = "POSTGRES_USER='$pgUser' POSTGRES_PASSWORD='$pgPassword' POSTGRES_DB='$pgDatabase' docker compose -f docker-compose.dev.yml up -d db redis"
$composeResult = Invoke-WslRepoCommand $composeCommand
if ($composeResult.ExitCode -ne 0) {
	throw "Failed to start docker-compose services."
}
Write-Step "  ✓ Containers starting" ([ConsoleColor]::Green)

Write-Step "Waiting for Postgres health check..." ([ConsoleColor]::Yellow)
if (-not (Wait-For-ContainerHealthy -ContainerName 'rca_db')) {
	throw "Postgres container failed to report healthy status.";
}
Write-Step "  ✓ Postgres healthy" ([ConsoleColor]::Green)

Write-Step "Verifying Postgres TCP endpoint..." ([ConsoleColor]::Yellow)
if (-not (Wait-For-TcpPort -TargetHost $pgHost -TargetPort $pgPort -TimeoutSeconds 90)) {
	if ($pgHost -in @('localhost', '127.0.0.1')) {
		Ensure-WindowsPortProxy -Port $pgPort -ServiceName 'Postgres (dev)'
		if (-not (Wait-For-TcpPort -TargetHost $pgHost -TargetPort $pgPort -TimeoutSeconds 45)) {
			throw "Postgres TCP endpoint $($pgHost):$pgPort not reachable within timeout after attempting port proxy repair."
		}
	} else {
		throw "Postgres TCP endpoint $($pgHost):$pgPort not reachable within timeout."
	}
}
Write-Step "  ✓ Postgres accepting connections" ([ConsoleColor]::Green)

$pythonPath = Resolve-Path 'venv\Scripts\python.exe'

Write-Step "Applying database migrations..." ([ConsoleColor]::Yellow)

$originalPgUser = $env:POSTGRES_USER
$originalPgPassword = $env:POSTGRES_PASSWORD
$originalPgDb = $env:POSTGRES_DB
$originalPgHost = $env:POSTGRES_HOST
$originalPgPort = $env:POSTGRES_PORT

$env:POSTGRES_USER = $pgUser
$env:POSTGRES_PASSWORD = $pgPassword
$env:POSTGRES_DB = $pgDatabase
$env:POSTGRES_HOST = $pgHost
$env:POSTGRES_PORT = $pgPort

$maxMigrationAttempts = 3
$migrationExit = -1

for ($attempt = 1; $attempt -le $maxMigrationAttempts; $attempt++) {
	if ($attempt -gt 1) {
		Write-Step "  Alembic upgrade attempt $attempt of $maxMigrationAttempts after failure (exit code $migrationExit). Retrying in 5 seconds..." ([ConsoleColor]::DarkYellow)
		Start-Sleep -Seconds 5
	}

	& $pythonPath -m alembic upgrade head
	$migrationExit = $LASTEXITCODE

	if ($migrationExit -eq 0) {
		break
	}
}

if ($null -ne $originalPgUser) { $env:POSTGRES_USER = $originalPgUser } else { Remove-Item Env:POSTGRES_USER -ErrorAction SilentlyContinue }
if ($null -ne $originalPgPassword) { $env:POSTGRES_PASSWORD = $originalPgPassword } else { Remove-Item Env:POSTGRES_PASSWORD -ErrorAction SilentlyContinue }
if ($null -ne $originalPgDb) { $env:POSTGRES_DB = $originalPgDb } else { Remove-Item Env:POSTGRES_DB -ErrorAction SilentlyContinue }
if ($null -ne $originalPgHost) { $env:POSTGRES_HOST = $originalPgHost } else { Remove-Item Env:POSTGRES_HOST -ErrorAction SilentlyContinue }
if ($null -ne $originalPgPort) { $env:POSTGRES_PORT = $originalPgPort } else { Remove-Item Env:POSTGRES_PORT -ErrorAction SilentlyContinue }

if ($migrationExit -ne 0) {
	throw "Alembic migrations failed. Review the terminal output above."
}
Write-Step "  ✓ Alembic migrations applied" ([ConsoleColor]::Green)

Ensure-NpmDependencies -Folder (Join-Path (Get-Location) 'ui') -Description 'Next.js UI'

$repoPath = (Get-Location).Path

Write-Step "Launching Backend API (new console)..." ([ConsoleColor]::Yellow)
$backendProcess = Launch-DetachedProcess -Title 'RCA Engine - Backend API' -BodyLines @(
	"Set-Location '$repoPath'",
	"& '.\\venv\\Scripts\\activate.ps1'",
	"python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload"
)

Start-Sleep -Seconds 3
Wait-For-HttpEndpoint -Url 'http://localhost:8000/api/health/live' -Description 'Backend API'

Write-Step "Launching Frontend UI (new console)..." ([ConsoleColor]::Yellow)
$uiPath = Join-Path $repoPath 'ui'
$uiProcess = Launch-DetachedProcess -Title 'RCA Engine - Frontend UI' -BodyLines @(
	"Set-Location '$uiPath'",
	"npm run dev"
)

Start-Sleep -Seconds 3
Wait-For-HttpEndpoint -Url 'http://localhost:3000' -Description 'Frontend UI'

if ($IncludeWorker) {
	Write-Step "Launching background worker (new console)..." ([ConsoleColor]::Yellow)
	$workerProcess = Launch-DetachedProcess -Title 'RCA Engine - Worker' -BodyLines @(
		"Set-Location '$repoPath'",
		"& '.\\venv\\Scripts\\activate.ps1'",
		"python -m apps.worker.main"
	)
	Write-Step "  ✓ Worker window opened" ([ConsoleColor]::Green)
}

if ($RunPlaywrightSmoke) {
	Run-PlaywrightSmokeSuite
}

Write-Banner "Environment Ready"
Write-Step "Backend API:     http://localhost:8000" ([ConsoleColor]::Green)
Write-Step "API Docs:        http://localhost:8000/api/docs" ([ConsoleColor]::Green)
Write-Step "Frontend UI:     http://localhost:3000" ([ConsoleColor]::Green)
if ($IncludeWorker) {
	Write-Step "Worker Status: running in dedicated console" ([ConsoleColor]::Green)
}

if ($RunPlaywrightSmoke) {
	Write-Step "Playwright report: tests/playwright/playwright-report" ([ConsoleColor]::Green)
}

Write-Step "Use Ctrl+C in the spawned PowerShell windows to stop individual services." ([ConsoleColor]::Yellow)
Write-Step "Run 'docker compose -f docker-compose.dev.yml down' inside WSL to stop the containers." ([ConsoleColor]::Yellow)

exit 0

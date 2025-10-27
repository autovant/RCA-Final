param(
    [switch]$IncludeWorker,
    [switch]$NoBrowser,
    [switch]$NoWorker
)

$backendPort = 8000
$copilotPort = 5001
$script:copilotProxyStarted = $false
$script:copilotProxyMessage = ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RCA Engine - Dev Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

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
        $netstatLine = netstat -ano | Select-String -Pattern "LISTENING.*[:\.]$Port\s" | Select-Object -First 1
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

function Stop-PortListener {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Description
    )

    $listener = Get-PortListener -Port $Port
    if ($listener) {
        $owner = if ($listener.ProcessName) { "$($listener.ProcessName) (PID $($listener.ProcessId))" } else { "PID $($listener.ProcessId)" }
        Write-Host "⚠ $Description port $Port is occupied by $owner - force closing..." -ForegroundColor Yellow
        
        try {
            Stop-Process -Id $listener.ProcessId -Force -ErrorAction Stop
            Start-Sleep -Milliseconds 500
            
            # Verify the port is now free
            $stillListening = Get-PortListener -Port $Port
            if ($stillListening) {
                Write-Host "  WARNING: Process may still be terminating, waiting..." -ForegroundColor Yellow
                Start-Sleep -Seconds 2
            } else {
                Write-Host "  ✓ Port $Port freed successfully" -ForegroundColor Green
            }
        } catch {
            Write-Host "  ERROR: Failed to terminate process $($listener.ProcessId): $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "  You may need to manually close the process or run as Administrator." -ForegroundColor Yellow
            exit 1
        }
    }
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
        Write-Host "Stop the conflicting process or update your configuration, then rerun the script." -ForegroundColor Yellow
        exit 1
    }
}

if (-not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: .\\setup-dev-environment.ps1" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file missing!" -ForegroundColor Red
    Write-Host "Please run: .\\setup-dev-environment.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Preparing backend services..." -ForegroundColor Yellow
& .\start-dev.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to initialize backend dependencies" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Force close any processes on required ports
Write-Host ""
Write-Host "Checking and clearing required ports..." -ForegroundColor Yellow
Stop-PortListener -Port $backendPort -Description "Backend API"
Stop-PortListener -Port 3000 -Description "Frontend UI"
Stop-PortListener -Port $copilotPort -Description "Copilot Proxy"
Write-Host "✓ All required ports are available" -ForegroundColor Green
Write-Host ""

$repoPath = (Get-Location).Path
$startWorker = -not $NoWorker
if ($PSBoundParameters.ContainsKey('IncludeWorker')) {
    $startWorker = $true
}

if (-not $startWorker) {
    Write-Host "NOTE: Worker process disabled. Uploads will remain queued until a worker is running." -ForegroundColor Yellow
}

function New-LaunchScript {
    param([string]$Content)

    $tempFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "rca-" + [System.Guid]::NewGuid().ToString("N") + ".ps1")
    Set-Content -Path $tempFile -Value $Content -Encoding UTF8
    return $tempFile
}

function Get-DotEnvValue {
    param([string]$Key)

    if (-not (Test-Path ".env")) {
        return $null
    }

    $line = Get-Content ".env" | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $value = ($line -split "=", 2)[1].Trim()
    return $value.Trim('"').Trim("'")
}

function Start-CopilotProxy {
    Write-Host "Launching GitHub Copilot proxy..." -ForegroundColor Yellow

    if (-not (Test-Path "copilot-to-api-main\server.py")) {
        Write-Host "WARN: copilot-to-api-main\server.py not found; skipping proxy." -ForegroundColor Yellow
        $script:copilotProxyMessage = "Copilot proxy skipped: missing copilot-to-api-main/server.py"
        return
    }

    $pythonExe = Join-Path (Get-Location) "venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Host "WARN: Python virtual environment missing; proxy not started." -ForegroundColor Yellow
        $script:copilotProxyMessage = "Copilot proxy skipped: missing venv"
        return
    }

    $githubToken = Get-DotEnvValue "GITHUB_TOKEN"
    if (-not $githubToken) {
        Write-Host "WARN: GITHUB_TOKEN missing in .env; proxy will likely fail authentication." -ForegroundColor Yellow
    }

    $envBlock = "`$env:PORT = '$copilotPort'`n"
    if ($githubToken) {
        $envBlock += "`$env:GITHUB_TOKEN = '$githubToken'`n"
    }

    $copilotScript = @"
Write-Host 'RCA Engine - GitHub Copilot Proxy' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
Set-Location '$repoPath'
& '.\venv\Scripts\activate.ps1'
$envBlock
python -m pip install --disable-pip-version-check --quiet -r '.\copilot-to-api-main\requirements.txt' | Out-Null
python '.\copilot-to-api-main\server.py'
"@

    $copilotScriptPath = New-LaunchScript -Content $copilotScript
    $process = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $copilotScriptPath -PassThru

    if ($process) {
        $script:copilotProxyStarted = $true
        $script:copilotProxyMessage = "Copilot proxy: http://localhost:$copilotPort (PID $($process.Id))"
        Write-Host "Copilot proxy starting in a dedicated terminal (PID $($process.Id))." -ForegroundColor Green
    } else {
        $script:copilotProxyMessage = "Copilot proxy launch failed"
        Write-Host "ERROR: failed to launch Copilot proxy." -ForegroundColor Red
    }
}

Write-Host "Launching Backend API..." -ForegroundColor Yellow
$backendScript = @"
Write-Host 'RCA Engine - Backend API' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
Set-Location '$repoPath'
& '.\venv\Scripts\activate.ps1'
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $backendPort --reload
"@
$backendScriptPath = New-LaunchScript -Content $backendScript
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScriptPath
Start-Sleep -Seconds 2

Write-Host "Launching Frontend UI..." -ForegroundColor Yellow
$uiScript = @"
Write-Host 'RCA Engine - Frontend UI' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
Set-Location '$repoPath\ui'
npm run dev
"@
$uiScriptPath = New-LaunchScript -Content $uiScript
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $uiScriptPath
Start-Sleep -Seconds 2

if ($startWorker) {
    Write-Host "Launching Background Worker..." -ForegroundColor Yellow
    $workerScript = @"
Write-Host 'RCA Engine - Worker' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
Set-Location '$repoPath'
& '.\venv\Scripts\activate.ps1'
python -m apps.worker.main
"@
    $workerScriptPath = New-LaunchScript -Content $workerScript
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $workerScriptPath
    Start-Sleep -Seconds 2
}

Start-CopilotProxy

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services Starting" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:$backendPort" -ForegroundColor White
Write-Host "API Docs:   http://localhost:$backendPort/api/docs" -ForegroundColor White
Write-Host "Frontend:   http://localhost:3000" -ForegroundColor White
if ($startWorker) {
    Write-Host "Worker:     running from dedicated terminal" -ForegroundColor White
}
if ($copilotProxyStarted) {
    Write-Host "Copilot:    http://localhost:$copilotPort" -ForegroundColor White
} elseif ($copilotProxyMessage) {
    Write-Host $copilotProxyMessage -ForegroundColor Yellow
}

if (-not $NoBrowser) {
    Write-Host "Opening frontend in default browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:3000" | Out-Null
}

Write-Host ""
Write-Host "✓ Development environment is coming online." -ForegroundColor Green
Write-Host "Check the new PowerShell windows for live logs." -ForegroundColor Gray

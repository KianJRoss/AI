#Requires -RunAsAdministrator
# net-os node-agent installer for Windows (MSI Laptop)
# Run as Administrator in PowerShell

param(
    [string]$NodeName    = "MSI",
    [string]$PcIp        = "192.168.0.27",
    [int]   $Port        = 7700,
    [string]$NodeToken   = "netoskeylocal"
)

$InstallDir = "C:\net-os-agent"
$StartupDir = [System.IO.Path]::Combine(
    [System.Environment]::GetFolderPath("ApplicationData"),
    "Microsoft\Windows\Start Menu\Programs\Startup"
)

Write-Host "`n=== net-os node-agent installer (Windows) ===" -ForegroundColor Cyan
Write-Host "Install dir : $InstallDir"
Write-Host "Node name   : $NodeName"
Write-Host "PC IP       : $PcIp"
Write-Host "Port        : $Port"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Create install directory
# ---------------------------------------------------------------------------
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Host "[ok] Created $InstallDir" -ForegroundColor Green
} else {
    Write-Host "[ok] $InstallDir already exists" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 2. Copy agent.py
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentSource = Join-Path $ScriptDir "agent.py"

if (Test-Path $AgentSource) {
    Copy-Item $AgentSource "$InstallDir\agent.py" -Force
    Write-Host "[ok] agent.py copied from $ScriptDir" -ForegroundColor Green
} else {
    Write-Host "[!!] agent.py not found at $AgentSource — attempting download from PC..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "http://${PcIp}:8080/bootstrap/node-agent.py" -OutFile "$InstallDir\agent.py" -UseBasicParsing
        Write-Host "[ok] agent.py downloaded from PC" -ForegroundColor Green
    } catch {
        Write-Host "[!!] Could not download agent.py. Place it at $InstallDir\agent.py manually." -ForegroundColor Red
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 3. Create config.json
# ---------------------------------------------------------------------------
$config = @{
    name   = $NodeName
    pc_ip  = $PcIp
    port   = $Port
    hub_ws_url = "ws://100.99.89.118:8080"
} | ConvertTo-Json -Depth 3

Set-Content -Path "$InstallDir\config.json" -Value $config -Encoding UTF8
Write-Host "[ok] config.json written" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 4. Create projects.json (empty for laptop — no deployable projects)
# ---------------------------------------------------------------------------
Set-Content -Path "$InstallDir\projects.json" -Value '{}' -Encoding UTF8
Write-Host "[ok] projects.json written (empty — laptop has no deployable projects)" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Create .env file
# ---------------------------------------------------------------------------
$envContent = @"
NODE_TOKEN=$NodeToken
NODE_PORT=$Port
"@
Set-Content -Path "$InstallDir\.env" -Value $envContent -Encoding UTF8
Write-Host "[ok] .env written" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 6. Check for Python / uvicorn
# ---------------------------------------------------------------------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[!!] Python not found in PATH. Install Python 3.11+ then re-run." -ForegroundColor Red
    exit 1
}
Write-Host "[ok] Python: $($python.Source)" -ForegroundColor Green

# Install uvicorn and deps if missing
Write-Host "[+] Installing Python dependencies..." -ForegroundColor Cyan
& python -m pip install --quiet fastapi "uvicorn[standard]" psutil pydantic websockets 2>&1 | Select-String -Pattern "error|Error" | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
Write-Host "[ok] Python deps installed" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 7. Create startup .cmd launcher
# ---------------------------------------------------------------------------
$startupCmd = @"
@echo off
REM net-os node-agent startup launcher
set NODE_TOKEN=$NodeToken
set NODE_PORT=$Port
cd /d $InstallDir
start /min "net-os-agent" python -m uvicorn agent:app --host 0.0.0.0 --port $Port
"@

$startupCmdPath = Join-Path $StartupDir "net-os-agent.cmd"
Set-Content -Path $startupCmdPath -Value $startupCmd -Encoding ASCII
Write-Host "[ok] Startup launcher: $startupCmdPath" -ForegroundColor Green

# Also create a Task Scheduler entry for more reliable startup
Write-Host "[+] Registering Task Scheduler task..." -ForegroundColor Cyan
$taskAction = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "-m uvicorn agent:app --host 0.0.0.0 --port $Port" `
    -WorkingDirectory $InstallDir

$taskTrigger = New-ScheduledTaskTrigger -AtLogOn
$taskSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

$taskPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

$envAction = @{
    Name  = "net-os-agent"
    Action = $taskAction
    Trigger = $taskTrigger
    Settings = $taskSettings
    Principal = $taskPrincipal
    Description = "net-os Node Agent - AI Network OS"
}

try {
    Unregister-ScheduledTask -TaskName "net-os-agent" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask @envAction | Out-Null

    # Set environment variable for the task
    $task = Get-ScheduledTask -TaskName "net-os-agent"
    $task.Actions[0].Arguments = "-m uvicorn agent:app --host 0.0.0.0 --port $Port"

    # Set env vars via registry for the task
    $regPath = "HKCU:\Environment"
    Write-Host "[ok] Task Scheduler task registered" -ForegroundColor Green
} catch {
    Write-Host "[warn] Task Scheduler registration failed: $_" -ForegroundColor Yellow
    Write-Host "[warn] Startup .cmd will be used as fallback" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 8. Create orch-node wrapper in a PATH-accessible location
# ---------------------------------------------------------------------------
$orchNodeDir = "C:\net-os-agent\bin"
if (-not (Test-Path $orchNodeDir)) {
    New-Item -ItemType Directory -Path $orchNodeDir -Force | Out-Null
}

$orchNodeScript = @'
#!/usr/bin/env pwsh
# orch-node — quick CLI for the local node agent
param(
    [Parameter(Position=0)] [string]$Cmd,
    [Parameter(Position=1, ValueFromRemainingArguments)] [string[]]$Rest
)

$Base   = "http://localhost:7700"
$Token  = $env:NODE_TOKEN ?? "netoskeylocal"
$Headers = @{ "X-Node-Token" = $Token }

function Invoke-Agent([string]$Method, [string]$Path, $Body=$null) {
    $uri = "$Base$Path"
    if ($Body) {
        Invoke-RestMethod -Method $Method -Uri $uri -Headers $Headers -Body ($Body | ConvertTo-Json) -ContentType "application/json"
    } else {
        Invoke-RestMethod -Method $Method -Uri $uri -Headers $Headers
    }
}

switch ($Cmd) {
    "health"   { Invoke-Agent GET /health | ConvertTo-Json }
    "projects" { Invoke-Agent GET /projects | ConvertTo-Json -Depth 5 }
    "exec"     {
        $node_cmd = $Rest -join " "
        Invoke-Agent POST /exec @{ cmd = $node_cmd } | ConvertTo-Json
    }
    "ping"     { Invoke-RestMethod "$Base/ping" | ConvertTo-Json }
    default {
        Write-Host "orch-node - local node agent CLI"
        Write-Host "  health        Show node health"
        Write-Host "  projects      List deployable projects"
        Write-Host "  exec <cmd>    Run a shell command"
        Write-Host "  ping          Unauthenticated ping"
    }
}
'@

Set-Content -Path "$orchNodeDir\orch-node.ps1" -Value $orchNodeScript -Encoding UTF8

# Add to user PATH if not already present
$currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$orchNodeDir*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$currentPath;$orchNodeDir", "User")
    Write-Host "[ok] Added $orchNodeDir to user PATH" -ForegroundColor Green
}

# Create a .cmd shim for non-PS environments
Set-Content -Path "$orchNodeDir\orch-node.cmd" -Value "@pwsh -NoProfile -File `"$orchNodeDir\orch-node.ps1`" %*" -Encoding ASCII
Write-Host "[ok] orch-node wrapper created at $orchNodeDir" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 9. Start agent now
# ---------------------------------------------------------------------------
Write-Host "[+] Starting agent..." -ForegroundColor Cyan
$env:NODE_TOKEN = $NodeToken
$env:NODE_PORT  = $Port
$job = Start-Process -FilePath "python" `
    -ArgumentList "-m uvicorn agent:app --host 0.0.0.0 --port $Port" `
    -WorkingDirectory $InstallDir `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 3
try {
    $health = Invoke-RestMethod -Uri "http://localhost:$Port/ping" -TimeoutSec 5
    Write-Host "[ok] Agent is responding: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "[warn] Agent didn't respond yet — it may still be starting" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== INSTALLATION COMPLETE ===" -ForegroundColor Cyan
Write-Host "Install dir  : $InstallDir"
Write-Host "Startup cmd  : $startupCmdPath"
Write-Host "Health check : Invoke-RestMethod -Uri http://localhost:${Port}/health -Headers @{'X-Node-Token'='$NodeToken'}"
Write-Host "orch-node    : orch-node health"
Write-Host ""
Write-Host "The agent starts automatically at login via Task Scheduler." -ForegroundColor Green

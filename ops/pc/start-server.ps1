# Starts the PC server (API + web) in the background from an env file.
#   powershell -ExecutionPolicy Bypass -File ops\pc\start-server.ps1
#   powershell -ExecutionPolicy Bypass -File ops\pc\start-server.ps1 -EnvFile <path> -SkipBuild
param(
    [string]$EnvFile = "",
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $EnvFile) { $EnvFile = Join-Path $Root "server\.env" }
if (-not (Test-Path $EnvFile)) { throw "Missing env file: $EnvFile (copy server\.env.example and fill it in)." }

Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $name, $value = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
    }
}

foreach ($required in "SESSION_SECRET", "PUBLIC_HOST", "DEFAULT_OWNER_USERNAME", "DEFAULT_OWNER_PASSWORD", "DEFAULT_OWNER_TOTP_SECRET") {
    if (-not [Environment]::GetEnvironmentVariable($required, "Process")) { throw "$required is empty in $EnvFile" }
}
if ($env:PUBLIC_MODE -eq "true" -and -not $env:SMTP_PASSWORD) { throw "SMTP_PASSWORD is empty in $EnvFile (Gmail App Password)." }

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing virtualenv: $Python" }
$RunDir = Join-Path $Root "runtime\pc"
New-Item -ItemType Directory -Force $RunDir | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Root "server\data") | Out-Null

& (Join-Path $PSScriptRoot "stop-server.ps1")

$env:VITE_PUBLIC_HOST = $env:PUBLIC_HOST
if (-not $env:PORT) { $env:PORT = "8765" }
if (-not $env:FRONTEND_PORT) { $env:FRONTEND_PORT = "5173" }
Set-Location $Root

if (-not $SkipBuild) {
    # The build must not see server secrets.
    $saved = @{}
    foreach ($secret in "SESSION_SECRET", "SMTP_PASSWORD", "DEFAULT_OWNER_PASSWORD", "DEFAULT_OWNER_TOTP_SECRET") {
        $saved[$secret] = [Environment]::GetEnvironmentVariable($secret, "Process")
        [Environment]::SetEnvironmentVariable($secret, $null, "Process")
    }
    try {
        & npm --prefix frontend run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
    } finally {
        foreach ($secret in $saved.Keys) { [Environment]::SetEnvironmentVariable($secret, $saved[$secret], "Process") }
    }
}

& $Python -m alembic -c server\alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
& $Python -m server.cli seed-default-owner
if ($LASTEXITCODE -ne 0) { throw "Default owner seed failed." }

$api = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "server.app.main:app", "--host", "127.0.0.1", "--port", $env:PORT -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RunDir "api.out.log") -RedirectStandardError (Join-Path $RunDir "api.err.log")
Set-Content -Path (Join-Path $RunDir "api.pid") -Value $api.Id -Encoding ascii
$web = Start-Process -FilePath "node" -ArgumentList "ops\pc\static-server.mjs" -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RunDir "web.out.log") -RedirectStandardError (Join-Path $RunDir "web.err.log")
Set-Content -Path (Join-Path $RunDir "web.pid") -Value $web.Id -Encoding ascii

$healthy = $false
foreach ($attempt in 1..40) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$($env:FRONTEND_PORT)/api/v1/health" -TimeoutSec 3
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) { throw "Server did not become healthy; see $RunDir\*.log" }
Write-Output "PC server is up: http://127.0.0.1:$($env:FRONTEND_PORT)  (public: https://$($env:PUBLIC_HOST))"
Write-Output "Logs: $RunDir"

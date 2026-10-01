# Stops the API and web processes started by start-server.ps1.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RunDir = Join-Path $Root "runtime\pc"
foreach ($name in "api", "web") {
    $pidFile = Join-Path $RunDir "$name.pid"
    if (-not (Test-Path $pidFile)) { continue }
    $processId = [int](Get-Content $pidFile | Select-Object -First 1)
    # Only stop the process if it is still the one this project started.
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -and ($process.CommandLine -match "server\.app\.main:app|static-server\.mjs")) {
        Stop-Process -Id $processId -Force -Confirm:$false
        Write-Output "Stopped $name (pid $processId)"
    }
    Remove-Item $pidFile -Force -Confirm:$false
}

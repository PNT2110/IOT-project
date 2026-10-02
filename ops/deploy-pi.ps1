# Deploys the Pi part of the project. Run from the project folder on the PC:
#   powershell -ExecutionPolicy Bypass -File ops\deploy-pi.ps1
# Needs SSH key access to the Pi (no passwords are typed or stored here) and
# a filled-in ops\pi5\pi.env. Add -Flash to upload the firmware to the ESP32
# (remove the propellers first); by default the firmware is only built.
param(
    [string]$PiHost = "100.123.225.88",
    [string]$PiUser = "pitan",
    [switch]$Flash,
    [switch]$SkipFirmwareBuild
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $root "ops\pi5\pi.env"
if (-not (Test-Path $envFile)) { throw "Missing ops\pi5\pi.env (copy ops\pi5\pi.env.example and fill it in)." }
foreach ($required in "PI_SMTP_PASSWORD", "PI_DEFAULT_ADMIN_PASSWORD", "PI_DEVICE_ID", "PI_DEVICE_KEY") {
    if (-not (Select-String -Path $envFile -Pattern "^$required=.+" -Quiet)) { throw "$required is empty in ops\pi5\pi.env" }
}
$target = "${PiUser}@${PiHost}"
$ssh = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=15")
& ssh @ssh $target "true"
if ($LASTEXITCODE -ne 0) { throw "SSH key login to $target failed. Install this PC's public key on the Pi first." }

$pkg = Join-Path $env:TEMP "iot-pi.tgz"
Push-Location $root
try { & tar -czf $pkg --exclude=__pycache__ --exclude=pi.env --exclude=pi.env.example edge/pi5 firmware/FC_can_bang contracts ops/pi5/pi-setup.sh ops/pi5/pi-network.sh ops/pi5/pi-wifi-permission.sh }
finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Packaging failed." }

Write-Output "== Copy to $target"
& scp @ssh $pkg "${target}:/tmp/iot-pi.tgz"
if ($LASTEXITCODE -ne 0) { throw "Copy failed." }
& scp @ssh $envFile "${target}:/tmp/iot-pi.env"
if ($LASTEXITCODE -ne 0) { throw "Copy of pi.env failed." }
Remove-Item $pkg -Force -Confirm:$false

$vars = @()
if ($Flash) { $vars += "FLASH=1" }
if ($SkipFirmwareBuild) { $vars += "BUILD_FIRMWARE=0" }
$remote = "mkdir -p ~/iot && rm -rf ~/iot/edge ~/iot/contracts ~/iot/ops && tar -xzf /tmp/iot-pi.tgz -C ~/iot && rm -f /tmp/iot-pi.tgz && install -m 600 /tmp/iot-pi.env ~/iot/pi.env && rm -f /tmp/iot-pi.env && sed -i 's/\r$//' ~/iot/ops/pi5/*.sh && $($vars -join ' ') bash ~/iot/ops/pi5/pi-setup.sh 2>&1 | tee ~/iot/deploy.log"
& ssh @ssh $target $remote
if ($LASTEXITCODE -ne 0) { throw "Pi setup failed; see ~/iot/deploy.log on the Pi." }
Write-Output "Done. Pi web: http://192.168.4.1/ on the Pi Wi-Fi, or http://${PiHost}/ over Tailscale."

#requires -version 5.1

param(
    [string]$InstallDir = "$env:ProgramFiles\NetworkProbe"
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Execute este desinstalador em um PowerShell como Administrador."
    exit 1
}

$targetExe = Join-Path $InstallDir "NetworkProbe.exe"
$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*NetworkProbe.exe*" }
foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Unregister-ScheduledTask -TaskName "NetworkProbe" -Confirm:$false -ErrorAction SilentlyContinue
Get-NetFirewallRule -DisplayName "NetworkProbe *" -ErrorAction SilentlyContinue | Remove-NetFirewallRule

$startMenuDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\Network Probe"
if (Test-Path $startMenuDir) {
    Remove-Item -LiteralPath $startMenuDir -Recurse -Force
}

$resolvedInstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$programFiles = [System.IO.Path]::GetFullPath($env:ProgramFiles)
if ((Test-Path $resolvedInstallDir) -and $resolvedInstallDir.StartsWith($programFiles, [System.StringComparison]::OrdinalIgnoreCase)) {
    Remove-Item -LiteralPath $resolvedInstallDir -Recurse -Force
}

Write-Host "Network Probe removido."

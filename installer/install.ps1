#requires -version 5.1

param(
    [string]$InstallDir = "$env:ProgramFiles\NetworkProbe",
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8081,
    [bool]$StartAtLogon = $true,
    [switch]$PublicFirewall
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Execute este instalador em um PowerShell como Administrador."
    exit 1
}

$sourceExe = Join-Path $PSScriptRoot "NetworkProbe.exe"
if (-not (Test-Path $sourceExe)) {
    $sourceExe = Join-Path $PSScriptRoot "..\dist\NetworkProbe.exe"
}
if (-not (Test-Path $sourceExe)) {
    Write-Host "NetworkProbe.exe nao foi encontrado ao lado do instalador."
    exit 1
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
$targetExe = Join-Path $InstallDir "NetworkProbe.exe"
Copy-Item -LiteralPath $sourceExe -Destination $targetExe -Force

$startMenuDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\Network Probe"
New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null

$urlHost = if ($ListenHost -eq "0.0.0.0") { "127.0.0.1" } else { $ListenHost }
$urlFile = Join-Path $startMenuDir "Open Network Probe.url"
Set-Content -Path $urlFile -Value "[InternetShortcut]`r`nURL=http://${urlHost}:${Port}/" -Encoding ASCII

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $startMenuDir "Start Network Probe.lnk"))
$shortcut.TargetPath = $targetExe
$shortcut.Arguments = "--host $ListenHost --port $Port"
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Save()

$taskName = "NetworkProbe"
if ($StartAtLogon) {
    $action = New-ScheduledTaskAction -Execute $targetExe -Argument "--host $ListenHost --port $Port --quiet"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel LeastPrivilege
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description "Network Probe web application" -Force | Out-Null
}

if ($PublicFirewall) {
    $ruleName = "NetworkProbe $Port"
    Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Program $targetExe | Out-Null
}

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*NetworkProbe.exe*" -and $_.CommandLine -like "*--port $Port*" }
foreach ($process in $existing) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath $targetExe -ArgumentList "--host $ListenHost --port $Port --quiet" -WindowStyle Hidden

Write-Host "Network Probe instalado em: $InstallDir"
Write-Host "URL local: http://${urlHost}:${Port}/"
if ($ListenHost -eq "0.0.0.0") {
    Write-Host "Acesso pela rede: use http://IP_DA_MAQUINA:${Port}/"
}

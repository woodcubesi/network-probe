#requires -version 5.1

param(
    [string]$InstallDir = "$env:ProgramFiles\NetworkProbe",
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8081,
    [string]$PythonPath = "",
    [ValidateSet("auto", "demand")]
    [string]$Startup = "auto",
    [switch]$PublicFirewall,
    [bool]$StartNow = $true
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-Python {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        if (Test-Path $RequestedPath) {
            return (Resolve-Path $RequestedPath).Path
        }
        throw "PythonPath informado nao existe: $RequestedPath"
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $resolved = & $py.Source -3 -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -eq 0 -and $resolved) {
            return $resolved.Trim()
        }
    }

    throw "Python 3 nao encontrado. Instale Python 3 ou rode com -PythonPath C:\caminho\python.exe."
}

if (-not (Test-IsAdmin)) {
    Write-Host "Execute este instalador em um PowerShell como Administrador."
    exit 1
}

function Remove-ExistingService {
    $existing = Get-Service -Name "NetworkProbe" -ErrorAction SilentlyContinue
    if (-not $existing) {
        return
    }

    if ($existing.Status -ne "Stopped") {
        Stop-Service -Name "NetworkProbe" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    sc.exe delete NetworkProbe | Out-Null
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        if (-not (Get-Service -Name "NetworkProbe" -ErrorAction SilentlyContinue)) {
            return
        }
    }
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$sourceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Copy-Item -LiteralPath (Join-Path $sourceRoot "README.md") -Destination (Join-Path $InstallDir "README.md") -Force -ErrorAction SilentlyContinue

$sourceExe = Join-Path $PSScriptRoot "NetworkProbeService.exe"
if (-not (Test-Path $sourceExe)) {
    $sourceExe = Join-Path $sourceRoot "NetworkProbeService.exe"
}
if (-not (Test-Path $sourceExe)) {
    $sourceExe = Join-Path $sourceRoot "dist\NetworkProbeService.exe"
}

Push-Location $InstallDir
try {
    Remove-ExistingService
    if (Test-Path $sourceExe) {
        Copy-Item -LiteralPath $sourceExe -Destination (Join-Path $InstallDir "NetworkProbeService.exe") -Force
        & ".\NetworkProbeService.exe" install --startup $Startup --host $ListenHost --port $Port
        if ($StartNow) {
            & ".\NetworkProbeService.exe" start
        }
    } else {
        $pythonExe = Resolve-Python -RequestedPath $PythonPath
        Copy-Item -LiteralPath (Join-Path $sourceRoot "app.py") -Destination (Join-Path $InstallDir "app.py") -Force
        Copy-Item -LiteralPath (Join-Path $sourceRoot "service.py") -Destination (Join-Path $InstallDir "service.py") -Force
        & $pythonExe ".\service.py" install --startup $Startup --host $ListenHost --port $Port --python $pythonExe
        if ($StartNow) {
            & $pythonExe ".\service.py" start
        }
    }
} finally {
    Pop-Location
}

if ($PublicFirewall) {
    $ruleName = "NetworkProbe $Port"
    Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
}

$urlHost = if ($ListenHost -eq "0.0.0.0") { "127.0.0.1" } else { $ListenHost }
$startMenuDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\Network Probe"
New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
Set-Content -Path (Join-Path $startMenuDir "Open Network Probe.url") -Value "[InternetShortcut]`r`nURL=http://${urlHost}:${Port}/" -Encoding ASCII

Write-Host "Network Probe instalado como servico do Windows."
Write-Host "Servico: NetworkProbe"
Write-Host "URL local: http://${urlHost}:${Port}/"
if ($ListenHost -eq "0.0.0.0") {
    Write-Host "Acesso pela rede: http://IP_DA_MAQUINA:${Port}/"
}

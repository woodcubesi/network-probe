#requires -version 5.1

param(
    [string]$InstallDir = "$env:ProgramFiles\NetworkProbe",
    [string]$PythonPath = ""
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

    return $null
}

if (-not (Test-IsAdmin)) {
    Write-Host "Execute este desinstalador em um PowerShell como Administrador."
    exit 1
}

$serviceScript = Join-Path $InstallDir "service.py"
$serviceExe = Join-Path $InstallDir "NetworkProbeService.exe"
$pythonExe = Resolve-Python -RequestedPath $PythonPath
if (Test-Path $serviceExe) {
    Push-Location $InstallDir
    try {
        & ".\NetworkProbeService.exe" uninstall
    } finally {
        Pop-Location
    }
} elseif ($pythonExe -and (Test-Path $serviceScript)) {
    Push-Location $InstallDir
    try {
        & $pythonExe ".\service.py" uninstall
    } finally {
        Pop-Location
    }
} else {
    sc.exe stop NetworkProbe | Out-Null
    sc.exe delete NetworkProbe | Out-Null
}

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

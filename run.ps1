$ErrorActionPreference = "Stop"

$localPython = "C:\Users\JOSUE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pythonCmd = $null

if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} elseif (Test-Path $localPython) {
    $pythonCmd = $localPython
} else {
    Write-Host "Python nao foi encontrado. Instale Python 3 ou adicione python.exe ao PATH."
    exit 1
}

& $pythonCmd "$PSScriptRoot\app.py" @args

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$Port,

    [int]$BaudRate = 1500000,

    [string]$FirmwarePath = ""
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ktoolPath = Join-Path $scriptRoot "ktool.py"

if (-not $FirmwarePath) {
    $FirmwarePath = Join-Path $scriptRoot "kboot.kfpkg"
}

if (-not (Test-Path $ktoolPath)) {
    Write-Error "ktool.py was not found next to this script."
}

if (-not (Test-Path $FirmwarePath)) {
    Write-Error "Firmware file not found: $FirmwarePath"
}

$pythonExe = $null
$pythonPrefix = @()

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $pythonExe = $pyLauncher.Source
    $pythonPrefix = @("-3")
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $pythonExe = $python.Source
    }
}

if (-not $pythonExe) {
    Write-Error "Python 3 was not found. Install Python 3 and rerun this script."
}

& $pythonExe @($pythonPrefix + @("-c", "import serial"))
if ($LASTEXITCODE -ne 0) {
    Write-Host "PySerial is missing. Install it with:"
    if ($pythonPrefix.Count -gt 0) {
        Write-Host "  py -3 -m pip install -r requirements-flash.txt"
    } else {
        Write-Host "  python -m pip install -r requirements-flash.txt"
    }
    exit $LASTEXITCODE
}

$arguments = $pythonPrefix + @(
    $ktoolPath,
    "-B",
    "goE",
    "-b",
    "$BaudRate",
    "-p",
    $Port,
    $FirmwarePath
)

Write-Host "Flashing $FirmwarePath to $Port at $BaudRate baud..."
& $pythonExe @arguments
exit $LASTEXITCODE

<# 
Windows build script (PyInstaller).

Examples:
  powershell -ExecutionPolicy Bypass -File .\build.ps1
  powershell -ExecutionPolicy Bypass -File .\build.ps1 -Targets AutoStarter
  powershell -ExecutionPolicy Bypass -File .\build.ps1 -Clean

Notes:
  - Windows PowerShell 5.1+ recommended
  - Python 3.x required
  - Creates/reuses .venv in repo root (unless -NoVenv)
#>

#Requires -Version 5.1

[CmdletBinding()]
param(
  [ValidateSet('AutoStarter', 'Config')]
  [string[]]$Targets = @('AutoStarter', 'Config'),
  [switch]$Clean,
  [string]$Version,
  [switch]$NoVenv,
  [string]$Python = 'python'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Windows {
  $isWin = $false
  try { $isWin = $IsWindows } catch { $isWin = ($env:OS -eq "Windows_NT") }
  if (-not $isWin) {
    throw "This script is for Windows only."
  }
}

function Get-RepoRoot {
  if ($PSScriptRoot) { return $PSScriptRoot }
  return (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

function Resolve-BuildVersion([string]$repoRoot, [string]$ver) {
  if ($ver -and $ver.Trim().Length -gt 0) { return $ver.Trim() }
  try {
    $gitVer = (& git -C $repoRoot describe --tags --always 2>$null)
    if ($LASTEXITCODE -eq 0 -and $gitVer) { return $gitVer.Trim() }
  } catch { }
  return (Get-Date -Format 'yyyyMMdd-HHmm')
}

function Ensure-VenvPython([string]$repoRoot, [string]$pythonCmd) {
  $venvDir = Join-Path $repoRoot ".venv"
  $venvPy  = Join-Path $venvDir "Scripts\python.exe"

  if (-not (Test-Path $venvPy)) {
    Write-Host "[1/5] Creating venv (.venv) ..."
    & $pythonCmd -m venv $venvDir
  } else {
    Write-Host "[1/5] Reusing venv (.venv) ..."
  }

  return $venvPy
}

function Install-Dependencies([string]$pythonExe, [string]$repoRoot) {
  Write-Host "[2/5] Installing dependencies ..."
  & $pythonExe -m pip install -U pip

  $req = Join-Path $repoRoot "requirements.txt"
  if (Test-Path $req) {
    & $pythonExe -m pip install -r $req
  } else {
    Write-Warning "requirements.txt not found; skip."
  }

  # Extra deps for packaging / GUI
  & $pythonExe -m pip install -U pyinstaller customtkinter
}

function Clean-Outputs([string]$repoRoot) {
  foreach ($p in @('build', 'dist')) {
    $full = Join-Path $repoRoot $p
    if (Test-Path $full) {
      Write-Host "Cleaning: $p"
      Remove-Item -Recurse -Force $full
    }
  }
}

function Run-PyInstaller([string]$pythonExe, [string]$repoRoot, [string]$specFile) {
  $specPath = Join-Path $repoRoot $specFile
  if (-not (Test-Path $specPath)) {
    throw "Spec file not found: $specPath"
  }
  Write-Host "[3/5] Running PyInstaller: $specFile"
  Push-Location $repoRoot
  try {
    & $pythonExe -m PyInstaller $specFile
  } finally {
    Pop-Location
  }
}

function Print-Done([string]$repoRoot) {
  Write-Host "[5/5] Done"
  Write-Host "dist/: $(Join-Path $repoRoot 'dist')"
}

# --------------------------- main ---------------------------

Assert-Windows
$repoRoot = Get-RepoRoot

if ($Clean) { Clean-Outputs -repoRoot $repoRoot }

$versionResolved = Resolve-BuildVersion -repoRoot $repoRoot -ver $Version

$pythonExe = $Python
if (-not $NoVenv) {
  $pythonExe = Ensure-VenvPython -repoRoot $repoRoot -pythonCmd $Python
}

Install-Dependencies -pythonExe $pythonExe -repoRoot $repoRoot

if ($Targets -contains 'AutoStarter') {
  Run-PyInstaller -pythonExe $pythonExe -repoRoot $repoRoot -specFile "AutoStarter.spec"
}
if ($Targets -contains 'Config') {
  Run-PyInstaller -pythonExe $pythonExe -repoRoot $repoRoot -specFile "AutoStarterConfig.spec"
}

Print-Done -repoRoot $repoRoot

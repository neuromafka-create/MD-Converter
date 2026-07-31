<#
.SYNOPSIS
  Build MD-Converter.exe (PyInstaller) and Windows installer (Inno Setup).

.DESCRIPTION
  1. Installs runtime deps if needed
  2. Builds onefile EXE via build.spec
  3. Compiles installer\MD-Converter.iss with ISCC
  4. Prints path to Setup EXE

.EXAMPLE
  .\scripts\build_installer.ps1
  .\scripts\build_installer.ps1 -SkipPyInstaller   # only recompile installer
#>
[CmdletBinding()]
param(
    [switch]$SkipPyInstaller,
    [switch]$SkipInstaller,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-Python {
    if ($Python -and (Test-Path $Python)) { return $Python }
    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python not found. Create .venv or pass -Python path."
}

function Find-ISCC {
    $candidates = @(
        "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$py = Find-Python
Write-Host "Python: $py"
Write-Host "Root:   $Root"

# --- Dependencies ---
Write-Step "Checking dependencies"
& $py -m pip install -q -r (Join-Path $Root "requirements.txt")
& $py -m pip install -q pyinstaller

# --- PyInstaller ---
$exePath = Join-Path $Root "dist\MD-Converter.exe"
if (-not $SkipPyInstaller) {
    Write-Step "Building EXE with PyInstaller"
    $dist = Join-Path $Root "dist"
    $build = Join-Path $Root "build"
    if (Test-Path $dist) {
        # Keep installer folder if present
        Get-ChildItem $dist -File | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem $dist -Directory | Where-Object { $_.Name -ne "installer" } |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $build) { Remove-Item $build -Recurse -Force -ErrorAction SilentlyContinue }

    & $py -m PyInstaller --noconfirm --clean (Join-Path $Root "build.spec")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
    if (-not (Test-Path $exePath)) { throw "Expected EXE not found: $exePath" }

    $sizeMb = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    Write-Host "EXE ready: $exePath ($sizeMb MB)" -ForegroundColor Green
} else {
    if (-not (Test-Path $exePath)) {
        throw "SkipPyInstaller set but EXE missing: $exePath"
    }
    Write-Host "Skipping PyInstaller (using existing EXE)"
}

# --- Inno Setup ---
if (-not $SkipInstaller) {
    Write-Step "Building installer with Inno Setup"
    $iscc = Find-ISCC
    if (-not $iscc) {
        Write-Host "Inno Setup (ISCC.exe) not found." -ForegroundColor Yellow
        Write-Host "Install: winget install --id JRSoftware.InnoSetup -e"
        Write-Host "Or open installer\MD-Converter.iss in Inno Setup Compiler."
        throw "ISCC.exe not found"
    }
    Write-Host "ISCC: $iscc"

    $iss = Join-Path $Root "installer\MD-Converter.iss"
    $outDir = Join-Path $Root "dist\installer"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    & $iscc $iss
    if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

    $setup = Get-ChildItem $outDir -Filter "MD-Converter-Setup-*.exe" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $setup) { throw "Installer EXE not found in $outDir" }

    $setupMb = [math]::Round($setup.Length / 1MB, 2)
    Write-Host ""
    Write-Host "Installer ready:" -ForegroundColor Green
    Write-Host "  $($setup.FullName) ($setupMb MB)"
    Write-Host ""
    Write-Host "Distribute this file to end users."
} else {
    Write-Host "Skipping installer build"
}

Write-Step "Done"

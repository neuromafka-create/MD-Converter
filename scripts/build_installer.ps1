<#
.SYNOPSIS
  Build MD-Converter.exe (PyInstaller), stage Tesseract runtime, and Windows installer.

.DESCRIPTION
  1. Installs runtime deps if needed
  2. Builds onefile EXE via build.spec (embeds tessdata rus+eng)
  3. Stages portable Tesseract engine into dist\tesseract\
  4. Compiles installer\MD-Converter.iss with ISCC (all-in-one Setup)
  5. Prints paths to portable folder and Setup EXE

.EXAMPLE
  .\scripts\build_installer.ps1
  .\scripts\build_installer.ps1 -SkipPyInstaller
  .\scripts\build_installer.ps1 -SkipInstaller
#>
[CmdletBinding()]
param(
    [switch]$SkipPyInstaller,
    [switch]$SkipInstaller,
    [switch]$SkipTesseractStage,
    [string]$Python = "",
    [string]$TesseractSource = ""
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

# --- Tessdata present ---
$tessdataRus = Join-Path $Root "tessdata\rus.traineddata"
$tessdataEng = Join-Path $Root "tessdata\eng.traineddata"
if (-not ((Test-Path $tessdataRus) -and (Test-Path $tessdataEng))) {
    Write-Step "Downloading bundled tessdata (rus+eng)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\download_tessdata.ps1")
}

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
        # Keep installer folder if present; wipe other dist content for clean stage
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

# --- Stage Tesseract runtime (all-in-one, no winget for end users) ---
$tessRuntime = Join-Path $Root "dist\tesseract"
if (-not $SkipTesseractStage) {
    Write-Step "Staging portable Tesseract runtime"
    $stageScript = Join-Path $Root "scripts\stage_tesseract_runtime.ps1"
    if ($TesseractSource) {
        & $stageScript -Dest $tessRuntime -Source $TesseractSource
    } else {
        & $stageScript -Dest $tessRuntime
    }
    if (-not (Test-Path (Join-Path $tessRuntime "tesseract.exe"))) {
        throw "Expected staged engine missing: $tessRuntime\tesseract.exe"
    }
} else {
    if (-not (Test-Path (Join-Path $tessRuntime "tesseract.exe"))) {
        throw "SkipTesseractStage set but $tessRuntime\tesseract.exe missing"
    }
    Write-Host "Skipping Tesseract stage (using existing dist\tesseract)"
}

# Also place tessdata next to portable EXE for non-installer use
$portableTessdata = Join-Path $Root "dist\tessdata"
New-Item -ItemType Directory -Force -Path $portableTessdata | Out-Null
Copy-Item (Join-Path $Root "tessdata\*.traineddata") -Destination $portableTessdata -Force

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
    Write-Host "Installer ready (all-in-one, OCR included):" -ForegroundColor Green
    Write-Host "  $($setup.FullName) ($setupMb MB)"
    Write-Host ""
    Write-Host "Portable folder: dist\MD-Converter.exe + dist\tesseract\ + dist\tessdata\"
    Write-Host "Distribute the Setup EXE to end users — no winget/Tesseract install needed."
} else {
    Write-Host "Skipping installer build"
    Write-Host "Portable OCR needs: dist\MD-Converter.exe + dist\tesseract\ + dist\tessdata\"
}

Write-Step "Done"

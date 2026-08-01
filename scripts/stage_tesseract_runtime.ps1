<#
.SYNOPSIS
  Stage a portable Tesseract runtime next to the app (no separate user install).

.DESCRIPTION
  Copies tesseract.exe + required DLLs from a local UB-Mannheim install
  into dist\tesseract\ (and optionally vendor\tesseract\).
  Language models stay in project tessdata\ (rus+eng) — not copied from system.

.EXAMPLE
  .\scripts\stage_tesseract_runtime.ps1
  .\scripts\stage_tesseract_runtime.ps1 -Source "C:\Program Files\Tesseract-OCR"
#>
[CmdletBinding()]
param(
    [string]$Source = "",
    [string]$Dest = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Find-TesseractInstall {
    $candidates = @(
        $Source,
        $env:TESSERACT_HOME,
        "C:\Program Files\Tesseract-OCR",
        "C:\Program Files (x86)\Tesseract-OCR"
    ) | Where-Object { $_ -and $_.Trim() }
    foreach ($c in $candidates) {
        $exe = Join-Path $c "tesseract.exe"
        if (Test-Path $exe) { return (Resolve-Path $c).Path }
    }
    $cmd = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($cmd) {
        return (Split-Path $cmd.Source -Parent)
    }
    return $null
}

$srcDir = Find-TesseractInstall
if (-not $srcDir) {
    throw @"
Tesseract install not found (needed only to *build* the all-in-one package).
Install once on the build machine:
  winget install --id UB-Mannheim.TesseractOCR -e
Or pass -Source path to the folder that contains tesseract.exe.
"@
}

if (-not $Dest) {
    $Dest = Join-Path $Root "dist\tesseract"
}

Write-Host "Source: $srcDir"
Write-Host "Dest:   $Dest"

if (Test-Path $Dest) {
    Remove-Item $Dest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

# Runtime only: engine + DLLs. Skip training tools, uninstaller, HTML man pages.
$copyCount = 0
Get-ChildItem $srcDir -File | ForEach-Object {
    $name = $_.Name
    $ext = $_.Extension.ToLowerInvariant()
    $skip = $false
    if ($ext -eq ".html" -or $ext -eq ".txt" -or $ext -eq ".md") { $skip = $true }
    if ($name -match '(?i)uninstall|winpath') { $skip = $true }
    # Keep only tesseract.exe among executables (drop training utilities).
    if ($ext -eq ".exe" -and $name -ne "tesseract.exe") { $skip = $true }
    if ($ext -notin @(".exe", ".dll") -and -not $skip) { $skip = $true }
    if ($skip) { return }

    Copy-Item $_.FullName -Destination (Join-Path $Dest $name) -Force
    $copyCount++
}

$tessExe = Join-Path $Dest "tesseract.exe"
if (-not (Test-Path $tessExe)) {
    throw "tesseract.exe missing after staging: $Dest"
}

# Smoke-test: list langs should work; we inject TESSDATA_PREFIX to project tessdata.
$projectTess = Join-Path $Root "tessdata"
$env:TESSDATA_PREFIX = $projectTess
$out = & $tessExe --version 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "Staged tesseract failed --version: $out"
}
Write-Host $out.Trim()

$sizeMb = [math]::Round(((Get-ChildItem $Dest -File | Measure-Object Length -Sum).Sum) / 1MB, 2)
Write-Host "Staged $copyCount files ($sizeMb MB) → $Dest" -ForegroundColor Green

<#
.SYNOPSIS
  Download Tesseract language models (rus + eng) into project tessdata/.

.DESCRIPTION
  winget install of UB-Mannheim.TesseractOCR often ships only English.
  MD-Converter therefore ships its own tessdata (tessdata_fast) so Russian
  screenshots/PDF scans OCR correctly without reinstalling Tesseract.

.EXAMPLE
  .\scripts\download_tessdata.ps1
  .\scripts\download_tessdata.ps1 -Best   # larger, higher quality models
#>
[CmdletBinding()]
param(
    [switch]$Best
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$OutDir = Join-Path $Root "tessdata"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if ($Best) {
    $Base = "https://github.com/tesseract-ocr/tessdata_best/raw/main"
    $Tag = "tessdata_best"
} else {
    $Base = "https://github.com/tesseract-ocr/tessdata_fast/raw/main"
    $Tag = "tessdata_fast"
}

$langs = @("eng", "rus")
Write-Host "Downloading $Tag language models into $OutDir" -ForegroundColor Cyan

foreach ($lang in $langs) {
    $url = "$Base/$lang.traineddata"
    $out = Join-Path $OutDir "$lang.traineddata"
    Write-Host "  $lang <- $url"
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
    $mb = [math]::Round((Get-Item $out).Length / 1MB, 2)
    Write-Host "    OK ($mb MB)" -ForegroundColor Green
}

$readme = @"
# Tesseract language data (bundled)

Source: $Tag
Languages: eng, rus
Downloaded: $(Get-Date -Format "yyyy-MM-dd")

These files are used by MD-Converter via ``--tessdata-dir`` so OCR works even
when the system Tesseract install has only English (common after winget).

Re-download:  ``.\scripts\download_tessdata.ps1``
Best quality: ``.\scripts\download_tessdata.ps1 -Best``
"@
Set-Content -Path (Join-Path $OutDir "README.md") -Value $readme -Encoding UTF8

Write-Host ""
Write-Host "Done. Models ready for OCR (rus+eng)." -ForegroundColor Green

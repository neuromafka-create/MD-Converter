# Tesseract language data (bundled)

Source: **tessdata_fast** (https://github.com/tesseract-ocr/tessdata_fast)

| File | Language |
|------|----------|
| `eng.traineddata` | English |
| `rus.traineddata` | Russian |

MD-Converter always prefers this folder over the system Tesseract `tessdata`
(winget installs often ship **English only**, which turns Cyrillic into
Latin look-alikes).

Re-download:

```powershell
.\scripts\download_tessdata.ps1
# higher quality, larger files:
.\scripts\download_tessdata.ps1 -Best
```

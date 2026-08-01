# MD-Converter

<p align="center">
  <img src="assets/logo.png" alt="MD-Converter logo" width="128">
</p>

Windows GUI-приложение для **пакетной** конвертации документов в чистый **Markdown**, оптимизированный по объёму для базы знаний AI-агента.

**Поддерживаемые форматы:** `.docx` · `.xlsx` · `.pdf` · `.png` · `.jpg` / `.jpeg` · `.webp` · `.bmp` · `.tif`

## Скриншот

![MD-Converter — главное окно](docs/screenshot.png)

---

## Зачем это нужно

Офисные форматы (DOCX/XLSX/PDF) тяжёлые и плохо подходят для RAG и контекста LLM. Markdown:

- заметно меньше по размеру (часто на порядок);
- сохраняет структуру: заголовки, списки, таблицы;
- удобно индексировать и отдавать агенту.

MD-Converter делает пакетную структурную конвертацию **без LLM** — быстро и предсказуемо.

## Возможности

| Область | Что умеет |
|--------|-----------|
| **Пакетная обработка** | Файлы и папки, рекурсивный обход, прогресс и журнал |
| **DOCX** | Заголовки, bold/italic, списки, таблицы GFM, гиперссылки |
| **XLSX** | Все листы, пропуск пустых строк, один `.md` на книгу или на лист |
| **PDF** | Текст, эвристика заголовков по размеру шрифта, таблицы (PyMuPDF), секции по страницам |
| **OCR** | PDF-сканы и **скриншоты** (PNG/JPG…) — Tesseract (`rus+eng`), auto / off / force |
| **Изображения** | Вебинары, слайды, фото страниц → Markdown (всегда через OCR) |
| **Оптимизация** | Без base64-картинок, схлопывание пустых строк, YAML frontmatter |
| **Надёжность** | Ошибка в одном файле не останавливает весь пакет |
| **Сборка** | PyInstaller → `MD-Converter.exe` |

## Требования

- Windows 10/11
- Python **3.11+** (для запуска из исходников)
- **Tesseract OCR** (опционально, для сканов PDF) — см. [ниже](#ocr-tesseract)

## Быстрый старт

```powershell
git clone https://github.com/neuromafka-create/MD-Converter.git
cd MD-Converter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Как пользоваться

1. **Добавить файлы** или **Добавить папку** (документы и/или скриншоты)
2. Указать **папку вывода** (если пусто — создаётся `md_output` рядом с источником)
3. При необходимости настроить опции
4. Нажать **Конвертировать**

## Опции конвертации

| Опция | Описание |
|--------|----------|
| Сохранять структуру папок | Зеркалировать дерево каталогов в выводе |
| YAML frontmatter | Метаданные: `title`, `source`, `type`, `converted_at` (+ `pages` для PDF) |
| Схлопывать пустые строки | Уменьшает шум в Markdown |
| Excel: пустые строки | Не писать полностью пустые ряды |
| Excel: файл на лист | Отдельный `.md` для каждого листа книги |
| Перезаписывать `.md` | Иначе добавляется суффикс `_1`, `_2`, … |
| Картинки (DOCX/PDF) | Плейсхолдер `![image]()` или пропуск (base64 **не** встраивается) |
| OCR (PDF + изображения) | **Авто:** PDF без текста + все PNG/JPG; выкл. — без OCR (изображения не конвертируются) |

### OCR (Tesseract)

Для **сканов PDF** и **скриншотов** (вебинары, слайды) включите OCR (по умолчанию вкл.).

- **PNG / JPG / WEBP / BMP / TIFF** — всегда идут через OCR (это основной сценарий для методичек со скриншотов).
- **PDF** — OCR только страниц почти без текстового слоя (*auto*), либо всех страниц (*force*).

#### 1. Движок Tesseract

Нужен только **исполняемый файл** Tesseract (языки из winget **не обязательны**):

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

При необходимости:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

> **Важно:** winget часто ставит Tesseract **только с English**. Без русского пакета кириллица превращается в «кракозябры» (`npodeccuokanbHbIii` вместо нормального текста).  
> MD-Converter **вшивает** модели `rus` + `eng` в папку [`tessdata/`](tessdata/) и всегда передаёт их через `--tessdata-dir`.

#### 2. Языковые модели (в проекте)

Уже лежат в репозитории: `tessdata/rus.traineddata`, `tessdata/eng.traineddata` (tessdata_fast).

Перекачать / обновить:

```powershell
.\scripts\download_tessdata.ps1
# более точные (тяжелее):
.\scripts\download_tessdata.ps1 -Best
```

#### 3. Frontmatter

- PDF: `ocr_pages`, `ocr_lang`
- изображения: `ocr: true`, `ocr_lang`, `width`, `height`

Цифровые PDF с нормальным текстовым слоем OCR **не** запускают (быстро и без Tesseract).

Программные режимы (`ConvertOptions.ocr_mode`): `off` | `auto` | `force`.

**Совет для методичек:** положите папку со скриншотами вебинара → «Добавить папку» → папка вывода → **Конвертировать**. Получите набор `.md` по одному на кадр; при необходимости слейте их вручную или скриптом.

## Пример результата

**Вход:** `reglament.docx` + `catalog.xlsx`  
**Выход:** компактные `.md` с frontmatter и таблицами GFM.

```markdown
---
title: "catalog"
source: "C:/docs/catalog.xlsx"
type: xlsx
converted_at: "2026-07-31T13:40:36"
---

# catalog

## Каталог

| SKU | Название | Цена |
| --- | --- | --- |
| A1  | Винт     | 12.5 |
| A2  | Гайка    | 3    |
```

## Зависимости

| Пакет | Назначение |
|--------|------------|
| `customtkinter` | GUI |
| `python-docx` | Чтение Word |
| `openpyxl` | Чтение Excel |
| `pymupdf` | Чтение PDF |
| `Pillow` | Изображения / рендер страниц для OCR |
| `pytesseract` | Обёртка над системным Tesseract OCR |
| `pytest` | Тесты |
| `pyinstaller` | Сборка `.exe` |

Полный список: [`requirements.txt`](requirements.txt).

## Тесты

```powershell
pytest -q
```

## Сборка и инсталлятор (Windows)

### Полная сборка (рекомендуется)

Собирает `MD-Converter.exe` (PyInstaller) и установщик **Setup** (Inno Setup 6):

```powershell
pip install -r requirements.txt
# Нужен Inno Setup 6 (один раз):
# winget install --id JRSoftware.InnoSetup -e

.\scripts\build_installer.ps1
```

Результаты:

| Файл | Назначение |
|------|------------|
| `dist\MD-Converter.exe` | Portable-запуск без установки |
| `dist\installer\MD-Converter-Setup-1.1.2.exe` | Инсталлятор для пользователей |

Инсталлятор:

- ставит приложение в `%LocalAppData%\Programs\MD-Converter` (без обязательных прав администратора);
- создаёт ярлыки в меню «Пуск» (и опционально на рабочем столе);
- добавляет запись в «Установка и удаление программ»;
- поддерживает русский и английский язык мастера.

### Только EXE

```powershell
pyinstaller build.spec
# → dist\MD-Converter.exe
```

### Только инсталлятор (если EXE уже собран)

```powershell
.\scripts\build_installer.ps1 -SkipPyInstaller
```

## Структура проекта

```
MD-Converter/
├── main.py                 # Точка входа
├── requirements.txt
├── build.spec              # PyInstaller
├── assets/
│   ├── logo.png            # Логотип / иконка GUI
│   └── logo.ico            # Иконка EXE и установщика
├── tessdata/               # Вшитые модели Tesseract (rus + eng)
├── docs/
│   └── screenshot.png      # Скриншот для README
├── installer/
│   └── MD-Converter.iss    # Inno Setup: Windows-инсталлятор
├── scripts/
│   └── build_installer.ps1 # Сборка EXE + Setup
├── app/
│   ├── config.py           # Константы, поддерживаемые расширения
│   ├── models.py           # ConvertOptions, FileJob, результаты
│   ├── gui/                # CustomTkinter UI
│   ├── converters/         # DOCX / XLSX / PDF / images → Markdown
│   ├── core/               # scanner, batch, optimize
│   └── utils/              # GFM-таблицы, пути, frontmatter
└── tests/
```

### Поток данных

```
Файлы / папка → scanner → batch worker
    → converter (docx | xlsx | pdf | image+OCR) → optimize → .md
    → лог + статистика сжатия
```

## Ограничения

- Нет legacy `.doc` / `.xls` (только Office Open XML и PDF)
- OCR требует установленный **Tesseract** (движок); языки **rus+eng вшиты** в `tessdata/` и в portable `.exe`
- Качество OCR зависит от DPI, шрифта и контраста скриншота
- Сложные нумерации Word и экзотическая вёрстка PDF — best-effort
- Нет LLM-суммаризации (только структурная конвертация)
- Зашифрованные PDF без пустого пароля не открываются

## Roadmap (идеи)

- [x] OCR для сканов (Tesseract)
- [ ] CLI-режим для пайплайнов
- [ ] `.pptx`, legacy Office через LibreOffice
- [ ] Drag-and-drop в GUI
- [ ] Сохранение пресетов настроек

## Лицензия

MIT

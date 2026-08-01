# MD-Converter

<p align="center">
  <img src="assets/logo.png" alt="MD-Converter logo" width="128">
</p>

Windows GUI-приложение для **пакетной** конвертации документов и скриншотов в чистый **Markdown**, оптимизированный для базы знаний AI-агента и методических материалов.

**Поддерживаемые форматы:** `.docx` · `.xlsx` · `.pdf` · `.png` · `.jpg` / `.jpeg` · `.webp` · `.bmp` · `.tif`

**Версия:** 1.2.0 — полный установщик **со встроенным OCR** (Tesseract + rus/eng). Пользователю **не нужно** отдельно ставить Tesseract или языковые пакеты.

## Скриншот

<p align="center">
  <img src="docs/screenshot.png" alt="MD-Converter v1.2.0 — главное окно" width="900">
</p>

*MD-Converter **v1.2.0** — пакетная конвертация DOCX / XLSX / PDF / PNG / JPG → Markdown, OCR для сканов и скриншотов.*

---

## Зачем это нужно

Офисные форматы (DOCX/XLSX/PDF) и скриншоты вебинаров плохо подходят для RAG и контекста LLM «как есть». Markdown:

- заметно меньше по размеру (часто на порядок);
- сохраняет структуру: заголовки, списки, таблицы;
- удобно индексировать и отдавать агенту.

MD-Converter делает пакетную структурную конвертацию **без LLM** — быстро и предсказуемо. Сканы и скриншоты распознаются через встроенный OCR.

## Возможности

| Область | Что умеет |
|--------|-----------|
| **Пакетная обработка** | Файлы и папки, рекурсивный обход, прогресс и журнал |
| **DOCX** | Заголовки, bold/italic, списки, таблицы GFM, гиперссылки |
| **XLSX** | Все листы, пропуск пустых строк, один `.md` на книгу или на лист |
| **PDF** | Текст, эвристика заголовков по размеру шрифта, таблицы (PyMuPDF), секции по страницам |
| **OCR** | PDF-сканы и **скриншоты** (PNG/JPG…) — Tesseract `rus+eng` (вшит в Setup) |
| **Изображения** | Вебинары, слайды, фото → Markdown (всегда через OCR) |
| **Оптимизация** | Без base64-картинок, схлопывание пустых строк, YAML frontmatter |
| **Надёжность** | Ошибка в одном файле не останавливает весь пакет |
| **Установка** | Один Setup: приложение + движок OCR + языки rus/eng |

## Установка (для пользователей)

1. Скачайте **`MD-Converter-Setup-1.2.0.exe`** из [Releases](https://github.com/neuromafka-create/MD-Converter/releases).
2. Запустите установщик (права администратора **не обязательны**).
3. Откройте MD-Converter из меню «Пуск».

Ничего дополнительно (winget, Tesseract, Python) ставить **не нужно**.

### Portable (без установщика)

Из артефактов сборки / релиза возьмите вместе:

- `MD-Converter.exe`
- папку `tesseract\` (движок)
- папку `tessdata\` (языки)

и положите рядом — OCR заработает так же, как после Setup.

## Как пользоваться

1. **Добавить файлы** или **Добавить папку** (документы и/или скриншоты вебинара)
2. Указать **папку вывода** (если пусто — создаётся `md_output` рядом с источником)
3. При необходимости настроить опции (OCR по умолчанию включён)
4. Нажать **Конвертировать**

**Методички со скриншотов:** папка с PNG/JPG → «Добавить папку» → конвертация → по одному `.md` на кадр.

## Опции конвертации

| Опция | Описание |
|--------|----------|
| Сохранять структуру папок | Зеркалировать дерево каталогов в выводе |
| YAML frontmatter | Метаданные: `title`, `source`, `type`, `converted_at` (+ `pages` для PDF) |
| Схлопывать пустые строки | Уменьшает шум в Markdown |
| Excel: пустые строки | Не писать полностью пустые ряды |
| Excel: файл на лист | Отдельный `.md` для каждого листа книги |
| Перезаписывать `.md` | Иначе добавляется суффикс `_1`, `_2`, … |
| Картинки в DOCX/PDF | Плейсхолдер `![image]()` или пропуск (base64 **не** встраивается) |
| OCR (PDF + изображения) | **Авто:** PDF без текста + все PNG/JPG; выкл. — без OCR |

### OCR

- **PNG / JPG / WEBP / BMP / TIFF** — всегда через OCR.
- **PDF** — OCR страниц почти без текстового слоя (*auto*), либо всех (*force*).
- Языки по умолчанию: **`rus+eng`** (модели в `tessdata/`).
- Цифровые PDF с нормальным текстовым слоем OCR **не** запускают.

В frontmatter:

- PDF: `ocr_pages`, `ocr_lang`
- изображения: `ocr: true`, `ocr_lang`, `width`, `height`

## Пример результата

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

## Разработка (из исходников)

```powershell
git clone https://github.com/neuromafka-create/MD-Converter.git
cd MD-Converter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# языки OCR (если ещё не в репозитории):
.\scripts\download_tessdata.ps1
python main.py
```

### Зависимости Python

| Пакет | Назначение |
|--------|------------|
| `customtkinter` | GUI |
| `python-docx` | Word |
| `openpyxl` | Excel |
| `pymupdf` | PDF |
| `Pillow` | Изображения / OCR prep |
| `pytesseract` | Обёртка Tesseract |
| `pytest` | Тесты |
| `pyinstaller` | Сборка `.exe` |

### Тесты

```powershell
pytest -q
```

### Сборка Setup (all-in-one)

На машине сборки нужны:

- Python 3.11+
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install --id JRSoftware.InnoSetup -e`)
- Tesseract **только для сборки** (скопировать runtime в пакет):  
  `winget install --id UB-Mannheim.TesseractOCR -e`

```powershell
.\scripts\build_installer.ps1
```

Результаты:

| Файл | Назначение |
|------|------------|
| `dist\MD-Converter.exe` | GUI (внутри — tessdata) |
| `dist\tesseract\` | Portable-движок OCR |
| `dist\tessdata\` | rus + eng |
| `dist\installer\MD-Converter-Setup-1.2.0.exe` | **Полный установщик для пользователей** |

## Структура проекта

```
MD-Converter/
├── main.py
├── requirements.txt
├── build.spec
├── assets/                 # логотип / иконка
├── tessdata/               # rus.traineddata + eng.traineddata
├── docs/screenshot.png
├── installer/MD-Converter.iss
├── scripts/
│   ├── build_installer.ps1
│   ├── download_tessdata.ps1
│   └── stage_tesseract_runtime.ps1
├── app/
│   ├── config.py
│   ├── models.py
│   ├── gui/
│   ├── converters/         # docx / xlsx / pdf / image
│   ├── core/
│   └── utils/              # ocr, postprocess, markdown, paths
└── tests/
```

```
Файлы / папка → scanner → batch worker
    → converter (docx | xlsx | pdf | image+OCR) → optimize → .md
```

## Ограничения

- Нет legacy `.doc` / `.xls` (только Office Open XML, PDF и растры)
- Качество OCR зависит от DPI, шрифта и контраста скриншота
- Сложные нумерации Word и экзотическая вёрстка PDF — best-effort
- Нет LLM-суммаризации (только структурная конвертация)
- Зашифрованные PDF без пустого пароля не открываются

## Roadmap

- [x] OCR для сканов PDF (Tesseract)
- [x] OCR изображений (PNG/JPG…)
- [x] Вшитые языки rus+eng
- [x] Полный Setup без отдельной установки Tesseract
- [ ] CLI-режим
- [ ] Drag-and-drop в GUI
- [ ] Сохранение пресетов настроек

## Лицензия

MIT. В состав дистрибутива входит [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache-2.0) и языковые модели tessdata.

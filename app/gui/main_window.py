"""Main GUI window for MD-Converter."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.config import (
    APP_VERSION,
    DEFAULT_OUTPUT_DIRNAME,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
)
from app.core.batch import BatchConverter
from app.core.scanner import scan_paths
from app.models import BatchSummary, ConvertOptions, ConvertResult, FileJob


class MainWindow:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.geometry("980x720")

        self._paths: list[Path] = []
        self._batch: BatchConverter | None = None

        self._build_ui()
        self._set_busy(False)

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="MD-Converter",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text=f"Пакетная конвертация DOCX/XLSX/PDF/PNG/JPG → Markdown  ·  v{APP_VERSION}",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray65"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Sources
        src_frame = ctk.CTkFrame(self.root)
        src_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        src_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(src_frame, text="Источник", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )

        btn_row = ctk.CTkFrame(src_frame, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        self.btn_add_files = ctk.CTkButton(btn_row, text="Добавить файлы…", command=self._add_files, width=140)
        self.btn_add_files.pack(side="left", padx=(0, 8))
        self.btn_add_folder = ctk.CTkButton(btn_row, text="Добавить папку…", command=self._add_folder, width=140)
        self.btn_add_folder.pack(side="left", padx=(0, 8))
        self.btn_clear = ctk.CTkButton(
            btn_row, text="Очистить", command=self._clear_sources, width=100, fg_color="gray40"
        )
        self.btn_clear.pack(side="left", padx=(0, 8))

        self.lbl_count = ctk.CTkLabel(btn_row, text="Файлов: 0")
        self.lbl_count.pack(side="right")

        self.listbox = tk.Listbox(
            src_frame,
            height=8,
            activestyle="dotbox",
            selectmode=tk.EXTENDED,
            font=("Segoe UI", 10),
        )
        self.listbox.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

        # Middle: options + output
        mid = ctk.CTkFrame(self.root, fg_color="transparent")
        mid.grid(row=2, column=0, sticky="nsew", padx=16, pady=4)
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_columnconfigure(1, weight=1)
        mid.grid_rowconfigure(0, weight=1)

        opt_frame = ctk.CTkFrame(mid)
        opt_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(opt_frame, text="Опции", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        self.var_preserve = ctk.BooleanVar(value=True)
        self.var_frontmatter = ctk.BooleanVar(value=True)
        self.var_collapse = ctk.BooleanVar(value=True)
        self.var_skip_empty = ctk.BooleanVar(value=True)
        self.var_per_sheet = ctk.BooleanVar(value=False)
        self.var_overwrite = ctk.BooleanVar(value=True)
        self.var_ocr = ctk.BooleanVar(value=True)
        self.var_image = ctk.StringVar(value="placeholder")

        for text, var in [
            ("Сохранять структуру папок", self.var_preserve),
            ("YAML frontmatter (метаданные)", self.var_frontmatter),
            ("Схлопывать лишние пустые строки", self.var_collapse),
            ("Excel: пропускать пустые строки", self.var_skip_empty),
            ("Excel: отдельный .md на каждый лист", self.var_per_sheet),
            ("Перезаписывать существующие .md", self.var_overwrite),
            ("OCR (PDF-сканы и изображения, Tesseract)", self.var_ocr),
        ]:
            ctk.CTkCheckBox(opt_frame, text=text, variable=var).pack(anchor="w", padx=14, pady=3)

        img_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        img_row.pack(anchor="w", padx=14, pady=(8, 4), fill="x")
        ctk.CTkLabel(img_row, text="Картинки в DOCX/PDF:").pack(side="left")
        ctk.CTkRadioButton(
            img_row, text="плейсхолдер", variable=self.var_image, value="placeholder"
        ).pack(side="left", padx=(10, 6))
        ctk.CTkRadioButton(
            img_row, text="пропускать", variable=self.var_image, value="skip"
        ).pack(side="left")

        ctk.CTkLabel(
            opt_frame,
            text="OCR: PNG/JPG всегда; PDF — без текста. Tesseract + языки rus/eng из tessdata/.",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
            wraplength=360,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 12))

        out_frame = ctk.CTkFrame(mid)
        out_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        out_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(out_frame, text="Папка вывода", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )

        path_row = ctk.CTkFrame(out_frame, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", padx=12)
        path_row.grid_columnconfigure(0, weight=1)

        self.var_output = ctk.StringVar(value="")
        self.entry_output = ctk.CTkEntry(path_row, textvariable=self.var_output)
        self.entry_output.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(path_row, text="Обзор…", width=90, command=self._browse_output).grid(
            row=0, column=1
        )

        ctk.CTkLabel(
            out_frame,
            text="Если пусто — будет создана подпапка md_output рядом с первым источником.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray65"),
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(8, 4))

        # Actions
        action = ctk.CTkFrame(out_frame, fg_color="transparent")
        action.grid(row=3, column=0, sticky="ew", padx=12, pady=(16, 12))
        self.btn_convert = ctk.CTkButton(
            action,
            text="Конвертировать",
            command=self._start_convert,
            height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.btn_convert.pack(side="left", padx=(0, 8))
        self.btn_cancel = ctk.CTkButton(
            action,
            text="Отмена",
            command=self._cancel_convert,
            height=36,
            width=100,
            fg_color="gray40",
            state="disabled",
        )
        self.btn_cancel.pack(side="left")

        # Log + progress
        bottom = ctk.CTkFrame(self.root)
        bottom.grid(row=3, column=0, sticky="nsew", padx=16, pady=(4, 16))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        prog_row = ctk.CTkFrame(bottom, fg_color="transparent")
        prog_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        prog_row.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(prog_row)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.progress.set(0)
        self.lbl_progress = ctk.CTkLabel(prog_row, text="0 / 0", width=80)
        self.lbl_progress.grid(row=0, column=1)

        self.log = ctk.CTkTextbox(bottom, height=180, font=ctk.CTkFont(family="Consolas", size=12))
        self.log.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))
        self.log.configure(state="disabled")

    # ── Source management ────────────────────────────────────────────

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Выберите документы и изображения",
            filetypes=[
                ("Поддерживаемые", "*.docx;*.xlsx;*.pdf;*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff"),
                ("Документы", "*.docx;*.xlsx;*.pdf"),
                ("Изображения", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff"),
                ("Word", "*.docx"),
                ("Excel", "*.xlsx"),
                ("PDF", "*.pdf"),
                ("Все файлы", "*.*"),
            ],
        )
        if not paths:
            return
        self._paths.extend(Path(p) for p in paths)
        self._refresh_file_list()

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Выберите папку с документами")
        if not folder:
            return
        self._paths.append(Path(folder))
        self._refresh_file_list()

    def _clear_sources(self) -> None:
        self._paths.clear()
        self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        jobs = scan_paths(self._paths, recursive=True)
        self.listbox.delete(0, tk.END)
        for job in jobs:
            self.listbox.insert(tk.END, str(job.source))
        self.lbl_count.configure(text=f"Файлов: {len(jobs)}")
        self._jobs_cache = jobs

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(title="Папка для Markdown")
        if folder:
            self.var_output.set(folder)

    # ── Conversion ───────────────────────────────────────────────────

    def _collect_options(self) -> ConvertOptions:
        image_mode = self.var_image.get()
        if image_mode not in ("skip", "placeholder"):
            image_mode = "placeholder"
        return ConvertOptions(
            preserve_structure=bool(self.var_preserve.get()),
            yaml_frontmatter=bool(self.var_frontmatter.get()),
            collapse_blank_lines=bool(self.var_collapse.get()),
            skip_empty_excel_rows=bool(self.var_skip_empty.get()),
            excel_one_file_per_sheet=bool(self.var_per_sheet.get()),
            image_mode=image_mode,  # type: ignore[arg-type]
            overwrite=bool(self.var_overwrite.get()),
            ocr_mode="auto" if bool(self.var_ocr.get()) else "off",
        )

    def _resolve_output_dir(self, jobs: list[FileJob]) -> Path | None:
        raw = self.var_output.get().strip()
        if raw:
            return Path(raw)
        if not jobs:
            return None
        # Default: sibling md_output next to first source's parent
        first = jobs[0].source
        return first.parent / DEFAULT_OUTPUT_DIRNAME

    def _start_convert(self) -> None:
        if self._batch and self._batch.is_running:
            return

        jobs = getattr(self, "_jobs_cache", None) or scan_paths(self._paths, recursive=True)
        if not jobs:
            messagebox.showinfo(
                "Нет файлов",
                "Добавьте .docx, .xlsx, .pdf, .png, .jpg (или папку) для конвертации.",
            )
            return

        output_dir = self._resolve_output_dir(jobs)
        if output_dir is None:
            messagebox.showwarning("Папка вывода", "Укажите папку для сохранения Markdown.")
            return

        if not self.var_output.get().strip():
            self.var_output.set(str(output_dir))

        options = self._collect_options()
        self._append_log("—" * 48)
        self.progress.set(0)
        self.lbl_progress.configure(text=f"0 / {len(jobs)}")
        self._set_busy(True)

        self._batch = BatchConverter(
            jobs=jobs,
            output_dir=output_dir,
            options=options,
            on_progress=self._on_progress_thread,
            on_log=self._on_log_thread,
            on_finished=self._on_finished_thread,
        )
        self._batch.start()

    def _cancel_convert(self) -> None:
        if self._batch:
            self._batch.cancel()
            self._append_log("Запрошена отмена…")

    def _set_busy(self, busy: bool) -> None:
        state_idle = "normal" if not busy else "disabled"
        state_busy = "normal" if busy else "disabled"
        for w in (
            self.btn_add_files,
            self.btn_add_folder,
            self.btn_clear,
            self.btn_convert,
        ):
            w.configure(state=state_idle)
        self.btn_cancel.configure(state=state_busy)

    # Thread-safe UI marshaling via after()
    def _on_progress_thread(
        self,
        current: int,
        total: int,
        job: FileJob,
        result: ConvertResult | None,
    ) -> None:
        self.root.after(0, lambda: self._on_progress(current, total, job, result))

    def _on_log_thread(self, message: str) -> None:
        self.root.after(0, lambda m=message: self._append_log(m))

    def _on_finished_thread(self, summary: BatchSummary) -> None:
        self.root.after(0, lambda: self._on_finished(summary))

    def _on_progress(
        self,
        current: int,
        total: int,
        job: FileJob,
        result: ConvertResult | None,
    ) -> None:
        if total > 0:
            self.progress.set(current / total)
        self.lbl_progress.configure(text=f"{current} / {total}")

    def _on_finished(self, summary: BatchSummary) -> None:
        self._set_busy(False)
        if summary.total > 0:
            self.progress.set(1.0)
            self.lbl_progress.configure(text=f"{summary.total} / {summary.total}")

        if summary.failed and summary.succeeded == 0:
            messagebox.showerror(
                "Готово с ошибками",
                f"Не удалось конвертировать ни одного файла.\nОшибок: {summary.failed}",
            )
        elif summary.failed:
            messagebox.showwarning(
                "Готово",
                f"Успешно: {summary.succeeded}\nОшибок: {summary.failed}\n"
                f"См. журнал для подробностей.",
            )
        else:
            pct = summary.compression_percent
            pct_s = f"{pct:.1f}%" if pct is not None else "—"
            messagebox.showinfo(
                "Готово",
                f"Конвертировано файлов: {summary.succeeded}\n"
                f"Сжатие объёма: ~{pct_s}\n"
                f"Результат: {self.var_output.get()}",
            )

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

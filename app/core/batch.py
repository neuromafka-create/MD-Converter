"""Batch conversion orchestration with progress callbacks."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from app.models import BatchSummary, ConvertOptions, ConvertResult, FileJob

ProgressCallback = Callable[[int, int, FileJob, ConvertResult | None], None]
LogCallback = Callable[[str], None]


class BatchConverter:
    """
    Run conversions sequentially in a background thread.

    Callbacks may be invoked from the worker thread — GUI must marshal to main thread.
    """

    def __init__(
        self,
        jobs: list[FileJob],
        output_dir: Path,
        options: ConvertOptions,
        *,
        on_progress: ProgressCallback | None = None,
        on_log: LogCallback | None = None,
        on_finished: Callable[[BatchSummary], None] | None = None,
    ) -> None:
        self.jobs = jobs
        self.output_dir = Path(output_dir)
        self.options = options
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_finished = on_finished
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Batch already running")
        self._cancel.clear()
        self._thread = threading.Thread(target=self._run, name="md-batch", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def run_sync(self) -> BatchSummary:
        """Synchronous run (for tests / CLI)."""
        return self._run()

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(message)

    def _run(self) -> BatchSummary:
        summary = BatchSummary(total=len(self.jobs))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"Старт: {summary.total} файл(ов) → {self.output_dir}")

        for index, job in enumerate(self.jobs, start=1):
            if self._cancel.is_set():
                self._log("Отменено пользователем.")
                break

            self._log(f"[{index}/{summary.total}] {job.source.name}")
            if self.on_progress:
                self.on_progress(index - 1, summary.total, job, None)

            # Local import avoids circular dependency with converters → core.optimize
            from app.converters import convert_job

            result = convert_job(job, self.output_dir, self.options)
            summary.results.append(result)
            summary.bytes_in += result.bytes_in
            summary.bytes_out += result.bytes_out

            if result.ok:
                summary.succeeded += 1
                outs = ", ".join(str(p.name) for p in result.outputs) or "?"
                ratio = ""
                if result.bytes_in > 0:
                    saved = (1 - result.bytes_out / result.bytes_in) * 100
                    ratio = f" (−{saved:.0f}% объёма)"
                self._log(f"  OK → {outs}{ratio}")
            else:
                summary.failed += 1
                self._log(f"  ОШИБКА: {result.error}")

            if self.on_progress:
                self.on_progress(index, summary.total, job, result)

        if not self._cancel.is_set():
            pct = summary.compression_percent
            pct_s = f"{pct:.1f}%" if pct is not None else "n/a"
            self._log(
                f"Готово: успешно {summary.succeeded}, ошибок {summary.failed}, "
                f"сжатие ~{pct_s} "
                f"({_fmt_size(summary.bytes_in)} → {_fmt_size(summary.bytes_out)})"
            )

        if self.on_finished:
            self.on_finished(summary)
        return summary


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"

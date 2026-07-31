"""Core package: scanning, batching, markdown optimization."""

from .optimize import optimize_markdown
from .scanner import scan_paths

__all__ = ["optimize_markdown", "scan_paths", "BatchConverter"]


def __getattr__(name: str):
    # Lazy export avoids circular import: batch → converters → core.optimize
    if name == "BatchConverter":
        from .batch import BatchConverter

        return BatchConverter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

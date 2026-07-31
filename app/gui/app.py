"""Application bootstrap."""

from __future__ import annotations

import customtkinter as ctk

from app.config import APP_NAME
from app.gui.main_window import MainWindow
from app.resources import resource_path


def _apply_app_icon(root: ctk.CTk) -> None:
    """Set window / taskbar icon from bundled assets."""
    ico = resource_path("assets", "logo.ico")
    if ico.is_file():
        try:
            root.iconbitmap(default=str(ico))
            root.iconbitmap(str(ico))
        except Exception:
            pass

    # Higher-quality icon for title bar where supported (keep PhotoImage ref).
    png = resource_path("assets", "logo.png")
    if png.is_file():
        try:
            from PIL import Image, ImageTk

            img = Image.open(png).convert("RGBA")
            img.thumbnail((256, 256), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            root.iconphoto(True, photo)
            root._md_icon_photo = photo  # noqa: SLF001 — prevent GC
        except Exception:
            pass


def run_app() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(APP_NAME)
    _apply_app_icon(root)
    MainWindow(root)
    root.mainloop()

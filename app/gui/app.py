"""Application bootstrap."""

from __future__ import annotations

import customtkinter as ctk

from app.config import APP_NAME
from app.gui.main_window import MainWindow


def run_app() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(APP_NAME)
    MainWindow(root)
    root.mainloop()

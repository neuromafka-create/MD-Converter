# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for MD-Converter (Windows)

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH)

datas = []
binaries = []
hiddenimports = []

# customtkinter ships theme assets
tmp_ret = collect_all("customtkinter")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# App icon (window + taskbar when frozen)
_icon_ico = ROOT / "assets" / "logo.ico"
_icon_png = ROOT / "assets" / "logo.png"
if _icon_ico.is_file():
    datas.append((str(_icon_ico), "assets"))
if _icon_png.is_file():
    datas.append((str(_icon_png), "assets"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "docx",
        "openpyxl",
        "fitz",
        "pymupdf",
        "PIL",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MD-Converter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,
    uac_admin=False,
    icon=str(_icon_ico) if _icon_ico.is_file() else None,
)

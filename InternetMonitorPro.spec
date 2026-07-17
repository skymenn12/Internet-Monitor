# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path.cwd()
assets_dir = project_root / "assets"

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]
# Be tolerant with PySide6 plugin resolution in different environments.
hiddenimports += [m for m in collect_submodules("PySide6") if m.startswith("PySide6.Qt")]


a = Analysis(
    ["src/internet_monitor_pro/main.py"],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[(str(assets_dir), "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InternetMonitorPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets_dir / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="InternetMonitorPro",
)

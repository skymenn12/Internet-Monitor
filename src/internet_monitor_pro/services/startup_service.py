from __future__ import annotations

import os
import sys
from pathlib import Path

if os.name == "nt":
    import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "InternetProtokoll"
LEGACY_REG_NAMES = ("InternetMonitorPro",)


def should_notify_duplicate_start(argv: list[str]) -> bool:
    """Only interactive launches should show the already-running dialog."""
    return "--minimized" not in argv


class StartupService:
    @staticmethod
    def _command(start_minimized: bool = True) -> str:
        minimized_arg = " --minimized" if start_minimized else ""
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"{minimized_arg}'
        script = Path(sys.argv[0]).resolve()
        return f'"{sys.executable}" "{script}"{minimized_arg}'

    @classmethod
    def is_enabled(cls) -> bool:
        if os.name != "nt":
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(value)
        except OSError:
            return False

    @classmethod
    def set_enabled(cls, enabled: bool, start_minimized: bool = True) -> None:
        if os.name != "nt":
            return
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cls._command(start_minimized))
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
            # Older builds used a second value name. Keeping both values makes Windows
            # launch the app twice and the losing process displays the lock warning.
            for legacy_name in LEGACY_REG_NAMES:
                try:
                    winreg.DeleteValue(key, legacy_name)
                except FileNotFoundError:
                    pass

from __future__ import annotations

import os
import sys
from pathlib import Path

if os.name == "nt":
    import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "InternetMonitorPro"


class StartupService:
    @staticmethod
    def _command() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --minimized'
        script = Path(sys.argv[0]).resolve()
        return f'"{sys.executable}" "{script}" --minimized'

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
    def set_enabled(cls, enabled: bool) -> None:
        if os.name != "nt":
            return
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cls._command())
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from internet_monitor_pro.constants import APP_AUTHOR, APP_NAME, CONFIG_FILE_NAME, DEFAULT_CONFIG

try:
    from platformdirs import user_config_dir
except ImportError:  # pragma: no cover
    def user_config_dir(appname: str, appauthor: str | None = None) -> str:
        return str(Path.home() / ".config" / appname)


class ConfigService:
    def __init__(self) -> None:
        self.config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / CONFIG_FILE_NAME
        self._config: dict[str, Any] = self._load_or_create()

    @property
    def path(self) -> Path:
        return self.config_path

    def _load_or_create(self) -> dict[str, Any]:
        if not self.config_path.exists():
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            self._write(cfg)
            return cfg

        try:
            with self.config_path.open("r", encoding="utf-8") as fh:
                user_cfg = json.load(fh)
        except Exception:
            user_cfg = {}

        merged = self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), user_cfg)
        self._write(merged)
        return merged

    def _deep_merge(self, base: dict[str, Any], custom: dict[str, Any]) -> dict[str, Any]:
        for key, value in custom.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def _write(self, data: dict[str, Any]) -> None:
        with self.config_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    def get_all(self) -> dict[str, Any]:
        return copy.deepcopy(self._config)

    def get(self, *keys: str, default: Any = None) -> Any:
        data: Any = self._config
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return default
            data = data[key]
        return copy.deepcopy(data)

    def save(self, config: dict[str, Any]) -> None:
        self._config = self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), config)
        self._write(self._config)

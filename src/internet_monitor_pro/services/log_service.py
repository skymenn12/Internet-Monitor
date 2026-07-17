from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from internet_monitor_pro.constants import APP_AUTHOR, APP_NAME, EVENT_HISTORY_FILE_NAME, LOG_FILE_NAME, REPORTS_DIR_NAME

try:
    from platformdirs import user_log_dir
except ImportError:  # pragma: no cover
    def user_log_dir(appname: str, appauthor: str | None = None) -> str:
        return str(Path.home() / ".local" / "share" / appname / "logs")


class LogService:
    def __init__(self, max_bytes: int, backup_count: int) -> None:
        self.max_bytes = int(max_bytes)
        self.backup_count = int(backup_count)
        self.log_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = self.log_dir / REPORTS_DIR_NAME
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / LOG_FILE_NAME
        self.event_history_path = self.log_dir / EVENT_HISTORY_FILE_NAME
        self.event_history_path.touch(exist_ok=True)

        self.logger = logging.getLogger(APP_NAME)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler = RotatingFileHandler(self.log_path, maxBytes=self.max_bytes, backupCount=self.backup_count, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def reconfigure(self, max_bytes: int, backup_count: int) -> None:
        self.__init__(max_bytes=max_bytes, backup_count=backup_count)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def append_event(self, event: dict) -> None:
        with self.event_history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._trim_history_file()

    def read_history_events(self) -> list[dict]:
        events: list[dict] = []
        try:
            with self.event_history_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        events.append(obj)
        except FileNotFoundError:
            return []
        return events

    def export_events(self, events: list[dict], target_path: Path, formatter) -> Path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8") as fh:
            for event in events:
                fh.write(formatter(event) + "\n")
        return target_path

    def _trim_history_file(self) -> None:
        try:
            if self.event_history_path.stat().st_size <= self.max_bytes:
                return
            with self.event_history_path.open("rb") as fh:
                data = fh.read()
            trimmed = data[-self.max_bytes:]
            first_newline = trimmed.find(b"\n")
            if first_newline != -1:
                trimmed = trimmed[first_newline + 1:]
            with self.event_history_path.open("wb") as fh:
                fh.write(trimmed)
        except OSError:
            return

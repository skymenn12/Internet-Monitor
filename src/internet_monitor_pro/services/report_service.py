from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path


class ReportService:
    def __init__(self, reports_dir: Path) -> None:
        self.reports_dir = reports_dir

    def _normalize_date(self, value: str | date | datetime | None = None) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str) and value:
            return datetime.strptime(value, "%Y-%m-%d").date()
        return datetime.now().date()

    def build_daily_report_text(self, events: list[dict], report_date: str | date | datetime | None = None) -> str:
        target_date = self._normalize_date(report_date)
        counters = Counter(evt.get("type", "") for evt in events)
        lines = [
            f"Tagesbericht {target_date:%Y-%m-%d}",
            "=" * 50,
            f"Online-Wechsel: {counters.get('online', 0)}",
            f"Offline-Wechsel: {counters.get('offline', 0)}",
            f"IP-Änderungen: {counters.get('ip_changed', 0)}",
            f"Initiale IP-Erkennungen: {counters.get('ip_init', 0)}",
            f"Speedtests erfolgreich: {counters.get('speedtest_ok', 0)}",
            f"Speedtests mit Warnung: {counters.get('speedtest_warn', 0)}",
            f"Sonstige Fehler: {counters.get('error', 0)}",
            "",
            "Ereignisse:",
        ]
        if events:
            for evt in events:
                lines.append(f"{evt.get('timestamp', '-')} | {evt.get('type', '-')} | {evt.get('message', '-')}")
        else:
            lines.append("Keine Einträge für dieses Datum vorhanden.")
        return "\n".join(lines)

    def write_daily_report(self, events: list[dict], report_date: str | date | datetime | None = None) -> Path:
        target_date = self._normalize_date(report_date)
        filename = target_date.strftime("report_%Y-%m-%d.txt")
        path = self.reports_dir / filename
        path.write_text(self.build_daily_report_text(events, target_date), encoding="utf-8")
        return path

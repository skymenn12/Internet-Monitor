from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from internet_monitor_pro.services.network_service import NetworkService, SpeedtestResult


@dataclass(slots=True)
class EngineState:
    online: bool | None = None
    public_ip: str | None = None
    local_ip: str | None = None
    online_since: datetime | None = None
    offline_since: datetime | None = None
    last_speedtest: SpeedtestResult | None = None
    last_error: str = ""
    last_change: str = ""


class MonitorEngine(QObject):
    status_changed = Signal(dict)
    event_occurred = Signal(dict)
    error_occurred = Signal(str)
    action_started = Signal(str)

    def __init__(self, get_config: Callable[[], dict], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.get_config = get_config
        self.state = EngineState()
        self.events_today: list[dict] = []
        self._report_date = datetime.now().date()
        self._state_lock = threading.Lock()
        self._connection_running = False
        self._ip_running = False
        self._speedtest_running = False
        self.disconnect_count_today = 0
        self.public_ip_change_count_today = 0
        self.local_ip_change_count_today = 0
        self.ip_change_count_today = 0
        self.speedtest_results_today: list[SpeedtestResult] = []
        self.current_action: str = "Bereit"

        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self._on_connection_timer)
        self.ip_timer = QTimer(self)
        self.ip_timer.timeout.connect(self._on_ip_timer)
        self.speedtest_timer = QTimer(self)
        self.speedtest_timer.timeout.connect(self._on_speedtest_timer)
        self._connection_next_due: datetime | None = None
        self._ip_next_due: datetime | None = None
        self._speedtest_next_due: datetime | None = None
        self.report_timer = QTimer(self)
        self.report_timer.timeout.connect(self.check_report_due)
        self.report_timer.start(30_000)
        self.apply_schedule()

    def apply_schedule(self) -> None:
        cfg = self.get_config()
        now = datetime.now()
        if cfg["connection_watch"]["enabled"]:
            interval_seconds = max(0.5, float(cfg["connection_watch"]["interval_seconds"]))
            self.connection_timer.start(max(100, int(interval_seconds * 1000)))
            self._connection_next_due = now + timedelta(seconds=interval_seconds)
        else:
            self.connection_timer.stop()
            self._connection_next_due = None
        if cfg["ip_monitor"]["enabled"]:
            interval_seconds = max(1, int(cfg["ip_monitor"]["interval_seconds"]))
            self.ip_timer.start(interval_seconds * 1000)
            self._ip_next_due = now + timedelta(seconds=interval_seconds)
        else:
            self.ip_timer.stop()
            self._ip_next_due = None
        if cfg["speedtest"]["enabled"]:
            interval_minutes = max(1, int(cfg["speedtest"]["interval_minutes"]))
            self.speedtest_timer.start(interval_minutes * 60 * 1000)
            self._speedtest_next_due = now + timedelta(minutes=interval_minutes)
        else:
            self.speedtest_timer.stop()
            self._speedtest_next_due = None
        self.emit_status()

    def _on_connection_timer(self) -> None:
        cfg = self.get_config()
        interval_seconds = max(0.5, float(cfg["connection_watch"]["interval_seconds"]))
        self._connection_next_due = datetime.now() + timedelta(seconds=interval_seconds)
        self.request_connection()

    def _on_ip_timer(self) -> None:
        cfg = self.get_config()
        interval_seconds = max(1, int(cfg["ip_monitor"]["interval_seconds"]))
        self._ip_next_due = datetime.now() + timedelta(seconds=interval_seconds)
        self.request_ip()

    def _on_speedtest_timer(self) -> None:
        cfg = self.get_config()
        interval_minutes = max(1, int(cfg["speedtest"]["interval_minutes"]))
        self._speedtest_next_due = datetime.now() + timedelta(minutes=interval_minutes)
        self.request_speedtest()

    @staticmethod
    def _remaining_seconds(target: datetime | None) -> int | None:
        if target is None:
            return None
        return max(0, int((target - datetime.now()).total_seconds()))

    def start(self) -> None:
        self.request_connection()
        self.request_ip()
        self.request_speedtest()

    def restore_from_history(self, events: list[dict]) -> None:
        latest_speed = None
        for event in reversed(events):
            if event.get("type") in {"speedtest_ok", "speedtest_warn", "manual_speedtest", "manual_speedtest_warn"}:
                extra = event.get("extra") or {}
                try:
                    latest_speed = SpeedtestResult(
                        ok=True,
                        download_mbps=float(extra.get("download_mbps", 0.0) or 0.0),
                        upload_mbps=float(extra.get("upload_mbps", 0.0) or 0.0),
                        ping_ms=float(extra.get("ping_ms", 0.0) or 0.0),
                        error="",
                        server=str(extra.get("server", "") or ""),
                        isp=str(extra.get("isp", "") or ""),
                    )
                except Exception:
                    latest_speed = None
                break
        if latest_speed is not None:
            with self._state_lock:
                self.state.last_speedtest = latest_speed
                ts = next((e.get("timestamp") for e in reversed(events) if e.get("type") in {"speedtest_ok", "speedtest_warn", "manual_speedtest", "manual_speedtest_warn"}), None)
                if isinstance(ts, str) and ts.startswith(datetime.now().strftime("%Y-%m-%d")):
                    self.speedtest_results_today.append(latest_speed)
            self.emit_status()

    def _rollover_day_if_needed(self) -> None:
        today = datetime.now().date()
        if self._report_date != today:
            self._report_date = today
            self.disconnect_count_today = 0
            self.public_ip_change_count_today = 0
            self.local_ip_change_count_today = 0
            self.ip_change_count_today = 0
            self.speedtest_results_today.clear()
            self.events_today.clear()

    def emit_status(self) -> None:
        self._rollover_day_if_needed()
        cfg = self.get_config()
        with self._state_lock:
            last_speed = None if self.state.last_speedtest is None else asdict(self.state.last_speedtest)
            if last_speed and last_speed.get("ok"):
                avg_down = sum(r.download_mbps for r in self.speedtest_results_today if r.ok) / max(1, len([r for r in self.speedtest_results_today if r.ok]))
                avg_up = sum(r.upload_mbps for r in self.speedtest_results_today if r.ok) / max(1, len([r for r in self.speedtest_results_today if r.ok]))
                last_speed["avg_download_mbps"] = round(avg_down, 2)
                last_speed["avg_upload_mbps"] = round(avg_up, 2)
            payload = {
                "online": self.state.online,
                "public_ip": self.state.public_ip,
                "local_ip": self.state.local_ip,
                "last_speedtest": last_speed,
                "last_error": self.state.last_error,
                "last_change": self.state.last_change,
                "disconnect_count_today": self.disconnect_count_today,
                "public_ip_change_count_today": self.public_ip_change_count_today,
                "local_ip_change_count_today": self.local_ip_change_count_today,
                "ip_change_count_today": self.ip_change_count_today,
                "provider_download_mbps": cfg["speedtest"].get("provider_download_mbps", 0),
                "provider_upload_mbps": cfg["speedtest"].get("provider_upload_mbps", 0),
                "online_since": self.state.online_since.isoformat() if self.state.online_since else None,
                "offline_since": self.state.offline_since.isoformat() if self.state.offline_since else None,
                "next_connection_check_seconds": self._remaining_seconds(self._connection_next_due),
                "next_ip_check_seconds": self._remaining_seconds(self._ip_next_due),
                "next_speedtest_seconds": self._remaining_seconds(self._speedtest_next_due),
                "current_action": self.current_action,
            }
        self.status_changed.emit(payload)

    def add_event(self, event_type: str, message: str, extra: dict | None = None) -> None:
        self._rollover_day_if_needed()
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": event_type,
            "message": message,
            "extra": extra or {},
        }
        self.events_today.append(payload)
        self.event_occurred.emit(payload)

    def request_connection(self, manual: bool = False) -> None:
        if self._connection_running:
            self.current_action = "Verbindung wird bereits überprüft …"
            self.action_started.emit(self.current_action)
            self.emit_status()
            return
        self._connection_running = True
        self.current_action = "Verbindung wird überprüft …" if manual else "Automatische Verbindungsprüfung läuft …"
        self.action_started.emit(self.current_action)
        self.emit_status()
        threading.Thread(target=self._run_connection_check, args=(manual,), daemon=True).start()

    def _run_connection_check(self, manual: bool = False) -> None:
        try:
            cfg = self.get_config()
            online = NetworkService.is_online(cfg["connection_watch"]["socket_targets"])
            event = None
            with self._state_lock:
                previous = self.state.online
                if previous is None:
                    self.state.online = online
                    if online:
                        self.state.online_since = datetime.now()
                        self.state.offline_since = None
                    else:
                        self.state.offline_since = datetime.now()
                        self.state.online_since = None
                    self.state.last_change = f"Initialstatus: {'online' if online else 'offline'}"
                    event = ("online" if online else "offline", self.state.last_change, {"manual": manual, "initial": True})
                elif online != previous:
                    self.state.online = online
                    self.state.last_change = f"Internet {'online' if online else 'offline'}"
                    extra = {"manual": manual, "previous": previous, "current": online}
                    if previous is True and online is False:
                        self.state.offline_since = datetime.now()
                        self.state.online_since = None
                        self.disconnect_count_today += 1
                        event = ("offline", self.state.last_change, extra)
                    else:
                        self.state.online_since = datetime.now()
                        self.state.offline_since = None
                        event = ("online", self.state.last_change, extra)
                elif manual:
                    event = ("manual_connection_check", f"[MANUELL] Verbindung geprüft: {'online' if online else 'offline'}", {"manual": True, "current": online})
            if event:
                self.add_event(event[0], event[1], event[2])
            self.emit_status()
        finally:
            self._connection_running = False
            self.current_action = "Bereit"
            self.emit_status()

    def request_ip(self, manual: bool = False) -> None:
        if self._ip_running:
            self.current_action = "IP wird bereits überprüft …"
            self.action_started.emit(self.current_action)
            self.emit_status()
            return
        self._ip_running = True
        self.current_action = "IP wird überprüft …" if manual else "Automatische IP-Prüfung läuft …"
        self.action_started.emit(self.current_action)
        self.emit_status()
        threading.Thread(target=self._run_ip_check, args=(manual,), daemon=True).start()

    def _run_ip_check(self, manual: bool = False) -> None:
        try:
            cfg = self.get_config()
            if not cfg["ip_monitor"]["enabled"]:
                return
            public_ip = NetworkService.get_public_ip(cfg["ip_monitor"]["providers"])
            local_ip = NetworkService.get_local_ip()
            events: list[tuple[str, str, dict]] = []
            with self._state_lock:
                if public_ip:
                    if self.state.public_ip is None:
                        self.state.public_ip = public_ip
                        events.append(("ip_init", f"Initiale öffentliche IP erkannt: {public_ip}", {"scope": "public", "manual": manual, "new": public_ip}))
                    elif public_ip != self.state.public_ip:
                        old_ip = self.state.public_ip
                        self.state.public_ip = public_ip
                        self.public_ip_change_count_today += 1
                        self.ip_change_count_today += 1
                        events.append(("ip_changed", f"Öffentliche IP geändert: {old_ip} -> {public_ip}", {"scope": "public", "manual": manual, "old": old_ip, "new": public_ip}))
                if local_ip:
                    if self.state.local_ip is None:
                        self.state.local_ip = local_ip
                        events.append(("local_ip_init", f"Initiale lokale IP erkannt: {local_ip}", {"scope": "local", "manual": manual, "new": local_ip}))
                    elif local_ip != self.state.local_ip:
                        old_local_ip = self.state.local_ip
                        self.state.local_ip = local_ip
                        self.local_ip_change_count_today += 1
                        self.ip_change_count_today += 1
                        events.append(("local_ip_changed", f"Lokale IP geändert: {old_local_ip} -> {local_ip}", {"scope": "local", "manual": manual, "old": old_local_ip, "new": local_ip}))
                if manual:
                    events.append((
                        "manual_ip_check",
                        f"[MANUELL] IP geprüft | Öffentlich: {self.state.public_ip or '-'} | Lokal: {self.state.local_ip or '-'}",
                        {"manual": True, "scope": "both", "public_ip": self.state.public_ip, "local_ip": self.state.local_ip},
                    ))
            for item in events:
                self.add_event(item[0], item[1], item[2])
            self.emit_status()
        finally:
            self._ip_running = False
            self.current_action = "Bereit"
            self.emit_status()

    def request_speedtest(self, manual: bool = False) -> None:
        if self._speedtest_running:
            self.current_action = "Speedtest läuft bereits …"
            self.action_started.emit(self.current_action)
            self.emit_status()
            return
        cfg = self.get_config()
        if not cfg["speedtest"]["enabled"]:
            self.current_action = "Speedtest ist deaktiviert."
            self.action_started.emit(self.current_action)
            self.emit_status()
            return
        with self._state_lock:
            online = self.state.online
        if online is False:
            self.current_action = "Speedtest übersprungen: keine Internetverbindung."
            self.action_started.emit(self.current_action)
            self.emit_status()
            return
        self._speedtest_running = True
        self.current_action = "Speedtest wird ausgeführt …" if manual else "Automatischer Speedtest läuft …"
        self.action_started.emit(self.current_action)
        self.emit_status()
        threading.Thread(target=self._run_speedtest, args=(manual,), daemon=True).start()

    def _run_speedtest(self, manual: bool = False) -> None:
        try:
            cfg = self.get_config()
            result = NetworkService.run_speedtest(int(cfg["speedtest"]["timeout_seconds"]))
            provider_down = float(cfg["speedtest"].get("provider_download_mbps", 0) or 0)
            provider_up = float(cfg["speedtest"].get("provider_upload_mbps", 0) or 0)
            extra = asdict(result)
            extra["download_percent"] = round((result.download_mbps / provider_down) * 100, 1) if provider_down > 0 else 100.0
            extra["upload_percent"] = round((result.upload_mbps / provider_up) * 100, 1) if provider_up > 0 else 100.0
            with self._state_lock:
                self.state.last_speedtest = result
                if not result.ok:
                    self.state.last_error = result.error
                else:
                    self.speedtest_results_today.append(result)
            if result.ok:
                warn_messages: list[str] = []
                if cfg["speedtest"].get("warn_download_mbps_below", 0) > 0 and result.download_mbps < float(cfg["speedtest"]["warn_download_mbps_below"]):
                    warn_messages.append(f"Download zu niedrig: {result.download_mbps} Mbit/s")
                if cfg["speedtest"].get("warn_upload_mbps_below", 0) > 0 and result.upload_mbps < float(cfg["speedtest"]["warn_upload_mbps_below"]):
                    warn_messages.append(f"Upload zu niedrig: {result.upload_mbps} Mbit/s")
                if cfg["speedtest"].get("warn_ping_ms_above", 0) > 0 and result.ping_ms > float(cfg["speedtest"]["warn_ping_ms_above"]):
                    warn_messages.append(f"Ping zu hoch: {result.ping_ms} ms")
                extra["warn_messages"] = list(warn_messages)
                msg = (
                    f"Speedtest | Down {result.download_mbps} Mbit/s ({extra['download_percent']:.0f}%) | "
                    f"Up {result.upload_mbps} Mbit/s ({extra['upload_percent']:.0f}%) | Ping {result.ping_ms} ms"
                )
                if manual:
                    extra["manual"] = True
                    if warn_messages:
                        self.add_event("manual_speedtest_warn", "[MANUELL] " + msg + " | " + "; ".join(warn_messages), extra)
                    else:
                        self.add_event("manual_speedtest", "[MANUELL] " + msg, extra)
                else:
                    if warn_messages:
                        self.add_event("speedtest_warn", msg + " | " + "; ".join(warn_messages), extra)
                    else:
                        self.add_event("speedtest_ok", msg, extra)
            else:
                if manual:
                    self.add_event("manual_speedtest_error", f"[MANUELL] Speedtest fehlgeschlagen: {result.error}", extra)
                else:
                    self.add_event("error", f"Speedtest fehlgeschlagen: {result.error}")
                self.error_occurred.emit(result.error)
            self.emit_status()
        finally:
            self._speedtest_running = False
            self.current_action = "Bereit"
            self.emit_status()

    def consume_daily_events(self) -> list[dict]:
        events = list(self.events_today)
        self.events_today.clear()
        self._report_date = datetime.now().date()
        return events

    def check_report_due(self) -> None:
        now = datetime.now()
        cfg = self.get_config()
        if not cfg["reporting"]["enabled"]:
            return
        try:
            hours, minutes = [int(x) for x in str(cfg["reporting"]["daily_report_time"]).split(":", 1)]
        except Exception:
            hours, minutes = 23, 55
        if self._report_date == now.date():
            if now.hour > hours or (now.hour == hours and now.minute >= minutes):
                self.add_event("report_due", "Tagesbericht fällig")
                self._report_date = now.date().fromordinal(now.date().toordinal() - 1)

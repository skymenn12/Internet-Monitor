from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from internet_monitor_pro.constants import APP_NAME, APP_WINDOW_TITLE, APP_VERSION, ASSETS_DIR_NAME, ICON_FILE_NAME, POPUP_TITLE
from internet_monitor_pro.core.monitor_engine import MonitorEngine
from internet_monitor_pro.gui.settings_window import SettingsWindow
from internet_monitor_pro.services.config_service import ConfigService
from internet_monitor_pro.services.log_service import LogService
from internet_monitor_pro.services.notification_service import NotificationConfig, NotificationService
from internet_monitor_pro.services.report_service import ReportService
from internet_monitor_pro.services.startup_service import StartupService, should_notify_duplicate_start


class AppController:
    def __init__(self, app: QApplication, start_minimized: bool = False) -> None:
        self.app = app
        self.config_service = ConfigService()
        initial_cfg = self.config_service.get_all()
        StartupService.set_enabled(
            bool(initial_cfg["startup"]["start_with_windows"]),
            bool(initial_cfg["startup"]["start_minimized_to_tray"]),
        )
        self.log_service = LogService(max_bytes=int(initial_cfg["logging"]["max_bytes"]), backup_count=int(initial_cfg["logging"]["backup_count"]))
        self.report_service = ReportService(self.log_service.reports_dir)

        self.window = SettingsWindow()
        self.window.setWindowIcon(self._app_icon())
        self.window.title_bar.set_window_icon(self.window.windowIcon())
        self.window.load_config(initial_cfg, self.config_service.path, self.log_service.log_path)
        history_events = self.log_service.read_history_events()
        self.window.set_history_events(history_events)

        self.tray_icon = QSystemTrayIcon(self._app_icon(), self.app)
        self.tray_menu = QMenu()
        self.action_open = QAction("Einstellungen öffnen")
        self.action_check = QAction("Jetzt Verbindung prüfen")
        self.action_ip = QAction("Jetzt IP prüfen")
        self.action_speed = QAction("Jetzt Speedtest")
        self.action_logs = QAction("Logordner öffnen")
        self.action_quit = QAction("Beenden")
        for action in [self.action_open, self.action_check, self.action_ip, self.action_speed, self.action_logs]:
            self.tray_menu.addAction(action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.action_quit)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.setToolTip(APP_NAME)
        self.tray_icon.show()

        self.notification_service = NotificationService(self.tray_icon, self._notification_config)
        self.engine = MonitorEngine(self.config_service.get_all)

        self._wire_events()
        self.engine.restore_from_history(history_events)
        self.engine.start()

        if start_minimized:
            self.window.hide()
        else:
            self.window.show()

    def _resolve_asset_path(self, filename: str) -> Path | None:
        bases: list[Path] = []
        if getattr(sys, "frozen", False):
            bases.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)))
            bases.append(Path(sys.executable).resolve().parent)
        bases.append(Path(__file__).resolve().parents[3])
        for base in bases:
            candidate = base / ASSETS_DIR_NAME / filename
            if candidate.exists():
                return candidate
        return None

    def _app_icon(self) -> QIcon:
        icon_path = self._resolve_asset_path(ICON_FILE_NAME)
        if icon_path is not None:
            return QIcon(str(icon_path))
        return self.app.style().standardIcon(QStyle.SP_ComputerIcon)

    def _notification_config(self) -> NotificationConfig:
        n = self.config_service.get("notifications")
        return NotificationConfig(
            enabled=bool(n["enabled"]),
            show_online=bool(n["show_online"]),
            show_offline=bool(n["show_offline"]),
            show_ip_change=bool(n["show_ip_change"]),
            show_speed_warnings=bool(n["show_speed_warnings"]),
            cooldown_seconds=int(n["cooldown_seconds"]),
            show_windows_toasts=bool(n.get("show_windows_toasts", False)),
            show_app_toasts=bool(n.get("show_app_toasts", True)),
        )

    def _wire_events(self) -> None:
        self.action_open.triggered.connect(self.show_window)
        self.action_check.triggered.connect(lambda: self.engine.request_connection(manual=True))
        self.action_ip.triggered.connect(lambda: self.engine.request_ip(manual=True))
        self.action_speed.triggered.connect(lambda: self.engine.request_speedtest(manual=True))
        self.action_logs.triggered.connect(self.open_logs_folder)
        self.action_quit.triggered.connect(self.quit_application)
        self.tray_icon.activated.connect(lambda reason: self.show_window() if reason == QSystemTrayIcon.DoubleClick else None)

        self.window.btn_reload.clicked.connect(self.reload_settings)
        self.window.config_edited.connect(self.save_settings)
        self.window.btn_check_now.clicked.connect(lambda: self.engine.request_connection(manual=True))
        self.window.btn_ip_now.clicked.connect(lambda: self.engine.request_ip(manual=True))
        self.window.btn_speed_now.clicked.connect(lambda: self.engine.request_speedtest(manual=True))
        self.window.btn_open_logs.clicked.connect(self.open_logs_folder)
        self.window.export_filtered_requested.connect(self.export_filtered_events)
        self.window.copy_ip_requested.connect(self.copy_ip_to_clipboard)
        self.window.copy_local_ip_requested.connect(self.copy_ip_to_clipboard)
        self.window.test_online_popup_requested.connect(lambda: self.notification_service.notify("online_test", POPUP_TITLE, "Du bist online", ignore_cooldown=True))
        self.window.test_offline_popup_requested.connect(lambda: self.notification_service.notify("offline_test", POPUP_TITLE, "Du bist offline", ignore_cooldown=True))
        self.window.test_ip_popup_requested.connect(lambda: self.notification_service.notify("ip_test", POPUP_TITLE, "Neue IP erkannt", ignore_cooldown=True))
        self.window.daily_report_requested.connect(self.show_daily_report)

        self.engine.status_changed.connect(self.window.update_status)
        self.engine.status_changed.connect(self.window.update_status_meta)
        self.engine.status_changed.connect(self.update_tray_tooltip)
        self.engine.event_occurred.connect(self.on_event)
        self.engine.event_occurred.connect(lambda _event: self.window.clear_current_action())
        self.engine.error_occurred.connect(lambda text: self.log_service.error(text))
        self.engine.action_started.connect(self.window.set_current_action)
        self.engine.action_started.connect(lambda text: self.window.status_bar.showMessage(text, 5000))

        original_close_event = self.window.closeEvent

        def wrapped_close_event(event: QCloseEvent) -> None:
            if self.config_service.get("ui", "close_to_tray", default=True):
                event.ignore()
                self.window.hide()
                return
            original_close_event(event)

        self.window.closeEvent = wrapped_close_event  # type: ignore[method-assign]


    @staticmethod
    def _percent_color(percent: float) -> str:
        p = max(0.0, min(100.0, float(percent))) / 100.0
        red = int(255 * (1.0 - p))
        green = int(60 + (195 * p))
        blue = int(70 + (60 * p))
        return f"#{red:02x}{green:02x}{blue:02x}"

    def _speed_popup_line(self, label: str, value: float | None, percent: float | None, unit: str = "Mbit/s") -> str:
        if value is None:
            return label
        pct_value = 0.0 if percent is None else float(percent)
        color = self._percent_color(pct_value)
        return (
            f"{label}<br>"
            f"<span style='color:{color}; font-size:22px; font-weight:800'>{float(value):.2f}</span> "
            f"<span style='color:#f3f3f3; font-size:16px; font-weight:700'>{unit}</span> "
            f"<span style='color:{color}; font-size:18px; font-weight:800'>{pct_value:.0f}%</span>"
        )

    def on_event(self, event: dict) -> None:
        self.window.append_event(event)
        self.log_service.append_event(event)
        self.log_service.info(f"{event['type']} | {event['message']}")
        self.window.status_bar.showMessage(event["message"], 6000)

        event_type = event["type"]
        ncfg = self.config_service.get("notifications")
        if event_type == "online" and ncfg["show_online"]:
            self.notification_service.notify("online", POPUP_TITLE, "Du bist online")
        elif event_type == "offline" and ncfg["show_offline"]:
            self.notification_service.notify("offline", POPUP_TITLE, "Du bist offline")
        elif event_type in {"ip_changed", "local_ip_changed"} and ncfg["show_ip_change"]:
            new_ip = str((event.get("extra") or {}).get("new") or "")
            self.notification_service.notify("ip_changed", POPUP_TITLE, f"Neue IP: {new_ip}" if new_ip else "Neue IP erkannt")
        elif event_type in {"speedtest_warn", "manual_speedtest_warn"} and ncfg["show_speed_warnings"]:
            extra = event.get("extra") or {}
            blocks: list[str] = []
            warn_messages = list(extra.get("warn_messages") or [])
            download_percent = extra.get("download_percent")
            upload_percent = extra.get("upload_percent")
            download_value = extra.get("download_mbps")
            upload_value = extra.get("upload_mbps")
            ping_value = extra.get("ping_ms")
            for item in warn_messages:
                lower = str(item).lower()
                if "download" in lower:
                    blocks.append(self._speed_popup_line("Downloadgeschwindigkeit unter dem Schwellwert", download_value, download_percent))
                elif "upload" in lower:
                    blocks.append(self._speed_popup_line("Uploadgeschwindigkeit unter dem Schwellwert", upload_value, upload_percent))
                elif "ping" in lower:
                    if ping_value is not None:
                        blocks.append(
                            "Ping über dem Schwellwert<br>"
                            f"<span style='color:#f3f3f3; font-size:22px; font-weight:800'>{float(ping_value):.0f}</span> "
                            "<span style='color:#f3f3f3; font-size:16px; font-weight:700'>ms</span>"
                        )
                    else:
                        blocks.append("Ping über dem Schwellwert")
            message = "<br><br>".join(blocks) if blocks else event.get("message", "Speedtest-Warnung")
            self.notification_service.notify("speed_warn", POPUP_TITLE, message)
        elif event_type == "report_due":
            events = self.engine.consume_daily_events()
            path = self.report_service.write_daily_report(events)
            self.log_service.info(f"Tagesbericht geschrieben: {path}")

    def update_tray_tooltip(self, status: dict) -> None:
        online = status.get("online")
        ip = status.get("public_ip") or "-"
        state = "Online" if online is True else "Offline" if online is False else "Unbekannt"
        self.tray_icon.setToolTip(f"{APP_NAME}\nStatus: {state}\nIP: {ip}")

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def save_settings(self) -> None:
        current = self.config_service.get_all()
        extracted = self.window.extract_config()
        merged = self._deep_merge(current, extracted)
        self.config_service.save(merged)
        self.log_service.reconfigure(max_bytes=int(merged["logging"]["max_bytes"]), backup_count=int(merged["logging"]["backup_count"]))
        StartupService.set_enabled(
            bool(merged["startup"]["start_with_windows"]),
            bool(merged["startup"]["start_minimized_to_tray"]),
        )
        self.engine.apply_schedule()
        self.window.status_bar.showMessage(f"Einstellungen gespeichert: {self.config_service.path}", 3000)

    def reload_settings(self) -> None:
        cfg = self.config_service.get_all()
        self.window.load_config(cfg, self.config_service.path, self.log_service.log_path)
        self.window.set_history_events(self.log_service.read_history_events())
        self.window.status_bar.showMessage(f"Einstellungen neu geladen aus: {self.config_service.path}", 5000)

    def show_daily_report(self, report_date: str) -> None:
        events = [event for event in self.log_service.read_history_events() if str(event.get("timestamp", "")).startswith(report_date)]
        path = self.report_service.write_daily_report(events, report_date)
        content = self.report_service.build_daily_report_text(events, report_date)
        self.window.show_report_text(f"Tagesbericht für {report_date}", content)
        self.window.status_bar.showMessage(f"Tagesbericht geladen: {path}", 5000)

    def export_filtered_events(self) -> None:
        target = self.window.choose_export_path()
        if target is None:
            return
        path = self.log_service.export_events(self.window.filtered_events(), target, self.window._format_event)
        self.window.status_bar.showMessage(f"Gefilterte Ansicht exportiert: {path}", 5000)

    def copy_ip_to_clipboard(self, ip: str) -> None:
        QGuiApplication.clipboard().setText(ip)
        self.window.status_bar.showMessage(f"IP kopiert: {ip}", 4000)

    def open_logs_folder(self) -> None:
        folder = str(self.log_service.log_dir)
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def quit_application(self) -> None:
        self.tray_icon.hide()
        self.app.quit()

    @staticmethod
    def _deep_merge(base: dict, custom: dict) -> dict:
        for key, value in custom.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = AppController._deep_merge(base[key], value)
            else:
                base[key] = value
        return base


def main() -> int:
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Internetprotokoll.App")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_WINDOW_TITLE)
    app.setQuitOnLastWindowClosed(False)

    runtime_dir = QStandardPaths.writableLocation(QStandardPaths.TempLocation) or os.getcwd()
    os.makedirs(runtime_dir, exist_ok=True)
    lock = QLockFile(os.path.join(runtime_dir, "internet_monitor_pro.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        if should_notify_duplicate_start(sys.argv):
            QMessageBox.information(None, POPUP_TITLE, "Internetprotokoll läuft bereits.")
        return 0

    minimized = "--minimized" in sys.argv
    controller = AppController(app, start_minimized=minimized)
    app._instance_lock = lock  # type: ignore[attr-defined]
    app._controller = controller  # type: ignore[attr-defined]
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

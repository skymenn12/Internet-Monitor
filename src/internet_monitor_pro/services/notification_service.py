from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel, QSystemTrayIcon, QVBoxLayout, QWidget


@dataclass(slots=True)
class NotificationConfig:
    enabled: bool
    show_online: bool
    show_offline: bool
    show_ip_change: bool
    show_speed_warnings: bool
    cooldown_seconds: int
    show_windows_toasts: bool = True
    show_app_toasts: bool = True


class ToastPopup(QWidget):
    def __init__(self, message: str, offset_index: int = 0) -> None:
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setObjectName("toastPopup")
        msg_label = QLabel(message)
        msg_label.setTextFormat(Qt.RichText)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setMinimumWidth(360)
        msg_label.setStyleSheet("color:#f3f3f3; font-size:18px; font-weight:700; background:#202020; border:none; border-radius:10px; padding:12px 16px;")
        layout.addWidget(msg_label)
        self.setStyleSheet("QWidget#toastPopup { background: transparent; border: none; }")
        self.adjustSize()
        self._place(offset_index)

    def _place(self, offset_index: int) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - 18
        y = geo.bottom() - self.height() - 18 - (offset_index * (self.height() + 10))
        self.move(QPoint(max(0, x), max(0, y)))


class NotificationService:
    def __init__(self, tray_icon: QSystemTrayIcon, get_config: Callable[[], NotificationConfig]) -> None:
        self.tray_icon = tray_icon
        self.get_config = get_config
        self._last_sent: dict[str, float] = {}
        self._active_toasts: list[ToastPopup] = []

    def notify(self, event_key: str, title: str, message: str, ignore_cooldown: bool = False) -> None:
        cfg = self.get_config()
        if not cfg.enabled:
            return
        now = time.time()
        cooldown = max(0, int(cfg.cooldown_seconds))
        last = self._last_sent.get(event_key, 0.0)
        if not ignore_cooldown and now - last < cooldown:
            return
        self._last_sent[event_key] = now
        if not self.tray_icon.isVisible():
            self.tray_icon.show()
        icon = QSystemTrayIcon.Warning if event_key in {"offline", "speed_warn"} else QSystemTrayIcon.Information
        if cfg.show_windows_toasts:
            self.tray_icon.showMessage(title, message, icon, 8000)
        if cfg.show_app_toasts:
            self._show_fallback_toast(message)

    def _show_fallback_toast(self, message: str) -> None:
        toast = ToastPopup(message, len(self._active_toasts))
        self._active_toasts.append(toast)
        toast.show()

        def cleanup() -> None:
            if toast in self._active_toasts:
                self._active_toasts.remove(toast)
            toast.close()
            toast.deleteLater()
            for idx, item in enumerate(list(self._active_toasts)):
                item._place(idx)

        QTimer.singleShot(7000, cleanup)

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, Signal, QDate, QRectF, QTimer, QRect, QEvent, QObject
from datetime import datetime, timedelta
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPixmap, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from internet_monitor_pro.constants import APP_WINDOW_TITLE, APP_VERSION, APP_AUTHOR


class TitleBar(QWidget):
    def __init__(self, parent_window: QMainWindow) -> None:
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._drag_pos: QPoint | None = None
        self.setObjectName("titleBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 2, 2, 0)
        layout.setSpacing(8)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("titleLogo")
        self.set_window_icon(self.parent_window.windowIcon())
        layout.addWidget(self.logo_label)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setText(
            "<span style='font-size:30px; font-weight:800;'>Internet-Protokoll</span>"
            f" <span style='font-size:15px; color:#b8b8b8; font-weight:600;'>{APP_VERSION}</span>"
            f" <span style='font-size:15px; color:#b8b8b8; font-weight:600;'>- von {APP_AUTHOR}</span>"
        )
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("▢")
        self.btn_close = QPushButton("✕")
        for btn, name in [
            (self.btn_min, "titleMinButton"),
            (self.btn_max, "titleMaxButton"),
            (self.btn_close, "titleCloseButton"),
        ]:
            btn.setObjectName(name)
            btn.setFixedSize(40, 24)
            layout.addWidget(btn, 0, Qt.AlignTop)

        self.btn_min.clicked.connect(self.parent_window.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        self.btn_close.clicked.connect(self.parent_window.close)

    def set_window_icon(self, icon: QIcon) -> None:
        pix = icon.pixmap(28, 28)
        if not pix.isNull():
            self.logo_label.setPixmap(pix)
            self.logo_label.setFixedSize(28, 28)

    def _toggle_max_restore(self) -> None:
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton and not self.parent_window.isMaximized():
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._toggle_max_restore()
            event.accept()


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(58, 30)
        self.setFocusPolicy(Qt.StrongFocus)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if self._checked == checked:
            self.update()
            return
        self._checked = checked
        self.update()
        self.toggled.emit(self._checked)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(58, 30)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        track_w = 52.0
        track_h = 22.0
        track_x = (self.width() - track_w) / 2.0
        track_y = (self.height() - track_h) / 2.0
        track = QRectF(track_x, track_y, track_w, track_h)

        track_color = QColor('#2f6feb') if self._checked else QColor('#3a3a3a')
        track_border = QColor('#4f8cff') if self._checked else QColor('#515151')
        painter.setPen(QPen(track_border, 1))
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(track, track_h / 2.0, track_h / 2.0)

        knob_diameter = track_h - 2.0
        knob_x = track.right() - knob_diameter - 1.0 if self._checked else track.left() + 1.0
        knob = QRectF(knob_x, track.top() + 1.0, knob_diameter, knob_diameter)
        painter.setPen(QPen(QColor('#cfcfcf'), 1))
        painter.setBrush(QBrush(QColor('#f7f7f7')))
        painter.drawEllipse(knob)

        if self.hasFocus():
            focus_pen = QPen(QColor('#7fb2ff'), 1, Qt.DashLine)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(track.adjusted(-6, -4, 6, 4), 14, 14)

        painter.end()


class SliderSpinField(QWidget):
    valueChanged = Signal(float)

    def __init__(self, minimum: float, maximum: float, step: float = 1.0, decimals: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        self._step = float(step)
        self._decimals = int(decimals)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("rangeSlider")
        self.slider.setRange(0, max(0, int(round((self._maximum - self._minimum) / self._step))))
        self.slider.setSingleStep(1)
        self.slider.setFixedWidth(110)

        if self._decimals > 0:
            self.spin = QDoubleSpinBox()
            self.spin.setDecimals(self._decimals)
            self.spin.setRange(self._minimum, self._maximum)
            self.spin.setSingleStep(self._step)
        else:
            self.spin = QSpinBox()
            self.spin.setRange(int(self._minimum), int(self._maximum))
            self.spin.setSingleStep(int(self._step))
        self.spin.setAccelerated(True)
        self.spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin.setFrame(False)
        self.spin.setMinimumWidth(30)
        self.spin.setMaximumWidth(40)
        self.spin.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.spin.setStyleSheet("background: transparent; border: none; padding: 0 2px;")

        layout.addStretch(1)
        layout.addWidget(self.spin, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.slider, 0)

        self.slider.valueChanged.connect(self._sync_from_slider)
        self.spin.valueChanged.connect(self._sync_from_spin)

    def _slider_to_value(self, index: int) -> float:
        value = self._minimum + (index * self._step)
        return round(value, self._decimals) if self._decimals > 0 else int(round(value))

    def _value_to_slider(self, value: float) -> int:
        value = min(self._maximum, max(self._minimum, float(value)))
        return int(round((value - self._minimum) / self._step))

    def _sync_from_slider(self, index: int) -> None:
        value = self._slider_to_value(index)
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self.valueChanged.emit(float(value))

    def _sync_from_spin(self, value) -> None:
        numeric = float(value)
        slider_value = self._value_to_slider(numeric)
        self.slider.blockSignals(True)
        self.slider.setValue(slider_value)
        self.slider.blockSignals(False)
        self.valueChanged.emit(float(numeric))

    def value(self):
        return round(float(self.spin.value()), self._decimals) if self._decimals > 0 else int(self.spin.value())

    def setValue(self, value: float) -> None:
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(value)
        self.slider.setValue(self._value_to_slider(value))
        self.slider.blockSignals(False)
        self.spin.blockSignals(False)



class BorderTitlePanel(QWidget):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("boxedPanel")
        self._radius = 16
        self._bg_color = QColor('#202020')
        self._border_color = QColor('#2f6fcb')

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("panelTitle")
        self._title_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._body = QWidget(self)
        self._body.setObjectName("boxedPanelBody")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(14, 12, 14, 14)
        self._body_layout.setSpacing(10)

    def bodyLayout(self) -> QVBoxLayout:
        return self._body_layout

    def titleLabel(self) -> QLabel:
        return self._title_label

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        margin_x = 16
        title_size = self._title_label.sizeHint()
        title_h = max(22, title_size.height())
        title_w = min(self.width() - 2 * margin_x, title_size.width() + 4)
        self._title_label.setGeometry(margin_x, 0, max(0, title_w), title_h)
        top_offset = max(10, title_h // 2 + 2)
        self._body.setGeometry(0, top_offset, self.width(), max(0, self.height() - top_offset))

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        title_h = self._title_label.height()
        top_offset = max(10, title_h // 2 + 2)
        rect = QRectF(0.5, top_offset + 0.5, self.width() - 1.0, self.height() - top_offset - 1.0)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(rect, self._radius, self._radius)

        pen = QPen(self._border_color, 1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        gap = self._title_label.geometry().adjusted(-2, 0, 2, 0)
        cutout = QRectF(gap.left(), top_offset - 1, gap.width(), 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRect(cutout)

        painter.end()



class SettingsWindow(QMainWindow):
    export_filtered_requested = Signal()
    copy_ip_requested = Signal(str)
    copy_local_ip_requested = Signal(str)
    config_edited = Signal()
    test_online_popup_requested = Signal()
    test_offline_popup_requested = Signal()
    test_ip_popup_requested = Signal()
    daily_report_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.resize(1420, 920)
        self.setMinimumSize(1180, 760)
        self.setMouseTracking(True)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self._all_events: list[dict] = []
        self._current_ip = ""
        self._current_local_ip = ""
        self._icon_labels: list[QLabel] = []

        self._resize_margin = 7
        self._resize_widgets: list[QWidget] = []
        self._resize_edges: set[str] = set()
        self._resizing = False
        self._resize_start_pos: QPoint | None = None
        self._resize_start_geometry: QRect | None = None

        outer = QWidget(self)
        outer.setObjectName("outerWindow")
        self.setCentralWidget(outer)
        outer.setMouseTracking(True)
        outer.installEventFilter(self)
        self.installEventFilter(self)
        shell = QVBoxLayout(outer)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.window_frame = QFrame()
        self.window_frame.setObjectName("windowFrame")
        frame_layout = QVBoxLayout(self.window_frame)
        frame_layout.setContentsMargins(12, 10, 12, 12)
        frame_layout.setSpacing(10)
        shell.addWidget(self.window_frame)

        self.title_bar = TitleBar(self)
        self.title_bar.installEventFilter(self)
        frame_layout.addWidget(self.title_bar)

        overview_row = QHBoxLayout()
        overview_row.setSpacing(12)
        self.card_status_value = self._create_status_card(overview_row, icon_file="wifi_icon.png", stretch=1)
        self.ip_card = self._create_ip_card(overview_row, "IP-Status", "-", icon_file="globe_icon.png", stretch=1)
        self.card_measurement_value = self._create_measurement_card(overview_row, icon_file="speed_icon.png", stretch=2)
        frame_layout.addLayout(overview_row)

        self.tabs = QTabWidget(self)
        frame_layout.addWidget(self.tabs, 1)

        self._build_home_tab()
        self._build_thresholds_tab()
        self._build_log_tab()

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.btn_reload = QPushButton("Neu laden"); self.btn_reload.setObjectName("btnSecondary")
        self.btn_check_now = QPushButton("Verbindung prüfen"); self.btn_check_now.setObjectName("btnSuccess")
        self.btn_ip_now = QPushButton("IP prüfen"); self.btn_ip_now.setObjectName("btnInfo")
        self.btn_speed_now = QPushButton("Speedtest ausführen"); self.btn_speed_now.setObjectName("btnAccent")
        self.btn_open_logs = QPushButton("Logordner"); self.btn_open_logs.setObjectName("btnSecondary")
        for btn in [self.btn_reload, self.btn_check_now, self.btn_ip_now, self.btn_speed_now, self.btn_open_logs]:
            button_row.addWidget(btn)
        self._set_button_icon(self.btn_reload, "reload_icon.png", 24)
        self._set_button_icon(self.btn_check_now, "wifi_icon.png", 24)
        self._set_button_icon(self.btn_ip_now, "globe_icon.png", 24)
        self._set_button_icon(self.btn_speed_now, "speed_icon.png", 24)
        self._set_button_icon(self.btn_open_logs, "folder_icon.png", 24)
        frame_layout.addLayout(button_row)

        self.status_bar = QStatusBar(self)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.installEventFilter(self)
        self.setStatusBar(self.status_bar)
        self.lbl_next_checks = QLabel("Nächste Prüfungen: -")
        self.lbl_next_checks.setObjectName("statusMetaLabel")
        self.lbl_current_action = QLabel("Aktivität: Bereit")
        self.lbl_current_action.setObjectName("statusActionLabel")
        self.lbl_version = QLabel(APP_VERSION)
        self.lbl_version.setObjectName("statusVersionLabel")
        self.status_meta_container = QWidget(self)
        self.status_meta_container.setObjectName("statusMetaContainer")
        status_meta_layout = QHBoxLayout(self.status_meta_container)
        status_meta_layout.setContentsMargins(0, 0, 0, 0)
        status_meta_layout.setSpacing(6)
        status_meta_layout.addWidget(self.lbl_next_checks)
        status_meta_layout.addWidget(self.lbl_current_action)
        status_meta_layout.addStretch(1)
        self.status_bar.addPermanentWidget(self.status_meta_container, 1)
        self.status_bar.addPermanentWidget(self.lbl_version)

        self.cmb_event_filter.currentTextChanged.connect(self._refresh_event_views)
        self.btn_export_events.clicked.connect(self.export_filtered_requested.emit)
        self.btn_copy_ip.clicked.connect(self._emit_copy_ip)
        self.btn_copy_local_ip.clicked.connect(self._emit_copy_local_ip)
        self.btn_test_popup_online.clicked.connect(self.test_online_popup_requested.emit)
        self.btn_test_popup_offline.clicked.connect(self.test_offline_popup_requested.emit)
        self.btn_test_popup_ip.clicked.connect(self.test_ip_popup_requested.emit)
        self.btn_show_daily_report.clicked.connect(self._emit_daily_report_request)

        self._status_received_at = datetime.now()
        self._meta_base_connection_seconds: int | None = None
        self._meta_base_ip_seconds: int | None = None
        self._meta_base_speed_seconds: int | None = None
        self._current_action_text = "Bereit"
        self._last_status_payload: dict = {}
        self._config_loading = False
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(1000)
        self._live_timer.timeout.connect(self._tick_live_ui)
        self._live_timer.start()
        self._wire_auto_save_controls()
        self._install_resize_tracking()

        self._apply_styles()


    def _install_resize_tracking(self) -> None:
        widgets = [self, self.centralWidget(), getattr(self, "title_bar", None), getattr(self, "status_bar", None)]
        central = self.centralWidget()
        if isinstance(central, QWidget):
            widgets.extend(central.findChildren(QWidget))
        seen: set[int] = set()
        tracked: list[QWidget] = []
        for widget in widgets:
            if not isinstance(widget, QWidget):
                continue
            wid = id(widget)
            if wid in seen:
                continue
            seen.add(wid)
            widget.setMouseTracking(True)
            widget.installEventFilter(self)
            tracked.append(widget)
        self._resize_widgets = tracked

    def eventFilter(self, watched: QObject, event):  # type: ignore[override]
        watched_is_widget = isinstance(watched, QWidget)
        if watched_is_widget and watched.window() is self:
            if event.type() == QEvent.MouseMove:
                local_pos = self._event_pos_in_window(watched, event)
                if local_pos is not None:
                    if self._resizing:
                        self._perform_resize(event.globalPosition().toPoint())
                        return True
                    if not self.isMaximized():
                        self._update_resize_cursor(local_pos)
            elif event.type() == QEvent.MouseButtonPress:
                local_pos = self._event_pos_in_window(watched, event)
                if (
                    local_pos is not None
                    and event.button() == Qt.LeftButton
                    and not self.isMaximized()
                ):
                    edges = self._hit_test_edges(local_pos)
                    if edges:
                        self._resizing = True
                        self._resize_edges = edges
                        self._resize_start_pos = event.globalPosition().toPoint()
                        self._resize_start_geometry = self.geometry()
                        self._set_resize_cursor_for_edges(edges)
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                if self._resizing:
                    self._resizing = False
                    self._resize_edges = set()
                    self._resize_start_pos = None
                    self._resize_start_geometry = None
                    self._clear_resize_cursors()
                    return True
            elif event.type() == QEvent.Leave and not self._resizing:
                if self.underMouse():
                    pass
                else:
                    self._clear_resize_cursors()
        return super().eventFilter(watched, event)

    def _event_pos_in_window(self, watched: QObject, event) -> QPoint | None:
        if not hasattr(event, "position"):
            return None
        point = event.position().toPoint()
        if watched is self:
            return point
        if isinstance(watched, QWidget):
            return watched.mapTo(self, point)
        return None

    def _hit_test_edges(self, pos: QPoint) -> set[str]:
        if self.isMaximized():
            return set()
        rect = self.rect()
        margin = self._resize_margin
        edges: set[str] = set()
        if pos.x() <= margin:
            edges.add("left")
        elif pos.x() >= rect.width() - margin:
            edges.add("right")
        if pos.y() <= margin:
            edges.add("top")
        elif pos.y() >= rect.height() - margin:
            edges.add("bottom")
        return edges

    def _update_resize_cursor(self, pos: QPoint) -> None:
        edges = self._hit_test_edges(pos)
        self._resize_edges = edges
        self._set_resize_cursor_for_edges(edges)

    def _set_resize_cursor_for_edges(self, edges: set[str]) -> None:
        if edges in ({"left", "top"}, {"right", "bottom"}):
            cursor = Qt.SizeFDiagCursor
        elif edges in ({"right", "top"}, {"left", "bottom"}):
            cursor = Qt.SizeBDiagCursor
        elif edges & {"left", "right"}:
            cursor = Qt.SizeHorCursor
        elif edges & {"top", "bottom"}:
            cursor = Qt.SizeVerCursor
        else:
            cursor = None

        widgets = self._resize_widgets or [self, self.centralWidget(), getattr(self, "status_bar", None), getattr(self, "title_bar", None)]
        for widget in widgets:
            if isinstance(widget, QWidget):
                if cursor is None:
                    widget.unsetCursor()
                else:
                    widget.setCursor(cursor)

    def _clear_resize_cursors(self) -> None:
        self._set_resize_cursor_for_edges(set())

    def _perform_resize(self, global_pos: QPoint) -> None:
        if not self._resize_start_pos or not self._resize_start_geometry:
            return
        delta = global_pos - self._resize_start_pos
        geom = QRect(self._resize_start_geometry)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        if "left" in self._resize_edges:
            new_left = geom.left() + delta.x()
            max_left = geom.right() - min_w + 1
            geom.setLeft(min(new_left, max_left))
        if "right" in self._resize_edges:
            new_width = max(min_w, geom.width() + delta.x())
            geom.setWidth(new_width)
        if "top" in self._resize_edges:
            new_top = geom.top() + delta.y()
            max_top = geom.bottom() - min_h + 1
            geom.setTop(min(new_top, max_top))
        if "bottom" in self._resize_edges:
            new_height = max(min_h, geom.height() + delta.y())
            geom.setHeight(new_height)

        self.setGeometry(geom)

    def _asset_path(self, filename: str) -> Path:
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(Path(meipass) / "assets" / filename)
            candidates.append(Path(sys.executable).resolve().parent / "assets" / filename)
        candidates.append(Path(__file__).resolve().parents[3] / "assets" / filename)
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _asset_url(self, filename: str) -> str:
        candidate = self._asset_path(filename)
        return candidate.resolve().as_uri() if candidate.exists() else filename

    def _set_icon_label(self, label: QLabel, filename: str, size: int = 28) -> None:
        icon_path = self._asset_path(filename)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix)
            label.setFixedSize(size, size)
        else:
            label.setText("•")
            label.setFixedSize(size, size)

    def _set_button_icon(self, button: QPushButton, filename: str, size: int = 26) -> None:
        icon_path = self._asset_path(filename)
        if icon_path.exists():
            button.setIcon(QIcon(str(icon_path)))
            button.setIconSize(QSize(size, size))

    def _right_aligned_field(self, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        layout.addWidget(widget, 0, Qt.AlignRight | Qt.AlignVCenter)
        return container

    def _build_home_tab(self) -> None:
        page = QWidget()
        page.setObjectName("tabPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.home_content_frame = QFrame(); self.home_content_frame.setObjectName("homeContentFrame")
        content_layout = QHBoxLayout(self.home_content_frame)
        content_layout.setContentsMargins(8, 10, 8, 8)
        content_layout.setSpacing(4)
        layout.addWidget(self.home_content_frame)

        self.left_panel_card = BorderTitlePanel("Allgemeine Einstellungen")
        self.left_panel_card.setMinimumWidth(450)
        self.left_panel_card.setMaximumWidth(450)
        left_outer = self.left_panel_card.bodyLayout()
        self.left_panel_title = self.left_panel_card.titleLabel()

        self.settings_scroll = QScrollArea(); self.settings_scroll.setObjectName("settingsScrollArea")
        self.settings_scroll.setWidgetResizable(True); self.settings_scroll.setFrameShape(QFrame.NoFrame)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll.viewport().setObjectName("settingsScrollViewport")
        scroll_content = QWidget(); scroll_content.setObjectName("settingsScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(3)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(3)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.chk_start_windows = ToggleSwitch()
        self.chk_start_minimized = ToggleSwitch()
        self.chk_conn_enabled = ToggleSwitch()
        self.spin_conn_seconds = SliderSpinField(0.5, 60.0, step=0.5, decimals=1)
        self.chk_ip_enabled = ToggleSwitch()
        self.spin_ip_seconds = SliderSpinField(1, 30, step=1, decimals=0)
        self.chk_speed_enabled = ToggleSwitch()
        self.spin_speed_minutes = SliderSpinField(1, 60, step=1, decimals=0)
        self.chk_notify_enabled = ToggleSwitch()
        self.chk_notify_windows = ToggleSwitch()
        self.chk_notify_app = ToggleSwitch()
        self.chk_notify_online = ToggleSwitch()
        self.chk_notify_offline = ToggleSwitch()
        self.chk_notify_ip = ToggleSwitch()
        self.chk_notify_speed = ToggleSwitch()
        self.spin_notify_cooldown = SliderSpinField(0, 60, step=1, decimals=0)

        for label, widget in [
            ("Programm bei Windows-Start ausführen", self._right_aligned_field(self.chk_start_windows)),
            ("Beim Start minimieren", self._right_aligned_field(self.chk_start_minimized)),
            ("Verbindungsüberwachung", self._right_aligned_field(self.chk_conn_enabled)),
            ("Prüfintervall Verbindungen (Sek.)", self.spin_conn_seconds),
            ("IP-Überwachung", self._right_aligned_field(self.chk_ip_enabled)),
            ("Prüfintervall IP (Sek.)", self.spin_ip_seconds),
            ("Speedtest", self._right_aligned_field(self.chk_speed_enabled)),
            ("Speedtest-Intervall (Min.)", self.spin_speed_minutes),
            ("Pop-up-Benachrichtigungen", self._right_aligned_field(self.chk_notify_enabled)),
            ("Windows-Popups", self._right_aligned_field(self.chk_notify_windows)),
            ("App-eigene Pop-ups", self._right_aligned_field(self.chk_notify_app)),
            ("Popup bei Online", self._right_aligned_field(self.chk_notify_online)),
            ("Popup bei Offline", self._right_aligned_field(self.chk_notify_offline)),
            ("Popup bei IP-Wechsel", self._right_aligned_field(self.chk_notify_ip)),
            ("Pop-up bei Speedwarnung", self._right_aligned_field(self.chk_notify_speed)),
            ("Cooldown (Sek.)", self.spin_notify_cooldown),
        ]:
            form.addRow(label, widget)
        scroll_layout.addLayout(form)

        report_title = QLabel("Tagesbericht")
        report_title.setObjectName("subSectionTitle")
        scroll_layout.addWidget(report_title)
        report_layout = QHBoxLayout()
        self.date_daily_report = QDateEdit()
        self.date_daily_report.setCalendarPopup(True)
        self.date_daily_report.setDisplayFormat("dd.MM.yyyy")
        self.date_daily_report.setDate(QDate.currentDate())
        self.btn_show_daily_report = QPushButton("Tagesbericht anzeigen")
        self.btn_show_daily_report.setObjectName("btnInfo")
        report_layout.addWidget(self.date_daily_report, 1)
        report_layout.addWidget(self.btn_show_daily_report, 1)
        scroll_layout.addLayout(report_layout)

        test_title = QLabel("Pop-up-Benachrichtigungen testen")
        test_title.setObjectName("subSectionTitle")
        scroll_layout.addWidget(test_title)
        test_layout = QHBoxLayout()
        self.btn_test_popup_online = QPushButton("Online"); self.btn_test_popup_online.setObjectName("btnSuccessSmall")
        self.btn_test_popup_offline = QPushButton("Offline"); self.btn_test_popup_offline.setObjectName("btnWarningSmall")
        self.btn_test_popup_ip = QPushButton("IP-Änderung"); self.btn_test_popup_ip.setObjectName("btnInfoSmall")
        test_layout.addWidget(self.btn_test_popup_online)
        test_layout.addWidget(self.btn_test_popup_offline)
        test_layout.addWidget(self.btn_test_popup_ip)
        scroll_layout.addLayout(test_layout)
        scroll_layout.addStretch(1)

        self.settings_scroll.setWidget(scroll_content)
        left_outer.addWidget(self.settings_scroll, 1)
        content_layout.addWidget(self.left_panel_card, 0)

        self.right_panel_card = BorderTitlePanel("Aktuelle Ereignisse")
        right_outer = self.right_panel_card.bodyLayout()

        header_top = QHBoxLayout()
        header_top.setContentsMargins(0, 0, 0, 0)
        header_top.setSpacing(12)
        self.right_panel_title = self.right_panel_card.titleLabel()

        self.lbl_filter_from = QLabel("Von:")
        self.lbl_filter_from.setObjectName("filterLabel")
        self.date_filter_from = QDateEdit()
        self.date_filter_from.setCalendarPopup(True)
        self.date_filter_from.setDisplayFormat("dd.MM.yyyy")
        self.date_filter_from.setDate(QDate.currentDate().addDays(-7))
        self.date_filter_from.setMinimumWidth(124)

        self.lbl_filter_to = QLabel("Bis:")
        self.lbl_filter_to.setObjectName("filterLabel")
        self.date_filter_to = QDateEdit()
        self.date_filter_to.setCalendarPopup(True)
        self.date_filter_to.setDisplayFormat("dd.MM.yyyy")
        self.date_filter_to.setDate(QDate.currentDate())
        self.date_filter_to.setMinimumWidth(124)

        self.lbl_filter_quick = QLabel("Zeitraum:")
        self.lbl_filter_quick.setObjectName("filterLabel")
        self.cmb_date_quick = QComboBox()
        self.cmb_date_quick.addItems(["Gesamter Zeitraum", "Letzte 24 Stunden", "Letzte Woche", "Letzter Monat", "Benutzerdefiniert"])
        self.cmb_date_quick.setMinimumWidth(180)

        left_filter_wrap = QHBoxLayout()
        left_filter_wrap.setContentsMargins(0, 0, 0, 0)
        left_filter_wrap.setSpacing(10)

        from_box = QVBoxLayout()
        from_box.setContentsMargins(0, 0, 0, 0)
        from_box.setSpacing(4)
        from_box.addWidget(self.lbl_filter_from)
        from_box.addWidget(self.date_filter_from)

        to_box = QVBoxLayout()
        to_box.setContentsMargins(0, 0, 0, 0)
        to_box.setSpacing(4)
        to_box.addWidget(self.lbl_filter_to)
        to_box.addWidget(self.date_filter_to)

        quick_box = QVBoxLayout()
        quick_box.setContentsMargins(0, 0, 0, 0)
        quick_box.setSpacing(4)
        quick_box.addWidget(self.lbl_filter_quick)
        quick_box.addWidget(self.cmb_date_quick)

        left_filter_wrap.addLayout(from_box)
        left_filter_wrap.addLayout(to_box)
        left_filter_wrap.addLayout(quick_box)

        header_top.addLayout(left_filter_wrap)
        header_top.addStretch(1)

        right_tools_wrap = QHBoxLayout()
        right_tools_wrap.setContentsMargins(0, 0, 0, 0)
        right_tools_wrap.setSpacing(8)

        filter_box = QVBoxLayout()
        filter_box.setContentsMargins(0, 0, 0, 0)
        filter_box.setSpacing(4)
        lbl_filter = QLabel("Filter:")
        lbl_filter.setObjectName("filterLabel")
        filter_box.addWidget(lbl_filter)
        self.cmb_event_filter = QComboBox(); self.cmb_event_filter.addItems(["Alle anzeigen", "Verbindungen", "IP-Änderungen", "Speedtests"])
        self.cmb_event_filter.setMinimumWidth(220)
        filter_box.addWidget(self.cmb_event_filter)

        right_tools_wrap.addLayout(filter_box)
        self.btn_export_events = QPushButton("Exportieren"); self.btn_export_events.setObjectName("btnSecondary")
        right_tools_wrap.addWidget(self.btn_export_events, 0, Qt.AlignBottom)

        header_top.addLayout(right_tools_wrap)
        right_outer.addLayout(header_top)

        self.tbl_events = QTableWidget(0, 5)
        self.tbl_events.setHorizontalHeaderLabels(["", "Datum", "Uhrzeit", "Ereignis", "Eintrag"])
        self.tbl_events.verticalHeader().setVisible(False)
        self.tbl_events.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_events.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_events.setAlternatingRowColors(True)
        self.tbl_events.setShowGrid(False)
        self.tbl_events.setWordWrap(False)
        self.tbl_events.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tbl_events.setColumnWidth(0, 36)
        self.tbl_events.setColumnWidth(1, 118)
        self.tbl_events.setColumnWidth(2, 88)
        self.tbl_events.setColumnWidth(3, 128)
        self.tbl_events.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        right_outer.addWidget(self.tbl_events, 1)
        content_layout.addWidget(self.right_panel_card, 2)

        self.tabs.addTab(page, "Startseite")

    def _build_thresholds_tab(self) -> None:
        page = QWidget()
        page.setObjectName("tabPage")
        layout = QGridLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        grp_provider = QGroupBox("Anbieter / Sollwerte")
        provider_layout = QFormLayout(grp_provider)
        self.spin_provider_down = QSpinBox(); self.spin_provider_down.setRange(0, 100000)
        self.spin_provider_up = QSpinBox(); self.spin_provider_up.setRange(0, 100000)
        provider_layout.addRow("Anbieter-Download (Mbit/s)", self.spin_provider_down)
        provider_layout.addRow("Anbieter-Upload (Mbit/s)", self.spin_provider_up)

        grp_speed = QGroupBox("Warnschwellen")
        speed_layout = QFormLayout(grp_speed)
        self.spin_warn_down = QSpinBox(); self.spin_warn_down.setRange(0, 100000)
        self.spin_warn_up = QSpinBox(); self.spin_warn_up.setRange(0, 100000)
        self.spin_warn_ping = QSpinBox(); self.spin_warn_ping.setRange(0, 100000)
        speed_layout.addRow("Warnung Download unter (Mbit/s)", self.spin_warn_down)
        speed_layout.addRow("Warnung Upload unter (Mbit/s)", self.spin_warn_up)
        speed_layout.addRow("Warnung Ping über (ms)", self.spin_warn_ping)

        grp_logs = QGroupBox("Dateigrenzen")
        log_layout = QFormLayout(grp_logs)
        self.spin_log_size = QSpinBox(); self.spin_log_size.setRange(100_000, 100_000_000); self.spin_log_size.setSingleStep(100_000)
        self.spin_log_backups = QSpinBox(); self.spin_log_backups.setRange(1, 20)
        log_layout.addRow("Max. Dateigröße Verlauf (Bytes)", self.spin_log_size)
        log_layout.addRow("Interne Log-Backups", self.spin_log_backups)

        layout.addWidget(grp_provider, 0, 0)
        layout.addWidget(grp_speed, 0, 1)
        layout.addWidget(grp_logs, 1, 0, 1, 2)
        self.tabs.addTab(page, "🛡  Grenzwerte")

    def _build_log_tab(self) -> None:
        page = QWidget()
        page.setObjectName("tabPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        self.txt_config_path = QLineEdit(); self.txt_config_path.setReadOnly(True)
        self.txt_log_path = QLineEdit(); self.txt_log_path.setReadOnly(True)
        self.txt_event_log = QTextEdit(); self.txt_event_log.setReadOnly(True); self.txt_event_log.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(QLabel("Konfigurationsdatei"))
        layout.addWidget(self.txt_config_path)
        layout.addWidget(QLabel("Interne Logdatei"))
        layout.addWidget(self.txt_log_path)
        layout.addWidget(QLabel("Protokoll / Verlauf / Tagesbericht"))
        layout.addWidget(self.txt_event_log, 1)
        self.tabs.addTab(page, "📄  Logs")

    def _apply_styles(self) -> None:
        arrow_url = self._asset_url("white_down_arrow.svg")

        stylesheet = """
            QMainWindow, QWidget#outerWindow {
                background: #1c1c1c;
                color: #e6eef9;
                font-size: 15px;
            }
            QFrame#windowFrame {
                background: transparent;
                border: none;
                border-radius: 0px;
            }
            QFrame#homeContentFrame {
                background: transparent;
                border: none;
            }
            QWidget#titleBar { background: transparent; border: none; }
            QLabel#titleLabel { color: #f3f3f3; font-weight: 700; }
            QLabel#titleLogo { background: transparent; }
            QPushButton#titleMinButton, QPushButton#titleMaxButton, QPushButton#titleCloseButton {
                background: transparent;
                color: #dce8f8;
                border: none;
                border-radius: 8px;
                min-height: 30px;
            }
            QPushButton#titleMinButton:hover, QPushButton#titleMaxButton:hover { background: rgba(255,255,255,0.05); }
            QPushButton#titleCloseButton:hover { background: rgba(185,28,28,0.18); }
            QStatusBar {
                color: #c7d2fe;
                background: transparent;
                border-top: 1px solid #3a434d;
            }
            QLabel#statusMetaLabel { color: #c7d2fe; padding-right: 0px; }
            QLabel#statusActionLabel { color: #8ea7c9; padding-left: 2px; padding-right: 10px; }
            QLabel#statusVersionLabel { color: #8ea7c9; min-width: 42px; padding-left: 14px; }
            QFrame#summaryCard {
                background: transparent;
                border: 1px solid #2f6fcb;
                border-radius: 16px;
            }
            QWidget#boxedPanel {
                background: transparent;
                border: none;
            }
            QWidget#boxedPanelBody {
                background: transparent;
                border: none;
            }
            QLabel#panelTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 800;
                padding: 0 2px;
                background: transparent;
            }
            QLabel#summaryTitle { color: #f3f7fd; font-size: 17px; font-weight: 700; }
            QLabel#summaryIcon { color: #60a5fa; font-size: 30px; font-weight: 700; }
            QLabel#summaryHeader { color: #f3f7fd; font-size: 15px; font-weight: 700; }
            QLabel#summaryMeta { color: #cbd5e1; font-size: 13px; }
            QLabel#summaryValue { color: #f3f3f3; font-size: 18px; font-weight: 600; }
            QLabel#sectionTitle, QLabel#subSectionTitle { color: #f3f3f3; font-size: 16px; font-weight: 700; }
            QPushButton#copyButton {
                min-width: 28px; min-height: 28px; max-width: 28px; max-height: 28px;
                padding: 0; border: 1px solid #4a5561;
                background: transparent; border-radius: 8px;
            }
            QPushButton#copyButton:hover { background: rgba(255,255,255,0.05); border-color: #7eb3ff; }
            QPushButton#iconOnlyButton {
                min-width: 28px; min-height: 28px; max-width: 28px; max-height: 28px;
                padding: 0;
                border: none;
                background: transparent;
                border-radius: 8px;
            }
            QPushButton#iconOnlyButton:hover { background: rgba(255,255,255,0.05); }
            QLabel#ipLabel { color: #f3f7fd; font-size: 16px; font-weight: 700; }
            QLabel#ipValue { color: #f3f3f3; font-size: 22px; font-weight: 700; }
            QLabel#inlineValue { color: #f3f3f3; font-size: 22px; font-weight: 700; }
            QLabel#ipSubText { color: #cbd5e1; font-size: 13px; }
            QFrame#ipDivider {
                background: transparent;
                border: none;
                border-top: 1px solid rgba(255,255,255,0.16);
            }
            QTabWidget::pane {
                background: #202020;
                border: 1px solid #46515d;
                border-radius: 12px;
                top: -1px;
                margin-top: -1px;
            }
            QWidget#tabPage {
                background: transparent;
                border: none;
            }
            QTabBar::tab {
                margin-left: 20px;
                padding: 12px 18px;
                background: #2b2b2b;
                color: #d3def0;
                border: 1px solid #46515d;
                border-bottom: none;
                margin-right: 4px;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
            }
            QTabBar::tab:selected {
                background: #202020;
                color: #ffffff;
                font-weight: 700;
                border-color: #46515d;
            }
            QTabBar::tab:hover:!selected { background: #343a43; }
            QScrollArea#settingsScrollArea {
                padding: 0;
                border: none;
                background: transparent;
            }
            QWidget#settingsScrollViewport, QWidget#settingsScrollContent {
                background: #202020;
                border-radius: 12px;
            }
            QGroupBox {
                color: #f3f3f3; font-weight: 700; border: none; border-radius: 0px; margin-top: 8px; padding-top: 12px; background: transparent;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 0px; padding: 0; color: #f3f3f3; background: transparent; }
            QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
                background: #1f1f1f;
                color: #f3f3f3;
                border: 1px solid #4b5662;
                border-radius: 8px;
                padding: 7px;
                selection-background-color: #2f6feb;
            }
            QSpinBox, QDoubleSpinBox {
                padding-right: 2px;
                background: transparent;
                border: none;
            }
            QComboBox::drop-down, QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow, QDateEdit::down-arrow {
                background: transparent;
                border: none;
                image: url("__ARROW_URL__");
                width: 12px;
                height: 8px;
            }
            QComboBox QAbstractItemView {
                background: #1f1f1f;
                color: #f3f3f3;
                border: 1px solid #4b5662;
                selection-background-color: #2f6feb;
            }
            QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
                background: transparent;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow, QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {
                width: 0px;
                height: 0px;
                image: none;
            }
            QLabel {
                background: transparent;
            }
            QPushButton {
                font-size: 16px;
                min-height: 38px;
                padding: 8px 14px;
                background: #2b2b2b;
                color: #f3f3f3;
                border: 1px solid #4a5561;
                border-radius: 10px;
                font-weight: 600;
            }
            QPushButton:hover { background: #333333; border-color: #7eb3ff; }
            QPushButton:pressed { background: #1f1f1f; border-color: #a7c9ff; }
            QLabel#filterLabel { color: #d3def0; font-size: 15px; }
            QPushButton#btnSuccessSmall, QPushButton#btnWarningSmall, QPushButton#btnInfoSmall {
                min-height: 32px; padding: 6px 10px; border-radius: 9px;
            }
            QPushButton#btnSuccessSmall { background: #15803d; border-color: #22c55e; }
            QPushButton#btnSuccessSmall:hover { background: #16a34a; }
            QPushButton#btnWarningSmall { background: #c2410c; border-color: #fb923c; }
            QPushButton#btnWarningSmall:hover { background: #ea580c; }
            QPushButton#btnInfoSmall { background: #1d4ed8; border-color: #60a5fa; }
            QPushButton#btnInfoSmall:hover { background: #2563eb; }
            QHeaderView::section {
                background: #30363d;
                color: #dce8f8;
                border: none;
                border-bottom: 1px solid #46515d;
                padding: 8px 6px;
                font-weight: 700;
            }
            QTableWidget {
                background: #1f1f1f;
                alternate-background-color: #242424;
                border: 1px solid #46515d;
                border-radius: 12px;
                gridline-color: transparent;
            }
            QSlider#rangeSlider::groove:horizontal {
                height: 6px;
                background: #2d3742;
                border-radius: 3px;
            }
            QSlider#rangeSlider::handle:horizontal {
                width: 6px;
                margin: -2px 0;
                background: #60a5fa;
                border: 1px solid #93c5fd;
                border-radius: 4px;
            }
            QSlider#rangeSlider::sub-page:horizontal {
                background: #2f6feb;
                border-radius: 3px;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid rgba(255,255,255,0.03);
            }
        """
        stylesheet = stylesheet.replace("__ARROW_URL__", arrow_url)
        self.setStyleSheet(stylesheet)

    def _create_summary_card(self, parent_layout: QHBoxLayout, title: str, value: str, icon: str | None = None, icon_file: str | None = None, stretch: int = 1) -> QLabel:
        card = QFrame(); card.setObjectName("summaryCard")
        layout = QVBoxLayout(card); layout.setContentsMargins(18, 18, 18, 14); layout.setSpacing(6)
        top = QHBoxLayout()
        lbl_title = QLabel(title); lbl_title.setObjectName("summaryTitle")
        lbl_icon = QLabel(); lbl_icon.setObjectName("summaryIcon")
        if icon_file:
            self._set_icon_label(lbl_icon, icon_file, 56)
        else:
            lbl_icon.setText(icon or "")
        top.addWidget(lbl_title); top.addStretch(1); top.addWidget(lbl_icon)
        lbl_value = QLabel(value); lbl_value.setObjectName("summaryValue"); lbl_value.setWordWrap(True); lbl_value.setTextFormat(Qt.RichText)
        layout.addLayout(top); layout.addWidget(lbl_value); layout.addStretch(1)
        parent_layout.addWidget(card, stretch)
        return lbl_value

    def _create_status_card(self, parent_layout: QHBoxLayout, icon_file: str | None = None, stretch: int = 1) -> QLabel:
        card = QFrame(); card.setObjectName("summaryCard")
        layout = QVBoxLayout(card); layout.setContentsMargins(18, 18, 18, 14); layout.setSpacing(2)
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0); top.setSpacing(0)
        self.lbl_status_title = QLabel("Online")
        self.lbl_status_title.setObjectName("summaryTitle")
        top.addWidget(self.lbl_status_title, 0, Qt.AlignVCenter | Qt.AlignLeft)
        top.addStretch(1)
        lbl_icon = QLabel(); lbl_icon.setObjectName("summaryIcon")
        if icon_file:
            self._set_icon_label(lbl_icon, icon_file, 56)
        top.addWidget(lbl_icon, 0, Qt.AlignTop | Qt.AlignRight)
        layout.addLayout(top)
        self.card_status_value = QLabel("-")
        self.card_status_value.setObjectName("summaryValue")
        self.card_status_value.setWordWrap(True)
        self.card_status_value.setTextFormat(Qt.RichText)
        layout.addStretch(1)
        layout.addWidget(self.card_status_value, 0, Qt.AlignVCenter)
        layout.addStretch(2)
        parent_layout.addWidget(card, stretch)
        return self.card_status_value

    def _create_measurement_card(self, parent_layout: QHBoxLayout, icon_file: str | None = None, stretch: int = 1) -> QLabel:
        card = QFrame(); card.setObjectName("summaryCard")
        layout = QVBoxLayout(card); layout.setContentsMargins(18, 18, 18, 14); layout.setSpacing(6)
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0); top.setSpacing(0)
        self.lbl_measurement_title = QLabel("Speed-Ergebnisse")
        self.lbl_measurement_title.setObjectName("summaryTitle")
        top.addWidget(self.lbl_measurement_title, 0, Qt.AlignVCenter | Qt.AlignLeft)
        top.addStretch(1)
        lbl_icon = QLabel(); lbl_icon.setObjectName("summaryIcon")
        if icon_file:
            self._set_icon_label(lbl_icon, icon_file, 56)
        top.addWidget(lbl_icon, 0, Qt.AlignTop | Qt.AlignRight)
        layout.addLayout(top)

        self.measure_grid = QGridLayout()
        self.measure_grid.setContentsMargins(0, 8, 0, 0)
        self.measure_grid.setHorizontalSpacing(24)
        self.measure_grid.setVerticalSpacing(2)
        self.measure_grid.setColumnStretch(0, 2)
        self.measure_grid.setColumnStretch(1, 2)
        self.measure_grid.setColumnStretch(2, 1)
        self.measure_grid.setColumnMinimumWidth(1, 210)

        self.lbl_down_block = QLabel("Noch kein Ergebnis")
        self.lbl_down_block.setObjectName("summaryValue")
        self.lbl_down_block.setTextFormat(Qt.RichText)
        self.lbl_down_block.setWordWrap(True)
        self.lbl_avg_down_block = QLabel("")
        self.lbl_avg_down_block.setObjectName("summaryValue")
        self.lbl_avg_down_block.setTextFormat(Qt.RichText)
        self.lbl_avg_down_block.setWordWrap(True)
        self.lbl_ping_placeholder = QLabel("")
        self.lbl_ping_placeholder.setObjectName("summaryValue")

        self.measure_grid.addWidget(self.lbl_down_block, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.measure_grid.addWidget(self.lbl_avg_down_block, 0, 1, Qt.AlignLeft | Qt.AlignVCenter)
        self.measure_grid.addWidget(self.lbl_ping_placeholder, 0, 2, Qt.AlignLeft | Qt.AlignVCenter)

        divider_row = QHBoxLayout(); divider_row.setContentsMargins(0, 6, 0, 6)
        divider_row.addSpacing(8)
        self.measure_divider = QFrame(); self.measure_divider.setObjectName("ipDivider"); self.measure_divider.setFixedHeight(1)
        divider_row.addWidget(self.measure_divider, 1)
        divider_row.addSpacing(8)
        self.measure_grid.addLayout(divider_row, 1, 0, 1, 3)

        self.lbl_up_block = QLabel("")
        self.lbl_up_block.setObjectName("summaryValue")
        self.lbl_up_block.setTextFormat(Qt.RichText)
        self.lbl_up_block.setWordWrap(True)
        self.lbl_avg_up_block = QLabel("")
        self.lbl_avg_up_block.setObjectName("summaryValue")
        self.lbl_avg_up_block.setTextFormat(Qt.RichText)
        self.lbl_avg_up_block.setWordWrap(True)
        self.lbl_ping_block = QLabel("")
        self.lbl_ping_block.setObjectName("summaryValue")
        self.lbl_ping_block.setTextFormat(Qt.RichText)
        self.lbl_ping_block.setWordWrap(True)

        self.measure_grid.addWidget(self.lbl_up_block, 2, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.measure_grid.addWidget(self.lbl_avg_up_block, 2, 1, Qt.AlignLeft | Qt.AlignVCenter)
        self.measure_grid.addWidget(self.lbl_ping_block, 2, 2, Qt.AlignLeft | Qt.AlignVCenter)

        layout.addStretch(1)
        layout.addLayout(self.measure_grid)
        layout.addStretch(2)
        parent_layout.addWidget(card, stretch)
        return self.lbl_down_block

    def _create_ip_card(self, parent_layout: QHBoxLayout, title: str, value: str, icon: str | None = None, icon_file: str | None = None, stretch: int = 1):
        card = QFrame(); card.setObjectName("summaryCard")
        layout = QVBoxLayout(card); layout.setContentsMargins(18, 18, 18, 14); layout.setSpacing(5)

        public_header_row = QHBoxLayout(); public_header_row.setContentsMargins(0, 0, 0, 0); public_header_row.setSpacing(8)
        self.lbl_public_label = QLabel("Öffentliche IP"); self.lbl_public_label.setObjectName("ipLabel")
        public_header_row.addWidget(self.lbl_public_label, 0, Qt.AlignVCenter)
        public_header_row.addStretch(1)
        lbl_icon = QLabel(); lbl_icon.setObjectName("summaryIcon")
        if icon_file:
            self._set_icon_label(lbl_icon, icon_file, 56)
        else:
            lbl_icon.setText(icon or "")
        public_header_row.addWidget(lbl_icon, 0, Qt.AlignTop | Qt.AlignRight)
        layout.addLayout(public_header_row)

        layout.addSpacing(2)
        public_value_row = QHBoxLayout(); public_value_row.setSpacing(2)
        self.lbl_public_value = QLabel("-"); self.lbl_public_value.setObjectName("inlineValue")
        self.btn_copy_ip = QPushButton("")
        self.btn_copy_ip.setObjectName("iconOnlyButton")
        self.btn_copy_ip.setToolTip("Öffentliche IP kopieren")
        self._set_button_icon(self.btn_copy_ip, "copy_icon.png", 24)
        public_value_row.addWidget(self.lbl_public_value, 0, Qt.AlignLeft)
        public_value_row.addWidget(self.btn_copy_ip, 0, Qt.AlignVCenter)
        public_value_row.addStretch(1)
        self.lbl_public_changes = QLabel("Erkannte Änderungen heute: 0"); self.lbl_public_changes.setObjectName("ipSubText")
        layout.addLayout(public_value_row)
        layout.addWidget(self.lbl_public_changes)

        divider_row = QHBoxLayout(); divider_row.setContentsMargins(0, 6, 0, 6)
        divider_row.addSpacing(8)
        divider = QFrame(); divider.setObjectName("ipDivider"); divider.setFixedHeight(1)
        divider_row.addWidget(divider, 1)
        divider_row.addSpacing(8)
        layout.addLayout(divider_row)

        self.lbl_local_label = QLabel("Lokale IP"); self.lbl_local_label.setObjectName("ipLabel")
        layout.addWidget(self.lbl_local_label)
        layout.addSpacing(2)
        local_value_row = QHBoxLayout(); local_value_row.setSpacing(2)
        self.lbl_local_value = QLabel("-"); self.lbl_local_value.setObjectName("inlineValue")
        self.btn_copy_local_ip = QPushButton("")
        self.btn_copy_local_ip.setObjectName("iconOnlyButton")
        self.btn_copy_local_ip.setToolTip("Lokale IP kopieren")
        self._set_button_icon(self.btn_copy_local_ip, "copy_icon.png", 24)
        local_value_row.addWidget(self.lbl_local_value, 0, Qt.AlignLeft)
        local_value_row.addWidget(self.btn_copy_local_ip, 0, Qt.AlignVCenter)
        local_value_row.addStretch(1)
        self.lbl_local_changes = QLabel("Erkannte Änderungen heute: 0"); self.lbl_local_changes.setObjectName("ipSubText")
        layout.addLayout(local_value_row)
        layout.addWidget(self.lbl_local_changes)

        layout.addStretch(2)
        parent_layout.addWidget(card, stretch)
        return card

    def _speed_metric_html(self, label: str, value: float, percent: float, unit: str = "Mbit/s") -> str:
        return (
            f"<span style='color:#cbd5e1; font-size:14px; font-weight:700;'>{html.escape(label)}</span><br>"
            f"<span style='color:{self._percent_color(percent)}; font-size:24px; font-weight:800;'>{value:.2f}</span> "
            f"<span style='color:#ffffff'>{html.escape(unit)}</span> "
            f"<span style='color:{self._percent_color(percent)}; font-weight:800;'>{percent:.0f}%</span>"
        )

    def _ping_metric_html(self, ping_ms: float) -> str:
        return (
            "<span style='color:#cbd5e1; font-size:14px; font-weight:700;'>Ping</span><br>"
            f"<span style='color:{self._ping_color(ping_ms)}; font-size:22px; font-weight:800;'>{ping_ms:.0f}</span> "
            "<span style='color:#ffffff'>ms</span>"
        )

    def _apply_quick_date_range(self) -> None:
        if not hasattr(self, 'cmb_date_quick'):
            return
        text = self.cmb_date_quick.currentText()
        today = QDate.currentDate()
        self.date_filter_from.blockSignals(True)
        self.date_filter_to.blockSignals(True)
        if text == "Gesamter Zeitraum":
            self.date_filter_from.setDate(today.addYears(-5))
            self.date_filter_to.setDate(today)
        elif text == "Letzte 24 Stunden":
            self.date_filter_from.setDate(today.addDays(-1))
            self.date_filter_to.setDate(today)
        elif text == "Letzte Woche":
            self.date_filter_from.setDate(today.addDays(-7))
            self.date_filter_to.setDate(today)
        elif text == "Letzter Monat":
            self.date_filter_from.setDate(today.addMonths(-1))
            self.date_filter_to.setDate(today)
        self.date_filter_from.blockSignals(False)
        self.date_filter_to.blockSignals(False)
        self._refresh_event_views()

    def _event_in_selected_range(self, event: dict) -> bool:
        ts = str(event.get('timestamp', ''))
        try:
            event_dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return True
        selected = self.cmb_date_quick.currentText() if hasattr(self, 'cmb_date_quick') else 'Gesamter Zeitraum'
        if selected == 'Letzte 24 Stunden':
            return event_dt >= datetime.now() - timedelta(hours=24)
        if selected == 'Letzte Woche':
            return event_dt >= datetime.now() - timedelta(days=7)
        if selected == 'Letzter Monat':
            return event_dt >= datetime.now() - timedelta(days=30)
        if selected == 'Gesamter Zeitraum':
            return True
        from_dt = datetime.combine(self.date_filter_from.date().toPython(), datetime.min.time())
        to_dt = datetime.combine(self.date_filter_to.date().toPython(), datetime.max.time())
        return from_dt <= event_dt <= to_dt

    def load_config(self, cfg: dict, config_path: Path, log_path: Path) -> None:
        self._config_loading = True
        self.chk_conn_enabled.setChecked(cfg["connection_watch"]["enabled"])
        self.spin_conn_seconds.setValue(cfg["connection_watch"]["interval_seconds"])
        self.chk_speed_enabled.setChecked(cfg["speedtest"]["enabled"])
        self.spin_speed_minutes.setValue(cfg["speedtest"]["interval_minutes"])
        self.chk_ip_enabled.setChecked(cfg["ip_monitor"]["enabled"])
        self.spin_ip_seconds.setValue(cfg["ip_monitor"]["interval_seconds"])
        self.date_daily_report.setDate(QDate.currentDate())
        self.chk_start_windows.setChecked(cfg["startup"]["start_with_windows"])
        self.chk_start_minimized.setChecked(cfg["startup"]["start_minimized_to_tray"])
        self.chk_notify_enabled.setChecked(cfg["notifications"]["enabled"])
        self.chk_notify_online.setChecked(cfg["notifications"]["show_online"])
        self.chk_notify_offline.setChecked(cfg["notifications"]["show_offline"])
        self.chk_notify_ip.setChecked(cfg["notifications"]["show_ip_change"])
        self.chk_notify_speed.setChecked(cfg["notifications"]["show_speed_warnings"])
        self.spin_notify_cooldown.setValue(cfg["notifications"]["cooldown_seconds"])
        self.chk_notify_windows.setChecked(cfg["notifications"].get("show_windows_toasts", True))
        self.chk_notify_app.setChecked(cfg["notifications"].get("show_app_toasts", True))
        self.spin_provider_down.setValue(int(cfg["speedtest"].get("provider_download_mbps", 0)))
        self.spin_provider_up.setValue(int(cfg["speedtest"].get("provider_upload_mbps", 0)))
        self.spin_warn_down.setValue(int(cfg["speedtest"]["warn_download_mbps_below"]))
        self.spin_warn_up.setValue(int(cfg["speedtest"]["warn_upload_mbps_below"]))
        self.spin_warn_ping.setValue(int(cfg["speedtest"]["warn_ping_ms_above"]))
        self.spin_log_size.setValue(int(cfg["logging"]["max_bytes"]))
        self.spin_log_backups.setValue(int(cfg["logging"]["backup_count"]))
        self.cmb_event_filter.setCurrentText(cfg.get("ui", {}).get("event_filter", "Alle anzeigen"))
        self.txt_config_path.setText(str(config_path))
        self.txt_log_path.setText(str(log_path))
        if hasattr(self, 'cmb_date_quick'):
            self.cmb_date_quick.setCurrentText("Gesamter Zeitraum")
            self._apply_quick_date_range()
        self._config_loading = False

    def extract_config(self) -> dict:
        return {
            "connection_watch": {"enabled": self.chk_conn_enabled.isChecked(), "interval_seconds": self.spin_conn_seconds.value()},
            "speedtest": {
                "enabled": self.chk_speed_enabled.isChecked(),
                "interval_minutes": self.spin_speed_minutes.value(),
                "provider_download_mbps": self.spin_provider_down.value(),
                "provider_upload_mbps": self.spin_provider_up.value(),
                "warn_download_mbps_below": self.spin_warn_down.value(),
                "warn_upload_mbps_below": self.spin_warn_up.value(),
                "warn_ping_ms_above": self.spin_warn_ping.value(),
            },
            "ip_monitor": {"enabled": self.chk_ip_enabled.isChecked(), "interval_seconds": self.spin_ip_seconds.value()},
            "notifications": {
                "enabled": self.chk_notify_enabled.isChecked(),
                "show_online": self.chk_notify_online.isChecked(),
                "show_offline": self.chk_notify_offline.isChecked(),
                "show_ip_change": self.chk_notify_ip.isChecked(),
                "show_speed_warnings": self.chk_notify_speed.isChecked(),
                "cooldown_seconds": self.spin_notify_cooldown.value(),
                "show_windows_toasts": self.chk_notify_windows.isChecked(),
                "show_app_toasts": self.chk_notify_app.isChecked(),
            },
            "logging": {"max_bytes": self.spin_log_size.value(), "backup_count": self.spin_log_backups.value()},
            "startup": {"start_with_windows": self.chk_start_windows.isChecked(), "start_minimized_to_tray": self.chk_start_minimized.isChecked()},
            "ui": {"event_filter": self.cmb_event_filter.currentText()},
        }

    def _safe_percent(self, value: float, provider_value: float) -> float:
        if provider_value <= 0:
            return 100.0
        return value / provider_value * 100.0

    def _percent_color(self, percent: float) -> str:
        p = max(0.0, min(100.0, percent)) / 100.0
        r = int(255 * (1.0 - p)); g = int(255 * p)
        return QColor(r, g, 80).name()

    def _ping_color(self, ping_ms: float) -> str:
        p = max(0.0, min(200.0, ping_ms)) / 200.0
        r = int(255 * p); g = int(255 * (1.0 - p))
        return QColor(r, g, 80).name()

    @staticmethod
    def _format_duration(seconds: int | None) -> str:
        if seconds is None:
            return "-"
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def update_status_meta(self, status: dict) -> None:
        self._last_status_payload = dict(status or {})
        self._status_received_at = datetime.now()
        self._meta_base_connection_seconds = status.get("next_connection_check_seconds")
        self._meta_base_ip_seconds = status.get("next_ip_check_seconds")
        self._meta_base_speed_seconds = status.get("next_speedtest_seconds")
        self._current_action_text = str(status.get("current_action") or self._current_action_text or "Bereit")
        self._update_status_meta_label()

    def update_status(self, status: dict) -> None:
        self._last_status_payload = dict(status or {})
        self._status_received_at = datetime.now()
        self._current_ip = str(status.get("public_ip") or self._current_ip or "")
        self._current_local_ip = str(status.get("local_ip") or self._current_local_ip or "")
        self._update_summary_cards(status)

    def _update_summary_cards(self, status: dict | None = None) -> None:
        status = dict(status or self._last_status_payload or {})
        online = status.get("online")
        outage_count = int(status.get("disconnect_count_today", 0))
        public_ip_changes = int(status.get("public_ip_change_count_today", 0))
        local_ip_changes = int(status.get("local_ip_change_count_today", 0))
        self._current_ip = str(status.get("public_ip") or "")
        self._current_local_ip = str(status.get("local_ip") or "")

        online_since_iso = status.get("online_since")
        online_since_text = "-"
        if online is True and online_since_iso:
            try:
                online_since = datetime.fromisoformat(str(online_since_iso))
                online_since_text = self._format_duration(int((datetime.now() - online_since).total_seconds()))
            except Exception:
                online_since_text = "-"

        if online is True:
            headline_text = "Online"
            headline_color = "#4ade80"
        elif online is False:
            headline_text = "Offline"
            headline_color = "#f87171"
            online_since_text = "-"
        else:
            headline_text = "Unbekannt"
            headline_color = "#cbd5e1"
            online_since_text = "-"
        self.lbl_status_title.setText(f"<span style='color:{headline_color}; font-size:30px; font-weight:800;'>{headline_text}</span>")
        self.card_status_value.setText(
            f"<span style='color:#cbd5e1'>Erkannte Abbrüche heute</span><br><span style='font-size:20px; font-weight:700; color:#f3f3f3'>{outage_count}</span>"
            + f"<br><span style='display:block; margin-top:10px; color:#cbd5e1'>Online seit</span><br><span style='font-size:18px; font-weight:700; color:#f3f3f3'>{online_since_text}</span>"
        )
        self.lbl_public_value.setText(self._current_ip or "-")
        self.lbl_local_value.setText(self._current_local_ip or "-")
        self.lbl_public_changes.setText(f"Erkannte Änderungen heute: {public_ip_changes}")
        self.lbl_local_changes.setText(f"Erkannte Änderungen heute: {local_ip_changes}")

        speed = status.get("last_speedtest")
        if speed and speed.get("ok"):
            avg_down = float(speed.get("avg_download_mbps", 0.0))
            avg_up = float(speed.get("avg_upload_mbps", 0.0))
            current_down = float(speed.get("download_mbps", 0.0) or 0.0)
            current_up = float(speed.get("upload_mbps", 0.0) or 0.0)
            down_percent = self._safe_percent(current_down, float(status.get("provider_download_mbps", 0.0) or 0.0))
            up_percent = self._safe_percent(current_up, float(status.get("provider_upload_mbps", 0.0) or 0.0))
            ping = float(speed.get("ping_ms", 0.0))
            avg_down_percent = self._safe_percent(avg_down, float(status.get("provider_download_mbps", 0.0) or 0.0))
            avg_up_percent = self._safe_percent(avg_up, float(status.get("provider_upload_mbps", 0.0) or 0.0))
            self.lbl_down_block.setText(self._speed_metric_html("Download", current_down, down_percent))
            self.lbl_avg_down_block.setText(self._speed_metric_html("Average", avg_down, avg_down_percent))
            self.lbl_up_block.setText(self._speed_metric_html("Upload", current_up, up_percent))
            self.lbl_avg_up_block.setText(self._speed_metric_html("Average", avg_up, avg_up_percent))
            self.lbl_ping_block.setText(self._ping_metric_html(ping))
            self.lbl_ping_placeholder.setText("")
        elif speed:
            fail_html = f"<span style='color:#f87171'><b>Letzte Messung fehlgeschlagen</b><br>{html.escape(speed.get('error', '-'))}</span>"
            self.lbl_down_block.setText(fail_html)
            self.lbl_avg_down_block.setText("")
            self.lbl_up_block.setText("")
            self.lbl_avg_up_block.setText("")
            self.lbl_ping_block.setText("")
            self.lbl_ping_placeholder.setText("")
        else:
            self.lbl_down_block.setText("Noch kein Ergebnis")
            self.lbl_avg_down_block.setText("")
            self.lbl_up_block.setText("")
            self.lbl_avg_up_block.setText("")
            self.lbl_ping_block.setText("")
            self.lbl_ping_placeholder.setText("")


    def _remaining_live_seconds(self, base_seconds: int | None) -> int | None:
        if base_seconds is None:
            return None
        elapsed = int((datetime.now() - self._status_received_at).total_seconds())
        return max(0, int(base_seconds) - elapsed)

    def _update_status_meta_label(self) -> None:
        next_connection = self._format_duration(self._remaining_live_seconds(self._meta_base_connection_seconds))
        next_ip = self._format_duration(self._remaining_live_seconds(self._meta_base_ip_seconds))
        next_speed = self._format_duration(self._remaining_live_seconds(self._meta_base_speed_seconds))
        self.lbl_next_checks.setText(
            f"Nächste Online-Prüfung: {next_connection}   |   Nächste IP-Prüfung: {next_ip}   |   Nächster Speedtest: {next_speed}"
        )
        self.lbl_current_action.setText(f"Aktivität: {self._current_action_text}")

    def _tick_live_ui(self) -> None:
        self._update_status_meta_label()
        self._update_summary_cards()

    def set_current_action(self, text: str) -> None:
        self._current_action_text = text or "Bereit"
        self._update_status_meta_label()

    def clear_current_action(self) -> None:
        self._current_action_text = "Bereit"
        self._update_status_meta_label()

    def _set_custom_date_range(self) -> None:
        if not hasattr(self, 'cmb_date_quick'):
            return
        if self.cmb_date_quick.currentText() != 'Benutzerdefiniert':
            self.cmb_date_quick.blockSignals(True)
            self.cmb_date_quick.setCurrentText('Benutzerdefiniert')
            self.cmb_date_quick.blockSignals(False)
        self._refresh_event_views()

    def _notify_config_edited(self) -> None:
        if not self._config_loading:
            self.config_edited.emit()

    def _wire_auto_save_controls(self) -> None:
        toggle_widgets = [
            self.chk_start_windows, self.chk_start_minimized, self.chk_conn_enabled, self.chk_ip_enabled,
            self.chk_speed_enabled, self.chk_notify_enabled, self.chk_notify_windows, self.chk_notify_app,
            self.chk_notify_online, self.chk_notify_offline, self.chk_notify_ip, self.chk_notify_speed,
        ]
        for widget in toggle_widgets:
            widget.toggled.connect(lambda _checked, self=self: self._notify_config_edited())
        spin_widgets = [
            self.spin_conn_seconds, self.spin_ip_seconds, self.spin_speed_minutes, self.spin_notify_cooldown,
            self.spin_provider_down, self.spin_provider_up, self.spin_warn_down, self.spin_warn_up,
            self.spin_warn_ping, self.spin_log_size, self.spin_log_backups,
        ]
        for widget in spin_widgets:
            widget.valueChanged.connect(lambda _value, self=self: self._notify_config_edited())
        self.cmb_event_filter.currentTextChanged.connect(lambda _text, self=self: self._notify_config_edited())
        if hasattr(self, 'cmb_date_quick'):
            self.cmb_date_quick.currentTextChanged.connect(self._apply_quick_date_range)
            self.date_filter_from.dateChanged.connect(lambda *_args: self._set_custom_date_range())
            self.date_filter_to.dateChanged.connect(lambda *_args: self._set_custom_date_range())

    def set_history_events(self, events: list[dict]) -> None:
        self._all_events = list(events)
        self._refresh_event_views()

    def append_event(self, event: dict) -> None:
        self._all_events.append(event)
        self._refresh_event_views()

    def show_report_text(self, title: str, content: str) -> None:
        self.tabs.setCurrentWidget(self.tabs.widget(2))
        self.txt_event_log.setPlainText(f"{title}\n\n{content}")
        self.txt_event_log.verticalScrollBar().setValue(0)

    def _filtered_events(self) -> list[dict]:
        mode = self.cmb_event_filter.currentText()
        filtered_source = [event for event in self._all_events if self._event_in_selected_range(event)]
        if mode == "Verbindungen":
            allowed = {"online", "offline", "manual_connection_check"}
        elif mode == "IP-Änderungen":
            allowed = {"ip_changed", "ip_init", "local_ip_changed", "local_ip_init", "manual_ip_check"}
        elif mode == "Speedtests":
            allowed = {"speedtest_ok", "speedtest_warn", "error", "manual_speedtest", "manual_speedtest_warn", "manual_speedtest_error"}
        else:
            return list(reversed(filtered_source))
        return list(reversed([event for event in filtered_source if event.get("type") in allowed]))

    def filtered_events(self) -> list[dict]:
        return self._filtered_events()

    def _event_icon_file(self, event_type: str) -> str | None:
        if event_type in {"online", "offline", "manual_connection_check"}:
            return "wifi_icon.png"
        if event_type in {"ip_changed", "ip_init", "local_ip_changed", "local_ip_init", "manual_ip_check"}:
            return "globe_icon.png"
        if event_type in {"speedtest_ok", "speedtest_warn", "manual_speedtest", "manual_speedtest_warn", "manual_speedtest_error"}:
            return "speed_icon.png"
        return None

    def _event_parts(self, event: dict):
        et = event.get("type", "")
        ts = str(event.get("timestamp", ""))
        parts = ts.split(" ", 1)
        date_part = parts[0] if parts else ""
        time_part = parts[1] if len(parts) > 1 else ""
        extra = event.get("extra") or {}
        if et in {"online", "offline", "manual_connection_check"}:
            if et == "manual_connection_check":
                return "", date_part, time_part, "Verbindung", html.escape(str(event.get("message", "-"))), QColor("#cbd5e1")
            return "", date_part, time_part, "Verbindung", ("online" if et == "online" else "offline"), QColor("#4ade80") if et == "online" else QColor("#f87171")
        if et in {"ip_changed", "ip_init", "local_ip_changed", "local_ip_init", "manual_ip_check"}:
            if et == "manual_ip_check":
                return "", date_part, time_part, "IP-Prüfung", html.escape(str(event.get("message", "-"))), QColor("#cbd5e1")
            scope = "Lokal" if et in {"local_ip_changed", "local_ip_init"} else "Öffentlich"
            return "", date_part, time_part, f"{scope}e IP", str(extra.get("new") or extra.get("local_ip") or extra.get("public_ip") or "-"), QColor("#60a5fa")
        if et in {"speedtest_ok", "speedtest_warn", "manual_speedtest", "manual_speedtest_warn", "manual_speedtest_error"}:
            dp = float(extra.get("download_percent", 0.0))
            up = float(extra.get("upload_percent", 0.0))
            ping = float(extra.get("ping_ms", 0.0))
            entry_html = (
                f"Down {extra.get('download_mbps', 0)} Mbit/s (<span style='color:{self._percent_color(dp)}; font-weight:700'>{dp:.0f}%</span>) | "
                f"Up {extra.get('upload_mbps', 0)} Mbit/s (<span style='color:{self._percent_color(up)}; font-weight:700'>{up:.0f}%</span>) | "
                f"Ping <span style='color:{self._ping_color(ping)}; font-weight:700'>{ping:.0f} ms</span>"
            )
            return "", date_part, time_part, "Speedtest", entry_html, None
        return "", date_part, time_part, "Hinweis", html.escape(str(event.get("message", "-"))), None

    def _refresh_event_views(self, *args) -> None:
        filtered = self._filtered_events()
        self.tbl_events.setRowCount(len(filtered))
        for row, event in enumerate(filtered):
            symbol, date_part, time_part, event_name, entry_html, color = self._event_parts(event)
            bg = QColor(44, 49, 57, 255) if row % 2 == 0 else QColor(31, 35, 41, 255)

            icon_item = QTableWidgetItem("")
            icon_item.setBackground(bg)
            self.tbl_events.setItem(row, 0, icon_item)
            icon_file = self._event_icon_file(str(event.get("type", "")))
            if icon_file:
                icon_label = QLabel()
                icon_label.setAlignment(Qt.AlignCenter)
                icon_label.setStyleSheet("background: transparent;")
                self._set_icon_label(icon_label, icon_file, 22)
                self.tbl_events.setCellWidget(row, 0, icon_label)

            for col, value in enumerate([date_part, time_part, event_name], start=1):
                item = QTableWidgetItem(value)
                item.setBackground(bg)
                self.tbl_events.setItem(row, col, item)
            filler = QTableWidgetItem("")
            filler.setBackground(bg)
            self.tbl_events.setItem(row, 4, filler)
            label = QLabel(); label.setTextFormat(Qt.RichText); label.setWordWrap(True)
            label.setStyleSheet("background: transparent; padding: 4px; color: #f3f3f3;")
            if color is not None and event.get("type") in {"online", "offline", "manual_connection_check", "ip_changed", "ip_init", "local_ip_changed", "local_ip_init", "manual_ip_check"}:
                label.setText(f"<span style='color:{color.name()}; font-weight:700'>{html.escape(str(entry_html))}</span>")
            else:
                label.setText(str(entry_html))
            self.tbl_events.setCellWidget(row, 4, label)
            self.tbl_events.setRowHeight(row, 48)

        self.txt_event_log.setPlainText("\n".join(self._format_event(event) for event in filtered))
        self.tbl_events.scrollToTop()
        self.txt_event_log.verticalScrollBar().setValue(0)

    def _format_event(self, event: dict) -> str:
        et = event.get("type", "")
        ts = str(event.get("timestamp", ""))
        extra = event.get("extra") or {}
        if et in {"online", "offline"}:
            return f"{ts} | Verbindung | {'online' if et == 'online' else 'offline'}"
        if et == "manual_connection_check":
            return f"{ts} | Verbindung | {event.get('message', '-')}"
        if et in {"ip_changed", "ip_init", "local_ip_changed", "local_ip_init"}:
            scope = "Lokale IP" if et in {"local_ip_changed", "local_ip_init"} else "Öffentliche IP"
            return f"{ts} | {scope} | {extra.get('old') or '-'} -> {extra.get('new') or '-'}"
        if et == "manual_ip_check":
            return f"{ts} | IP-Prüfung | {event.get('message', '-')}"
        if et in {"speedtest_ok", "speedtest_warn", "manual_speedtest", "manual_speedtest_warn", "manual_speedtest_error"}:
            return (
                f"{ts} | Speedtest | Down {extra.get('download_mbps', 0)} Mbit/s ({float(extra.get('download_percent', 0)):.0f}%) | "
                f"Up {extra.get('upload_mbps', 0)} Mbit/s ({float(extra.get('upload_percent', 0)):.0f}%) | Ping {extra.get('ping_ms', 0)} ms"
            )
        return f"{ts} | Hinweis | {event.get('message', '-')}"

    def show_config_json(self, cfg: dict) -> None:
        self.txt_event_log.append("\n--- Aktuelle Konfiguration ---\n" + json.dumps(cfg, indent=2, ensure_ascii=False))

    def choose_export_path(self) -> Path | None:
        filename, _ = QFileDialog.getSaveFileName(self, "Gefilterte Ereignisse exportieren", "ereignisse_export.txt", "Textdateien (*.txt)")
        return Path(filename) if filename else None

    def _emit_copy_ip(self) -> None:
        if self._current_ip:
            self.copy_ip_requested.emit(self._current_ip)

    def _emit_copy_local_ip(self) -> None:
        if self._current_local_ip:
            self.copy_local_ip_requested.emit(self._current_local_ip)

    def _emit_daily_report_request(self) -> None:
        self.daily_report_requested.emit(self.date_daily_report.date().toString("yyyy-MM-dd"))

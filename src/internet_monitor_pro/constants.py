APP_NAME = "Internet-Protokoll"
APP_AUTHOR = "Skymenn"
APP_WINDOW_TITLE = "Internet-Protokoll"
APP_VERSION = "V26"
POPUP_TITLE = "Internet-Protokoll"
CONFIG_FILE_NAME = "config.json"
LOG_FILE_NAME = "internal.log"
EVENT_HISTORY_FILE_NAME = "ereignisverlauf.jsonl"
REPORTS_DIR_NAME = "reports"
ASSETS_DIR_NAME = "assets"
ICON_FILE_NAME = "icon.ico"

DEFAULT_CONFIG = {
    "connection_watch": {
        "enabled": True,
        "interval_seconds": 0.5,
        "socket_targets": [
            {"host": "1.1.1.1", "port": 53, "timeout": 2.0},
            {"host": "8.8.8.8", "port": 53, "timeout": 2.0},
        ],
    },
    "speedtest": {
        "enabled": True,
        "interval_minutes": 5,
        "provider": "speedtest-cli",
        "timeout_seconds": 120,
        "provider_download_mbps": 250,
        "provider_upload_mbps": 50,
        "provider_download_mbps_set_by_installer": False,
        "provider_upload_mbps_set_by_installer": False,
        "warn_download_mbps_below": 0,
        "warn_upload_mbps_below": 0,
        "warn_ping_ms_above": 0,
    },
    "ip_monitor": {
        "enabled": True,
        "interval_seconds": 10,
        "providers": [
            "https://api.ipify.org",
            "https://checkip.amazonaws.com",
            "https://ipv4.icanhazip.com",
        ],
    },
    "notifications": {
        "enabled": True,
        "show_online": True,
        "show_offline": True,
        "show_ip_change": True,
        "show_speed_warnings": True,
        "cooldown_seconds": 5,
        "show_windows_toasts": False,
        "show_app_toasts": True,
    },
    "reporting": {"enabled": True, "daily_report_time": "23:55"},
    "logging": {"max_bytes": 5_000_000, "backup_count": 5, "max_lines_soft": 50000},
    "startup": {"start_with_windows": True, "start_minimized_to_tray": False},
    "ui": {"minimize_to_tray": True, "close_to_tray": True, "event_filter": "Alle anzeigen"},
}

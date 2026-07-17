from __future__ import annotations

import math
import sys
import types
from pathlib import Path

from internet_monitor_pro.services import network_service, startup_service


class _FakeResults:
    def __init__(self, ping: float) -> None:
        self._ping = ping

    def dict(self) -> dict:
        return {
            "ping": self._ping,
            "server": {"name": "Testserver"},
            "client": {"isp": "Test-ISP"},
        }


class _FakeSpeedtest:
    ping = 12.5

    def __init__(self, secure: bool = True) -> None:
        self.results = _FakeResults(self.ping)

    def get_best_server(self) -> None:
        return None

    def download(self) -> float:
        return 100_000_000.0

    def upload(self, pre_allocate: bool = False) -> float:
        return 20_000_000.0


def _run_with_ping(monkeypatch, ping: float):
    fake_class = type("FakeSpeedtest", (_FakeSpeedtest,), {"ping": ping})
    monkeypatch.setitem(sys.modules, "speedtest", types.SimpleNamespace(Speedtest=fake_class))
    return network_service.NetworkService.run_speedtest()


def test_speedtest_rejects_non_finite_ping(monkeypatch) -> None:
    result = _run_with_ping(monkeypatch, math.inf)

    assert result.ok is False
    assert "Ping" in result.error


def test_speedtest_rejects_impossibly_large_ping(monkeypatch) -> None:
    result = _run_with_ping(monkeypatch, 1.0e308)

    assert result.ok is False
    assert "Ping" in result.error


def test_speedtest_keeps_normal_ping(monkeypatch) -> None:
    result = _run_with_ping(monkeypatch, 24.75)

    assert result.ok is True
    assert result.ping_ms == 24.75


def test_app_and_installer_use_one_autostart_registry_name() -> None:
    installer = (Path(__file__).parents[1] / "scripts" / "installer.iss").read_text(encoding="utf-8")

    assert startup_service.APP_REG_NAME == "InternetProtokoll"
    assert 'ValueName: "InternetProtokoll"' in installer


def test_background_duplicate_start_is_silent() -> None:
    assert startup_service.should_notify_duplicate_start(["InternetMonitorPro.exe", "--minimized"]) is False
    assert startup_service.should_notify_duplicate_start(["InternetMonitorPro.exe"]) is True

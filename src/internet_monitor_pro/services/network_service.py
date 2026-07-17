from __future__ import annotations

import os
import math
import socket
import sys
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.request import Request, urlopen


MAX_VALID_PING_MS = 60_000.0


@dataclass(slots=True)
class SpeedtestResult:
    ok: bool
    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    ping_ms: float = 0.0
    error: str = ""
    server: str = ""
    isp: str = ""


class NetworkService:
    @staticmethod
    def is_online(socket_targets: Iterable[dict]) -> bool:
        for target in socket_targets:
            try:
                with socket.create_connection(
                    (target["host"], int(target["port"])),
                    timeout=float(target.get("timeout", 2.0)),
                ):
                    return True
            except OSError:
                continue
        return False

    @staticmethod
    def get_public_ip(providers: Iterable[str], timeout: float = 6.0) -> str | None:
        for provider in providers:
            try:
                req = Request(provider, headers={"User-Agent": "InternetMonitorPro/0.1"})
                with urlopen(req, timeout=timeout) as response:
                    value = response.read().decode("utf-8", errors="ignore").strip()
                if value:
                    return value
            except Exception:
                continue
        return None

    @staticmethod
    def get_local_ip() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            pass

        try:
            hostname = socket.gethostname()
            for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = sockaddr[0]
                if ip and not ip.startswith("127."):
                    return ip
        except OSError:
            pass
        return None

    @staticmethod
    def run_speedtest(timeout_seconds: int = 120) -> SpeedtestResult:
        start = time.time()
        null_handle = None
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            # In einer windowed EXE sind stdout/stderr oft None. speedtest-cli erwartet aber ein
            # Dateihandle mit fileno(). Deshalb hängen wir bei Bedarf os.devnull an.
            if sys.stdout is None or sys.stderr is None:
                null_handle = open(os.devnull, "w", encoding="utf-8")
                if sys.stdout is None:
                    sys.stdout = null_handle
                if sys.stderr is None:
                    sys.stderr = null_handle

            import speedtest  # type: ignore

            st = speedtest.Speedtest(secure=True)
            st.get_best_server()
            download_bps = st.download()
            upload_bps = st.upload(pre_allocate=False)
            results = st.results.dict()
            ping_ms = float(results.get("ping", 0.0))
            if not math.isfinite(ping_ms) or not 0.0 <= ping_ms <= MAX_VALID_PING_MS:
                raise ValueError(f"Ungültiger Pingwert vom Speedtest-Server: {ping_ms!r} ms")
            return SpeedtestResult(
                ok=True,
                download_mbps=round(download_bps / 1_000_000, 2),
                upload_mbps=round(upload_bps / 1_000_000, 2),
                ping_ms=round(ping_ms, 2),
                server=str(results.get("server", {}).get("name", "")),
                isp=str(results.get("client", {}).get("isp", "")),
            )
        except Exception as exc:
            took = round(time.time() - start, 1)
            return SpeedtestResult(ok=False, error=f"{exc} (after {took}s)")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if null_handle is not None:
                null_handle.close()

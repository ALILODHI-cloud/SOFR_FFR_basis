#!/usr/bin/env python3
"""
Live STIR curves server: serves dashboard + JSON API, auto-refreshes from Barchart.

Endpoints:
  GET /                      → dashboard HTML
  GET /api/data              → stir_curves_data.json
  GET /api/status            → refresh schedule / health
  POST /api/refresh          → trigger background Barchart fetch

Usage:
  python3 serve_stir_live.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "stir_curves_data.json"
DASHBOARD = ROOT / "stir_curves_dashboard.html"
PORT = int(__import__("os").environ.get("STIR_LIVE_PORT", "8787"))
REFRESH_MINUTES = int(__import__("os").environ.get("STIR_REFRESH_MINUTES", "30"))

_state = {
    "refreshing": False,
    "last_refresh_utc": None,
    "last_error": None,
    "next_refresh_utc": None,
}
_lock = threading.Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_str(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M UTC")


def run_refresh() -> None:
    with _lock:
        if _state["refreshing"]:
            return
        _state["refreshing"] = True
        _state["last_error"] = None

    print(f"[{utc_str()}] Starting Barchart refresh…")
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "analyze_stir_curves.py")],
            cwd=ROOT,
            check=True,
            timeout=3600,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "build_stir_curves_dashboard.py")],
            cwd=ROOT,
            check=True,
            timeout=120,
        )
        with _lock:
            _state["last_refresh_utc"] = utc_str()
            _state["next_refresh_utc"] = utc_str(utc_now() + timedelta(minutes=REFRESH_MINUTES))
        print(f"[{utc_str()}] Refresh complete.")
    except Exception as exc:
        with _lock:
            _state["last_error"] = str(exc)
        print(f"[{utc_str()}] Refresh failed: {exc}")
    finally:
        with _lock:
            _state["refreshing"] = False


def refresh_loop() -> None:
    while True:
        run_refresh()
        time.sleep(REFRESH_MINUTES * 60)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[{utc_str()}] {self.address_string()} {fmt % args}")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")

    def _json(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/stir_curves_dashboard.html"):
            return self._file(DASHBOARD, "text/html; charset=utf-8")
        if path == "/api/data":
            return self._file(DATA_FILE, "application/json")
        if path == "/api/status":
            with _lock:
                status = {
                    **_state,
                    "generated_utc": None,
                    "port": PORT,
                    "refresh_interval_minutes": REFRESH_MINUTES,
                }
            if DATA_FILE.is_file():
                try:
                    with DATA_FILE.open() as f:
                        status["generated_utc"] = json.load(f).get("generated_utc")
                except Exception:
                    pass
            return self._json(status)
        if path == "/health":
            return self._json({"ok": True, "time": utc_str()})
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/refresh":
            threading.Thread(target=run_refresh, daemon=True).start()
            return self._json({"started": True, "time": utc_str()})
        self.send_error(404)


def main() -> None:
    threading.Thread(target=refresh_loop, daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"STIR live server on http://0.0.0.0:{PORT}  (refresh every {REFRESH_MINUTES}m)")
    server.serve_forever()


if __name__ == "__main__":
    main()

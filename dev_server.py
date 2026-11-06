"""Local preview server that serves the dashboard and a mock Function endpoint."""

from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from insights import build_dashboard_payload  # noqa: E402


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/insights":
            query = parse_qs(parsed.query)
            diet = query.get("diet", ["all"])[0]
            try:
                dataframe = pd.read_csv(BACKEND / "All_Diets.csv")
                payload = build_dashboard_payload(
                    dataframe,
                    diet_filter=diet,
                    source="Local validation server",
                )
                self._json(payload, 200)
            except ValueError as error:
                self._json({"error": str(error)}, 400)
            return
        super().do_GET()

    def _json(self, payload, status):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print(f"Dashboard preview: http://{address[0]}:{address[1]}", flush=True)
    ThreadingHTTPServer(address, DashboardHandler).serve_forever()

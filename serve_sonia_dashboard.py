#!/usr/bin/env python3
"""Serve the SONIA dashboard locally (avoids file:// browser restrictions)."""
import http.server
import os
import socketserver
import webbrowser

PORT = int(os.environ.get("SONIA_DASH_PORT", "8765"))
ROOT = os.path.dirname(os.path.abspath(__file__))
DASH = "sonia_dashboard.html"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", f"/{DASH}")
            self.end_headers()
            return
        return super().do_GET()

    def log_message(self, fmt, *args):
        if args and "200" in str(args[1]):
            print(f"  {args[0]} -> {args[1]}")


def main():
    os.chdir(ROOT)
    if not os.path.isfile(DASH):
        raise SystemExit(
            f"Missing {DASH}. Run:\n"
            "  python analyze_sonia.py\n"
            "  python build_sonia_dashboard.py"
        )
    url = f"http://127.0.0.1:{PORT}/{DASH}"
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving SONIA dashboard at {url}")
        print("Press Ctrl+C to stop.")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()


if __name__ == "__main__":
    main()

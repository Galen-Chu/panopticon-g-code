"""
Outer Axis — Ecosystem Dashboard · 生態儀表板

Serves a single-page HTML dashboard showing G-Code ecosystem health.
Reads the latest health report JSON and renders it with D3.js.
"""
import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
DATA_DIR = DASHBOARD_DIR.parent.parent / "data" / "monitor"
PORT = 8600


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serves the dashboard HTML and health data API."""

    def do_GET(self):
        if self.path == "/api/health":
            self._serve_health_data()
        elif self.path == "/":
            self._serve_dashboard()
        else:
            super().do_GET()

    def _serve_health_data(self):
        """Return the latest health report as JSON."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        report = self._load_latest_report()
        self.wfile.write(json.dumps(report, ensure_ascii=False).encode("utf-8"))

    def _serve_dashboard(self):
        """Serve the dashboard HTML."""
        html_file = DASHBOARD_DIR / "index.html"
        if html_file.exists():
            content = html_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "Dashboard not found")

    def _load_latest_report(self) -> dict:
        """Load the most recent health report."""
        if not DATA_DIR.exists():
            return {"error": "No health reports available"}
        reports = sorted(DATA_DIR.glob("health_*.json"), reverse=True)
        if not reports:
            return {"error": "No health reports available"}
        return json.loads(reports[0].read_text(encoding="utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress request logging


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Panopticon Ecosystem Dashboard")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    server = HTTPServer(("localhost", args.port), DashboardHandler)
    print(f"\n  Panopticon Dashboard")
    print(f"  http://localhost:{args.port}")
    print(f"  API: http://localhost:{args.port}/api/health")
    print(f"  Press Ctrl+C to stop\n")

    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Dashboard stopped.")
        server.server_close()


if __name__ == "__main__":
    main()

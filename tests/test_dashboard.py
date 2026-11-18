"""Tests for the Outer Axis dashboard server."""
import json
import threading
import urllib.request
from http.server import HTTPServer

import pytest

from outer.dashboard.server import DashboardHandler


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    from outer.dashboard import server as server_module
    monkeypatch.setattr(server_module, "DATA_DIR", tmp_path)
    # two reports; the newer filename must win
    for name, total in (("health_20260101_000000.json", 5),
                        ("health_20260102_000000.json", 9)):
        (tmp_path / name).write_text(
            json.dumps({"timestamp": name, "total_repos": total}), encoding="utf-8")
    return tmp_path


def _serve_one():
    """Bind an ephemeral port and serve exactly one request."""
    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    return server, thread


class TestHealthAPI:
    def test_serves_latest_report(self, data_dir):
        server, thread = _serve_one()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                        timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            thread.join(timeout=5)
            server.server_close()
        assert payload["total_repos"] == 9

    def test_content_type_is_json(self, data_dir):
        server, thread = _serve_one()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                        timeout=5) as response:
                content_type = response.headers["Content-Type"]
        finally:
            thread.join(timeout=5)
            server.server_close()
        assert "application/json" in content_type


class TestEmptyData:
    def test_reports_error_without_data(self, tmp_path, monkeypatch):
        from outer.dashboard import server as server_module
        monkeypatch.setattr(server_module, "DATA_DIR", tmp_path)
        server, thread = _serve_one()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                        timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            thread.join(timeout=5)
            server.server_close()
        assert "error" in payload

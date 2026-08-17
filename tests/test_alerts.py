"""Tests for the Outer Axis alert system."""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from outer.alerts.alerter import AlertSystem


@pytest.fixture
def alerter(tmp_path, monkeypatch):
    from outer.alerts import alerter as alerter_module
    monkeypatch.setattr(alerter_module, "DATA_DIR", tmp_path)
    return AlertSystem()


class TestAlertSystem:
    def test_healthy_report_no_alerts(self, alerter):
        report = {
            "repos": [{"repo": "test", "status": "healthy", "open_issues": 0, "last_push": datetime.utcnow().isoformat()}],
        }
        alerts = alerter.check_and_alert(report)
        assert len(alerts) == 0

    def test_unhealthy_repo_triggers_alert(self, alerter):
        report = {
            "repos": [{"repo": "broken-repo", "status": "error", "open_issues": 0}],
        }
        alerts = alerter.check_and_alert(report)
        assert len(alerts) == 1
        assert alerts[0]["level"] == "warning"
        assert "broken-repo" in alerts[0]["message_en"]

    def test_high_issues_triggers_alert(self, alerter):
        report = {
            "repos": [{"repo": "busy-repo", "status": "healthy", "open_issues": 15, "last_push": datetime.utcnow().isoformat()}],
        }
        alerts = alerter.check_and_alert(report)
        assert len(alerts) == 1
        assert "15" in alerts[0]["message_en"]

    def test_stale_repo_triggers_alert(self, alerter):
        stale_date = (datetime.utcnow() - timedelta(days=45)).isoformat()
        report = {
            "repos": [{"repo": "stale-repo", "status": "healthy", "open_issues": 0, "last_push": stale_date}],
        }
        alerts = alerter.check_and_alert(report)
        assert len(alerts) == 1
        assert alerts[0]["level"] == "info"
        assert "45" in alerts[0]["message_en"]

    def test_alerts_are_bilingual(self, alerter):
        report = {
            "repos": [{"repo": "test", "status": "not_found", "open_issues": 0}],
        }
        alerts = alerter.check_and_alert(report)
        assert len(alerts) > 0
        assert "message_en" in alerts[0]
        assert "message_zh" in alerts[0]
        assert len(alerts[0]["message_zh"]) > 5

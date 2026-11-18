"""Tests for the Outer Axis alert system."""
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from outer.alerts.alerter import AlertSystem


@pytest.fixture
def alerter(tmp_path, monkeypatch):
    from outer.alerts import alerter as alerter_module
    monkeypatch.setattr(alerter_module, "DATA_DIR", tmp_path)
    return AlertSystem()


def _report(**repo_fields):
    """A one-repo health report; defaults are fully healthy."""
    repo = {"repo": "test", "status": "healthy", "open_issues": 0,
            "last_push": datetime.now(UTC).isoformat()}
    repo.update(repo_fields)
    return {"repos": [repo]}


class TestAlertSystem:
    def test_healthy_report_no_alerts(self, alerter):
        alerts = alerter.check_and_alert(_report())
        assert len(alerts) == 0

    def test_unhealthy_repo_triggers_alert(self, alerter):
        alerts = alerter.check_and_alert(_report(repo="broken-repo", status="error"))
        assert len(alerts) == 1
        assert alerts[0]["level"] == "warning"
        assert alerts[0]["type"] == "repo_unhealthy"
        assert "broken-repo" in alerts[0]["message_en"]

    def test_high_issues_triggers_alert(self, alerter):
        alerts = alerter.check_and_alert(_report(open_issues=15))
        assert len(alerts) == 1
        assert alerts[0]["type"] == "high_issues"
        assert "15" in alerts[0]["message_en"]

    def test_stale_repo_triggers_alert(self, alerter):
        stale_date = (datetime.now(UTC) - timedelta(days=45)).isoformat()
        alerts = alerter.check_and_alert(_report(last_push=stale_date))
        assert len(alerts) == 1
        assert alerts[0]["level"] == "info"
        assert alerts[0]["type"] == "stale"
        assert "45" in alerts[0]["message_en"]

    def test_alerts_are_bilingual(self, alerter):
        alerts = alerter.check_and_alert(_report(status="not_found"))
        assert len(alerts) > 0
        assert "message_en" in alerts[0]
        assert "message_zh" in alerts[0]
        assert len(alerts[0]["message_zh"]) > 5


class TestAnomalyState:
    """Delta computation against the persistent anomaly state."""

    def test_first_sighting_is_all_new(self, alerter):
        state = {"anomalies": {}, "recently_resolved": {}}
        alerts = [
            alerter._create_alert("ci_failing", "warning", "repo-a", "e", "z"),
            alerter._create_alert("stale", "info", "repo-b", "e", "z"),
        ]
        deltas = alerter._apply_state(state, alerts)
        assert deltas["new"] == ["ci_failing:repo-a", "stale:repo-b"]
        assert deltas["resolved"] == []
        assert set(state["anomalies"]) == {"ci_failing:repo-a", "stale:repo-b"}

    def test_resolution_moves_to_recently_resolved(self, alerter):
        state = {"anomalies": {}, "recently_resolved": {}}
        ci = alerter._create_alert("ci_failing", "warning", "repo-a", "e", "z")
        stale = alerter._create_alert("stale", "info", "repo-b", "e", "z")
        alerter._apply_state(state, [ci, stale])

        deltas = alerter._apply_state(state, [ci])  # repo-b recovered

        assert deltas["new"] == []
        assert deltas["resolved"] == ["stale:repo-b"]
        assert list(state["anomalies"]) == ["ci_failing:repo-a"]
        resolved = state["recently_resolved"]["stale:repo-b"]
        assert resolved["repo"] == "repo-b"
        assert resolved["duration_days"] == 0  # same-run resolution

    def test_state_roundtrip(self, alerter):
        state = {"anomalies": {}, "recently_resolved": {}}
        alert = alerter._create_alert("stale", "info", "repo-x", "e", "z")
        alerter._apply_state(state, [alert])
        alerter._save_state(state)

        loaded = alerter._load_state()
        assert "stale:repo-x" in loaded["anomalies"]
        assert loaded["anomalies"]["stale:repo-x"]["first_seen"]


class TestTrackingIssue:
    """The single labeled issue: create / update-on-change / close."""

    @staticmethod
    def _resp(status_code=200, payload=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = payload if payload is not None else []
        return resp

    @patch("outer.alerts.alerter.requests")
    def test_first_anomaly_creates_issue(self, mock_requests, tmp_path, monkeypatch):
        from outer.alerts import alerter as module
        monkeypatch.setattr(module, "DATA_DIR", tmp_path)
        monkeypatch.setenv("PANOPTICON_ALERT_ISSUES", "1")
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        created = self._resp(201, {"html_url": "http://x/1"})
        mock_requests.request.side_effect = [
            self._resp(200, []),       # GET open labeled issues → none
            self._resp(422),           # POST label (already exists is fine)
            created,                   # POST issue
        ]

        alerts = module.AlertSystem().check_and_alert(_report(status="error"))

        assert alerts
        state = json.loads((tmp_path / "state" / "alerts.json").read_text(encoding="utf-8"))
        assert "repo_unhealthy:test" in state["anomalies"]
        create_call = mock_requests.request.call_args_list[2]
        assert create_call.args[0] == "POST"
        assert create_call.kwargs["json"]["labels"] == ["panopticon-alert"]

    @patch("outer.alerts.alerter.requests")
    def test_unchanged_anomalies_are_silent(self, mock_requests, tmp_path, monkeypatch):
        from outer.alerts import alerter as module
        monkeypatch.setattr(module, "DATA_DIR", tmp_path)
        monkeypatch.setenv("PANOPTICON_ALERT_ISSUES", "1")
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        system = module.AlertSystem()

        # seed state so today's anomaly is already known
        state = {"anomalies": {}, "recently_resolved": {}}
        stale = system._create_alert("stale", "info", "test", "e", "z")
        system._apply_state(state, [stale])
        system._save_state(state)

        open_issue = {"number": 7, "title": "👁️ Panopticon Ecosystem Status"}
        mock_requests.request.return_value = self._resp(200, [open_issue])

        system.check_and_alert(_report(last_push=(datetime.now(UTC)
                                                  - timedelta(days=45)).isoformat()))

        # only the read happened — no writes for an unchanged set
        assert mock_requests.request.call_count == 1
        assert mock_requests.request.call_args.args[0] == "GET"

    @patch("outer.alerts.alerter.requests")
    def test_all_clear_closes_issue(self, mock_requests, tmp_path, monkeypatch):
        from outer.alerts import alerter as module
        monkeypatch.setattr(module, "DATA_DIR", tmp_path)
        monkeypatch.setenv("PANOPTICON_ALERT_ISSUES", "1")
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        system = module.AlertSystem()

        state = {"anomalies": {}, "recently_resolved": {}}
        alert = system._create_alert("stale", "info", "test", "e", "z")
        system._apply_state(state, [alert])
        system._save_state(state)

        open_issue = {"number": 7, "title": "👁️ Panopticon Ecosystem Status"}
        mock_requests.request.side_effect = [
            self._resp(200, [open_issue]),   # GET open labeled issues
            self._resp(201),                 # POST all-clear comment
            self._resp(200),                 # PATCH close
        ]

        alerts = system.check_and_alert(_report())  # fully healthy now

        assert alerts == []
        close_call = mock_requests.request.call_args_list[2]
        assert close_call.args[0] == "PATCH"
        assert close_call.kwargs["json"] == {"state": "closed"}
        state = json.loads((tmp_path / "state" / "alerts.json").read_text(encoding="utf-8"))
        assert state["anomalies"] == {}


class TestWorkflowFailureReport:
    @staticmethod
    def _resp(status_code=200, payload=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = payload if payload is not None else []
        return resp

    @patch("outer.alerts.alerter.requests")
    def test_failure_issue_deduped_per_day(self, mock_requests, monkeypatch):
        from outer.alerts import alerter as module
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        monkeypatch.setenv("GITHUB_RUN_ID", "123")
        title = (f"🚨 Panopticon daily cycle failed — "
                 f"{datetime.now(UTC).strftime('%Y-%m-%d')}")
        mock_requests.get.return_value = self._resp(200, [{"title": title}])

        module.report_workflow_failure()

        mock_requests.post.assert_not_called()

    @patch("outer.alerts.alerter.requests")
    def test_failure_issue_created_when_new(self, mock_requests, monkeypatch):
        from outer.alerts import alerter as module
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        monkeypatch.setenv("GITHUB_RUN_ID", "123")
        mock_requests.get.return_value = self._resp(200, [])
        mock_requests.post.return_value = self._resp(201, {"html_url": "http://x/9"})

        module.report_workflow_failure()

        body = mock_requests.post.call_args.kwargs["json"]["body"]
        assert "actions/runs/123" in body

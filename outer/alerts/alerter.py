"""
Outer Axis — Alert System · 異常警報系統

Detects anomalies in ecosystem health (repo status, open issues, stale
repos, failing CI) and delivers notifications via Slack, generic webhook,
or a GitHub issue (recommended — lands where you already read alerts).

Issue mode is stateful: a single persistent issue labeled
"panopticon-alert" tracks the current anomaly set. It is updated only
when the set changes (new / resolved anomalies) and closes itself when
everything is healthy again — chronic problems no longer open a new
issue every day. State persists in data/state/alerts.json and is
committed back by the daily workflow, so it survives between runs.
"""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ALERT_ISSUE_REPO = os.environ.get("PANOPTICON_REPO", "Galen-Chu/panopticon-g-code")
ALERT_LABEL = "panopticon-alert"

# Anomaly type → bilingual short label for the tracking issue body
TYPE_LABELS = {
    "repo_unhealthy": ("repo not healthy", "儲存庫狀態異常"),
    "ci_failing": ("failing CI", "CI 持續失敗"),
    "high_issues": ("high open issues", "未解決議題過多"),
    "stale": ("stale repo", "儲存庫休眠"),
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AlertSystem:
    """Detects ecosystem anomalies and sends alerts."""

    def __init__(self):
        self.alerts_dir = DATA_DIR / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = DATA_DIR / "state" / "alerts.json"

    # ── Detection ────────────────────────────────────────────────────

    def check_and_alert(self, health_report: dict) -> list:
        """Check a health report for anomalies and trigger alerts.

        In issue mode (CI), the anomaly set is folded into persistent
        state first, so the tracking issue is only touched on change.
        """
        alerts = self._detect(health_report)

        deltas = None
        if self._issue_mode():
            state = self._load_state()
            deltas = self._apply_state(state, alerts)
            self._save_state(state)

        if alerts:
            self._save_alerts(alerts)
            self._send_notifications(alerts, deltas)
        elif deltas and deltas["resolved"]:
            # everything recovered — close the tracking issue
            self._send_notifications([], deltas)

        return alerts

    def _detect(self, health_report: dict) -> list:
        alerts = []
        for repo in health_report.get("repos", []):
            name = repo.get("repo", "unknown")

            # Alert on non-healthy repos
            if repo.get("status") != "healthy":
                alerts.append(self._create_alert(
                    anomaly_type="repo_unhealthy", level="warning", repo=name,
                    message_en=f"Repository {name} status: {repo.get('status')}",
                    message_zh=f"儲存庫 {name} 狀態：{repo.get('status')}",
                ))

            # Alert on failing CI/CD pipelines
            ci = repo.get("ci", {})
            if ci.get("status") == "failing":
                failed = ci.get("failed_runs", "?")
                checked = ci.get("checked_runs", "?")
                alerts.append(self._create_alert(
                    anomaly_type="ci_failing", level="warning", repo=name,
                    message_en=(f"Failing CI: {failed}/{checked} recent runs failed "
                                f"in {name}"),
                    message_zh=f"CI 失敗：{name} 近期 {checked} 次執行中 {failed} 次失敗",
                ))

            # Alert on high open issues
            open_issues = repo.get("open_issues", 0)
            if open_issues > 10:
                alerts.append(self._create_alert(
                    anomaly_type="high_issues", level="warning", repo=name,
                    message_en=f"High open issues: {open_issues} in {name}",
                    message_zh=f"未解決議題過多：{name} 有 {open_issues} 個",
                ))

            # Alert on stale repos (no push in 30 days — GitHub disables
            # scheduled workflows at 60 days, this fires first as an early hint)
            last_push = repo.get("last_push", "")
            if last_push:
                push_date = self._parse_timestamp(last_push)
                if push_date:
                    days_since = (_utcnow() - push_date).days
                    if days_since > 30:
                        alerts.append(self._create_alert(
                            anomaly_type="stale", level="info", repo=name,
                            message_en=f"Stale repo: {name} — no push in {days_since} days",
                            message_zh=f"儲存庫休眠：{name} — {days_since} 天未推送",
                        ))

        return alerts

    @staticmethod
    def _parse_timestamp(value: str):
        """Parse an ISO timestamp; naive values are treated as UTC."""
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    def _create_alert(self, anomaly_type: str, level: str, repo: str,
                      message_en: str, message_zh: str) -> dict:
        return {
            "timestamp": _utcnow().isoformat(),
            "type": anomaly_type,
            "level": level,
            "repo": repo,
            "message_en": message_en,
            "message_zh": message_zh,
        }

    # ── Persistent anomaly state ─────────────────────────────────────

    def _issue_mode(self) -> bool:
        return os.environ.get("PANOPTICON_ALERT_ISSUES", "") == "1"

    def _load_state(self) -> dict:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"anomalies": {}, "recently_resolved": {}}
        state.setdefault("anomalies", {})
        state.setdefault("recently_resolved", {})
        return state

    def _save_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state["updated"] = _utcnow().isoformat()
        self.state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _key(alert: dict) -> str:
        return f"{alert['type']}:{alert['repo']}"

    def _apply_state(self, state: dict, alerts: list) -> dict:
        """Fold the current anomaly set into persistent state.

        Returns {"new": [...], "resolved": [...]} anomaly keys so the
        notifier acts only on change. Resolved entries move into
        recently_resolved (10 newest kept) for issue-body context.
        """
        now = _utcnow().isoformat()
        recorded = state["anomalies"]
        resolved_log = state["recently_resolved"]

        current = {self._key(a): a for a in alerts}
        new = sorted(k for k in current if k not in recorded)
        resolved = sorted(k for k in recorded if k not in current)

        for key, alert in current.items():
            entry = recorded.setdefault(key, {
                "type": alert["type"],
                "repo": alert["repo"],
                "level": alert["level"],
                "first_seen": now,
            })
            entry.update(last_seen=now, message_en=alert["message_en"],
                         message_zh=alert["message_zh"])

        for key in resolved:
            entry = recorded.pop(key)
            first = self._parse_timestamp(entry.get("first_seen", "")) or _utcnow()
            resolved_log[key] = {
                "repo": entry.get("repo", "?"),
                "message_en": entry.get("message_en", ""),
                "resolved_at": now,
                "duration_days": max((_utcnow() - first).days, 0),
            }

        if len(resolved_log) > 10:
            newest = sorted(resolved_log.items(),
                            key=lambda kv: kv[1]["resolved_at"], reverse=True)[:10]
            state["recently_resolved"] = dict(newest)

        return {"new": new, "resolved": resolved}

    # ── Delivery ─────────────────────────────────────────────────────

    def _save_alerts(self, alerts: list):
        """Save alerts to the data directory."""
        filepath = self.alerts_dir / f"alerts_{_utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath.write_text(
            json.dumps({"alerts": alerts, "count": len(alerts)}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _send_notifications(self, alerts: list, deltas: dict = None):
        """Send notifications via configured channels."""
        # Slack webhook
        slack_webhook = os.environ.get("SLACK_WEBHOOK", "")
        if slack_webhook and requests and alerts:
            self._send_slack(slack_webhook, alerts)

        # Generic webhook
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "")
        if webhook_url and requests and alerts:
            self._send_webhook(webhook_url, alerts)

        # GitHub tracking issue (recommended default in CI — see daily.yml)
        if self._issue_mode() and requests:
            self._send_github_issue(deltas)

    def _send_slack(self, webhook_url: str, alerts: list):
        """Send alerts to Slack."""
        try:
            text_lines = [f"👁️ Panopticon Alert ({len(alerts)} issues)"]
            for alert in alerts[:5]:
                icon = "⚠️" if alert["level"] == "warning" else "ℹ️"
                text_lines.append(f"{icon} {alert['message_en']}")

            requests.post(webhook_url, json={"text": "\n".join(text_lines)}, timeout=10)
        except Exception as e:
            print(f"  ⚠ Slack notification failed: {e}")

    def _send_webhook(self, url: str, alerts: list):
        """Send alerts to a generic webhook."""
        try:
            requests.post(url, json={"alerts": alerts, "source": "panopticon"}, timeout=10)
        except Exception as e:
            print(f"  ⚠ Webhook notification failed: {e}")

    # ── GitHub tracking issue ────────────────────────────────────────

    def _gh(self, method: str, path: str, **kwargs):
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}",
                   "Accept": "application/vnd.github+json"}
        return requests.request(method, f"https://api.github.com{path}",
                                headers=headers, timeout=10, **kwargs)

    def _send_github_issue(self, deltas: dict):
        """Maintain the single tracking issue labeled "panopticon-alert".

        Create it when the first anomaly appears, update body + comment
        when the anomaly set changes, close with an all-clear comment
        when everything is healthy. No changes → no API writes.
        """
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print("  ⚠ PANOPTICON_ALERT_ISSUES=1 but GITHUB_TOKEN not set — skipping")
            return
        state = self._load_state()
        anomalies = state.get("anomalies", {})
        try:
            resp = self._gh("GET", f"/repos/{ALERT_ISSUE_REPO}/issues",
                            params={"state": "open", "labels": ALERT_LABEL, "per_page": 5})
            issue = None
            if resp.status_code == 200:
                issue = next((i for i in resp.json() if "pull_request" not in i), None)

            if not anomalies:
                if issue:
                    number = issue["number"]
                    self._gh("POST", f"/repos/{ALERT_ISSUE_REPO}/issues/{number}/comments",
                             json={"body": "✅ All clear — every anomaly has resolved. "
                                           "全部異常已恢復，自動關閉。"})
                    self._gh("PATCH", f"/repos/{ALERT_ISSUE_REPO}/issues/{number}",
                             json={"state": "closed"})
                    print(f"  ✓ All clear — tracking issue #{number} closed")
                return

            body = self._render_issue_body(state)
            if not issue:
                # 422 = label already exists, which is fine
                self._gh("POST", f"/repos/{ALERT_ISSUE_REPO}/labels",
                         json={"name": ALERT_LABEL, "color": "5e0f73"})
                resp = self._gh("POST", f"/repos/{ALERT_ISSUE_REPO}/issues",
                                json={"title": "👁️ Panopticon Ecosystem Status",
                                      "body": body, "labels": [ALERT_LABEL]})
                if resp.status_code == 201:
                    print(f"  ✓ Tracking issue created: {resp.json().get('html_url', '')}")
                else:
                    print(f"  ⚠ Issue creation failed: HTTP {resp.status_code}")
            elif deltas and (deltas["new"] or deltas["resolved"]):
                number = issue["number"]
                self._gh("PATCH", f"/repos/{ALERT_ISSUE_REPO}/issues/{number}",
                         json={"body": body})
                self._gh("POST", f"/repos/{ALERT_ISSUE_REPO}/issues/{number}/comments",
                         json={"body": self._render_delta_comment(deltas, state)})
                print(f"  ✓ Tracking issue #{number} updated")
            # else: nothing changed — stay silent, no API writes
        except requests.RequestException as e:
            print(f"  ⚠ GitHub issue notification failed: {e}")

    @staticmethod
    def _duration_days(entry: dict) -> int:
        first = AlertSystem._parse_timestamp(entry.get("first_seen", ""))
        return max((_utcnow() - first).days, 0) if first else 0

    @staticmethod
    def _render_issue_body(state: dict) -> str:
        anomalies = state.get("anomalies", {})
        lines = [
            "Anomalies currently under watch — this issue updates on change "
            "and closes itself when all clear.",
            "目前監控中的異常——狀態變化時自動更新，全部恢復時自動關閉。",
            "",
            "| | Repo | Anomaly · 異常 | Since | Days · 天 |",
            "|---|---|---|---|---|",
        ]
        for _key, a in sorted(anomalies.items()):
            label = TYPE_LABELS.get(a.get("type"), (a.get("type", "?"), a.get("type", "?")))
            lines.append(
                f"| ⚠️ | `{a.get('repo', '?')}` | {label[0]} · {label[1]} "
                f"| {a.get('first_seen', '')[:10]} | {AlertSystem._duration_days(a)} |")

        resolved = state.get("recently_resolved", {})
        if resolved:
            lines += ["", "**Recently resolved · 近期已恢復**", ""]
            for key, r in sorted(resolved.items(),
                                 key=lambda kv: kv[1]["resolved_at"], reverse=True):
                lines.append(f"- ✅ `{r.get('repo', '?')}` — {key} "
                             f"({r.get('duration_days', '?')}d)")

        lines += ["", "---", "_Auto-maintained by the Panopticon daily cycle._"]
        return "\n".join(lines)

    @staticmethod
    def _render_delta_comment(deltas: dict, state: dict) -> str:
        lines = []
        if deltas.get("new"):
            lines.append("**⚠️ New anomalies · 新異常**")
            lines += [f"- `{k}`" for k in deltas["new"]]
        if deltas.get("resolved"):
            lines.append("**✅ Resolved · 已恢復**")
            resolved_log = state.get("recently_resolved", {})
            for k in deltas["resolved"]:
                r = resolved_log.get(k, {})
                suffix = f" ({r.get('duration_days', '?')}d)" if r else ""
                lines.append(f"- `{k}`{suffix}")
        return "\n".join(lines) or "(no changes)"


def report_workflow_failure() -> None:
    """Open an issue when the daily workflow itself fails (deduped per day).

    The watchtower needs its own watchtower — a failed daily cycle would
    otherwise only go red in the Actions tab, where nobody looks.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or not requests:
        print("  ⚠ GITHUB_TOKEN not set or requests unavailable — cannot report failure")
        return
    base = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}"
            f"/{os.environ.get('GITHUB_REPOSITORY', '')}")
    run_url = f"{base}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    title = f"🚨 Panopticon daily cycle failed — {_utcnow().strftime('%Y-%m-%d')}"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(f"https://api.github.com/repos/{ALERT_ISSUE_REPO}/issues",
                            headers=headers, params={"state": "open", "per_page": 50},
                            timeout=10)
        if resp.status_code == 200 and any(i.get("title") == title for i in resp.json()):
            print("  · Failure issue for today already open — skip")
            return
        body = ("The daily cycle workflow failed and needs attention.\n"
                "每日循環工作流程失敗，需要處理。\n\n"
                f"Run: {run_url}\n")
        resp = requests.post(f"https://api.github.com/repos/{ALERT_ISSUE_REPO}/issues",
                             headers=headers, timeout=10,
                             json={"title": title, "body": body})
        if resp.status_code == 201:
            print(f"  ✓ Failure issue created: {resp.json().get('html_url', '')}")
        else:
            print(f"  ⚠ Failure issue creation failed: HTTP {resp.status_code}")
    except requests.RequestException as e:
        print(f"  ⚠ Failure report failed: {e}")


def main():
    import argparse
    import sys

    # Degrade unencodable glyphs on legacy-codepage Windows consoles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Panopticon Alert System")
    parser.add_argument("--check", action="store_true",
                        help="Check latest health report for anomalies")
    parser.add_argument("--report-failure", action="store_true",
                        help="Open an issue because the daily cycle itself failed")
    args = parser.parse_args()

    if args.report_failure:
        report_workflow_failure()
        return

    if args.check:
        monitor_dir = DATA_DIR / "monitor"
        reports = sorted(monitor_dir.glob("health_*.json"), reverse=True) if monitor_dir.exists() else []
        if not reports:
            print("No health reports found. Run outer.monitor first.")
            return

        report = json.loads(reports[0].read_text(encoding="utf-8"))
        alerter = AlertSystem()
        alerts = alerter.check_and_alert(report)

        if alerts:
            print(f"  {len(alerts)} alert(s) generated:")
            for a in alerts:
                print(f"    [{a['level']}] {a['repo']}: {a['message_en']}")
        else:
            print("  ✓ No anomalies detected. Ecosystem is healthy.")


if __name__ == "__main__":
    main()

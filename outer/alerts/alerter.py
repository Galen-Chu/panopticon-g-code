"""
Outer Axis — Alert System · 異常警報系統

Detects anomalies in ecosystem health (repo status, open issues, stale
repos, failing CI) and delivers notifications via Slack, generic webhook,
or a GitHub issue (recommended — lands where you already read alerts).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ALERT_ISSUE_REPO = os.environ.get("PANOPTICON_REPO", "Galen-Chu/panopticon-g-code")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlertSystem:
    """Detects ecosystem anomalies and sends alerts."""

    def __init__(self):
        self.alerts_dir = DATA_DIR / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

    def check_and_alert(self, health_report: dict) -> list:
        """Check a health report for anomalies and trigger alerts."""
        alerts = []

        repos = health_report.get("repos", [])
        for repo in repos:
            # Alert on non-healthy repos
            if repo.get("status") != "healthy":
                alerts.append(self._create_alert(
                    level="warning",
                    repo=repo.get("repo", "unknown"),
                    message_en=f"Repository {repo.get('repo')} status: {repo.get('status')}",
                    message_zh=f"儲存庫 {repo.get('repo')} 狀態：{repo.get('status')}",
                ))

            # Alert on failing CI/CD pipelines
            ci = repo.get("ci", {})
            if ci.get("status") == "failing":
                failed = ci.get("failed_runs", "?")
                checked = ci.get("checked_runs", "?")
                alerts.append(self._create_alert(
                    level="warning",
                    repo=repo.get("repo", "unknown"),
                    message_en=(f"Failing CI: {failed}/{checked} recent runs failed "
                                f"in {repo.get('repo')}"),
                    message_zh=f"CI 失敗：{repo.get('repo')} 近期 {checked} 次執行中 {failed} 次失敗",
                ))

            # Alert on high open issues
            open_issues = repo.get("open_issues", 0)
            if open_issues > 10:
                alerts.append(self._create_alert(
                    level="warning",
                    repo=repo.get("repo", "unknown"),
                    message_en=f"High open issues: {open_issues} in {repo.get('repo')}",
                    message_zh=f"未解決議題過多：{repo.get('repo')} 有 {open_issues} 個",
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
                            level="info",
                            repo=repo.get("repo", "unknown"),
                            message_en=f"Stale repo: {repo.get('repo')} — no push in {days_since} days",
                            message_zh=f"儲存庫休眠：{repo.get('repo')} — {days_since} 天未推送",
                        ))

        # Save alerts
        if alerts:
            self._save_alerts(alerts)
            self._send_notifications(alerts)

        return alerts

    @staticmethod
    def _parse_timestamp(value: str):
        """Parse an ISO timestamp; naive values are treated as UTC."""
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _create_alert(self, level: str, repo: str, message_en: str, message_zh: str) -> dict:
        return {
            "timestamp": _utcnow().isoformat(),
            "level": level,
            "repo": repo,
            "message_en": message_en,
            "message_zh": message_zh,
        }

    def _save_alerts(self, alerts: list):
        """Save alerts to the data directory."""
        filepath = self.alerts_dir / f"alerts_{_utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath.write_text(
            json.dumps({"alerts": alerts, "count": len(alerts)}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _send_notifications(self, alerts: list):
        """Send notifications via configured channels."""
        # Slack webhook
        slack_webhook = os.environ.get("SLACK_WEBHOOK", "")
        if slack_webhook and requests:
            self._send_slack(slack_webhook, alerts)

        # Generic webhook
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "")
        if webhook_url and requests:
            self._send_webhook(webhook_url, alerts)

        # GitHub issue (recommended default in CI — see daily.yml)
        if os.environ.get("PANOPTICON_ALERT_ISSUES", "") == "1" and requests:
            self._send_github_issue(alerts)

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

    def _send_github_issue(self, alerts: list):
        """Open (or update) one GitHub issue per day summarizing the alerts.

        Keeps alerts where you already read them — the repo's issue tracker.
        Skips silently when GITHUB_TOKEN is not set or an issue with the
        same title is still open (no duplicates).
        """
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print("  ⚠ PANOPTICON_ALERT_ISSUES=1 but GITHUB_TOKEN not set — skipping")
            return
        headers = {"Authorization": f"Bearer {token}",
                   "Accept": "application/vnd.github+json"}
        title = f"👁️ Panopticon Alert {_utcnow().strftime('%Y-%m-%d')} — {len(alerts)} anomalies"
        try:
            # Dedupe: skip if today's issue is already open
            resp = requests.get(
                f"https://api.github.com/repos/{ALERT_ISSUE_REPO}/issues",
                headers=headers, params={"state": "open", "per_page": 50}, timeout=10)
            if resp.status_code == 200:
                if any(i.get("title") == title for i in resp.json()):
                    print("  · Issue for today already open — skip")
                    return

            body_lines = [
                "Panopticon detected the following ecosystem anomalies:",
                "Panopticon 偵測到以下生態系統異常：", "",
            ]
            for a in alerts:
                icon = "⚠️" if a["level"] == "warning" else "ℹ️"
                body_lines.append(f"{icon} **{a['repo']}** — {a['message_en']}")
                body_lines.append(f"   {a['message_zh']}")
            body_lines += ["", "---", "_Auto-generated by Panopticon Daily Cycle. "
                                  "Close after triage. 自動產生，分診後關閉。_"]

            resp = requests.post(
                f"https://api.github.com/repos/{ALERT_ISSUE_REPO}/issues",
                headers=headers, timeout=10,
                json={"title": title, "body": "\n".join(body_lines)})
            if resp.status_code == 201:
                print(f"  ✓ Alert issue created: {resp.json().get('html_url', '')}")
            else:
                print(f"  ⚠ Issue creation failed: HTTP {resp.status_code}")
        except requests.RequestException as e:
            print(f"  ⚠ GitHub issue notification failed: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Panopticon Alert System")
    parser.add_argument("--check", action="store_true", help="Check latest health report for anomalies")
    args = parser.parse_args()

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

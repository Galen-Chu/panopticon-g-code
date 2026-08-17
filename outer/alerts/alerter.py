"""
Outer Axis — Alert System · 異常警報系統

Detects anomalies in G-Code ecosystem health and sends notifications
via Slack, email, or generic webhook.
"""
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

DATA_DIR = Path(__file__).parent.parent.parent / "data"


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

            # Alert on high open issues
            open_issues = repo.get("open_issues", 0)
            if open_issues > 10:
                alerts.append(self._create_alert(
                    level="warning",
                    repo=repo.get("repo", "unknown"),
                    message_en=f"High open issues: {open_issues} in {repo.get('repo')}",
                    message_zh=f"未解決議題過多：{repo.get('repo')} 有 {open_issues} 個",
                ))

            # Alert on stale repos (no push in 30 days)
            last_push = repo.get("last_push", "")
            if last_push:
                push_date = datetime.fromisoformat(last_push.replace("Z", "+00:00"))
                days_since = (datetime.utcnow().replace(tzinfo=push_date.tzinfo) - push_date).days
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

    def _create_alert(self, level: str, repo: str, message_en: str, message_zh: str) -> dict:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "repo": repo,
            "message_en": message_en,
            "message_zh": message_zh,
        }

    def _save_alerts(self, alerts: list):
        """Save alerts to the data directory."""
        filepath = self.alerts_dir / f"alerts_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
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

    def _send_slack(self, webhook_url: str, alerts: list):
        """Send alerts to Slack."""
        try:
            text_lines = [f"👁️ Panopticon Alert ({len(alerts)} issues)"]
            for alert in alerts[:5]:
                icon = "⚠️" if alert["level"] == "warning" else "ℹ️"
                text_lines.append(f"{icon} {alert['message_en']}")

            requests.post(webhook_url, json={"text": "\n".join(text_lines)}, timeout=10)
        except Exception:
            pass  # Don't fail the monitoring on notification errors

    def _send_webhook(self, url: str, alerts: list):
        """Send alerts to a generic webhook."""
        try:
            requests.post(url, json={"alerts": alerts, "source": "panopticon"}, timeout=10)
        except Exception:
            pass


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

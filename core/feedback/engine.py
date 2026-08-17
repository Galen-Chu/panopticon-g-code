"""
Core — Feedback Engine · 回饋修正引擎

The bidirectional feedback loop between the Inner and Outer axes.
Inner observations inform ecosystem priorities; ecosystem health
reveals personal patterns. Both feed into adaptive adjustments.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class FeedbackEngine:
    """Correlates inner-axis observations with outer-axis ecosystem health."""

    def __init__(self):
        self.journal_dir = DATA_DIR / "journal"
        self.monitor_dir = DATA_DIR / "monitor"
        self.insights_dir = DATA_DIR / "insights"
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    def correlate(self) -> dict:
        """
        Find correlations between inner-axis entries and outer-axis health.

        Returns insights about how personal patterns relate to
        ecosystem states.
        """
        journal_entries = self._load_journal()
        health_reports = self._load_health()

        if not journal_entries or not health_reports:
            return {
                "status": "insufficient_data",
                "message": "Need both journal entries and health reports",
                "journal_count": len(journal_entries),
                "health_count": len(health_reports),
            }

        # Basic correlation: journal entry frequency vs. ecosystem health
        healthy_days = set()
        for report in health_reports:
            if report.get("healthy", 0) > 0:
                day = report.get("timestamp", "")[:10]
                healthy_days.add(day)

        reflection_on_healthy = 0
        reflection_on_issues = 0
        for entry in journal_entries:
            day = entry.get("date", "")
            if day in healthy_days:
                reflection_on_healthy += 1
            else:
                reflection_on_issues += 1

        insight = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "correlation",
            "data": {
                "total_reflections": len(journal_entries),
                "reflections_on_healthy_days": reflection_on_healthy,
                "reflections_on_issue_days": reflection_on_issues,
                "ecosystem_reports": len(health_reports),
                "healthy_days_observed": len(healthy_days),
                "pattern": self._interpret(reflection_on_healthy, reflection_on_issues),
            },
        }

        # Save insight
        filepath = self.insights_dir / f"insight_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath.write_text(json.dumps(insight, indent=2, ensure_ascii=False), encoding="utf-8")

        return insight

    def _interpret(self, healthy_count: int, issue_count: int) -> str:
        """Generate a bilingual interpretation of the correlation."""
        total = healthy_count + issue_count
        if total == 0:
            return "No data to interpret · 無資料可解讀"

        ratio = healthy_count / total
        if ratio > 0.7:
            return ("You tend to reflect more when the ecosystem is healthy — "
                    "a pattern of engagement during stability."
                    "你傾向在生態系統健康時進行反思——穩定時期參與度較高的模式。")
        elif ratio < 0.3:
            return ("You tend to reflect more when the ecosystem has issues — "
                    "a pattern of attention during crisis."
                    "你傾向在生態系統有問題時反思——危機時期注意力較集中的模式。")
        else:
            return ("Your reflection practice is balanced across ecosystem states — "
                    "consistent awareness regardless of external conditions."
                    "你的反思練習在各種生態狀態下保持平衡——不受外部條件影響的持續覺察。")

    def _load_journal(self) -> list:
        """Load recent journal entries."""
        entries = []
        if not self.journal_dir.exists():
            return entries
        for filepath in sorted(self.journal_dir.glob("*.json"), reverse=True)[:30]:
            try:
                entries.append(json.loads(filepath.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, KeyError):
                continue
        return entries

    def _load_health(self) -> list:
        """Load recent health reports."""
        reports = []
        if not self.monitor_dir.exists():
            return reports
        for filepath in sorted(self.monitor_dir.glob("health_*.json"), reverse=True)[:30]:
            try:
                reports.append(json.loads(filepath.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, KeyError):
                continue
        return reports


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Panopticon Feedback Engine")
    parser.add_argument("--correlate", action="store_true", help="Run correlation analysis")
    args = parser.parse_args()

    if args.correlate or not vars(args).get("any"):
        engine = FeedbackEngine()
        result = engine.correlate()
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

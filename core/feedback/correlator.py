"""
Core — Advanced Correlation Engine · 進階雙軸相關分析

Correlates inner-axis emotional patterns with outer-axis ecosystem
health to reveal deeper insights about the relationship between
personal consciousness and project ecosystem states.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class CorrelationEngine:
    """Advanced correlation between inner and outer axes."""

    def __init__(self):
        self.journal_dir = DATA_DIR / "journal"
        self.monitor_dir = DATA_DIR / "monitor"
        self.insights_dir = DATA_DIR / "insights"
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    def full_analysis(self, days: int = 30) -> dict:
        """Run full cross-axis correlation analysis."""
        journal = self._load_journal(days)
        health = self._load_health(days)

        if not journal or not health:
            return {
                "status": "insufficient_data",
                "message": "Need both journal and health data",
                "journal_count": len(journal),
                "health_count": len(health),
            }

        # Run multiple correlation analyses
        emotion_correlation = self._correlate_emotions_with_health(journal, health)
        behavior_correlation = self._correlate_behaviors_with_health(journal, health)
        timing_correlation = self._correlate_timing(journal, health)
        recommendations = self._generate_recommendations(
            emotion_correlation, behavior_correlation, timing_correlation
        )

        result = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_period_days": days,
            "emotion_correlation": emotion_correlation,
            "behavior_correlation": behavior_correlation,
            "timing_correlation": timing_correlation,
            "recommendations": recommendations,
        }

        # Save
        filepath = self.insights_dir / f"correlation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        return result

    def _correlate_emotions_with_health(self, journal: list, health: list) -> dict:
        """Find which emotions appear more on healthy vs issue days."""
        from inner.patterns.analyzer import EMOTION_KEYWORDS

        # Build day -> healthy/issues map
        day_health = {}
        for report in health:
            day = report.get("timestamp", "")[:10]
            issues = report.get("issues", 0)
            day_health[day] = "healthy" if issues == 0 else "issues"

        emotion_on_healthy = {}
        emotion_on_issues = {}

        for entry in journal:
            day = entry.get("date", "")
            context = day_health.get(day)
            if not context:
                continue

            text = entry.get("entry", "").lower()
            for emotion, keywords in EMOTION_KEYWORDS.items():
                count = sum(text.count(kw) for kw in keywords["en"])
                count += sum(entry.get("entry", "").count(kw) for kw in keywords["zh"])

                if context == "healthy":
                    emotion_on_healthy[emotion] = emotion_on_healthy.get(emotion, 0) + count
                else:
                    emotion_on_issues[emotion] = emotion_on_issues.get(emotion, 0) + count

        return {
            "emotions_on_healthy_days": dict(sorted(emotion_on_healthy.items(), key=lambda x: x[1], reverse=True)[:5]),
            "emotions_on_issue_days": dict(sorted(emotion_on_issues.items(), key=lambda x: x[1], reverse=True)[:5]),
        }

    def _correlate_behaviors_with_health(self, journal: list, health: list) -> dict:
        """Find which behavioral contexts correlate with ecosystem states."""
        from inner.patterns.analyzer import BEHAVIOR_PATTERNS

        day_health = {}
        for report in health:
            day = report.get("timestamp", "")[:10]
            issues = report.get("issues", 0)
            day_health[day] = "healthy" if issues == 0 else "issues"

        behavior_on_healthy = {}
        behavior_on_issues = {}

        for entry in journal:
            day = entry.get("date", "")
            context = day_health.get(day)
            if not context:
                continue

            text = entry.get("entry", "").lower()
            for behavior, keywords in BEHAVIOR_PATTERNS.items():
                count = sum(text.count(kw) for kw in keywords["en"] + keywords["zh"])
                if context == "healthy":
                    behavior_on_healthy[behavior] = behavior_on_healthy.get(behavior, 0) + count
                else:
                    behavior_on_issues[behavior] = behavior_on_issues.get(behavior, 0) + count

        return {
            "behaviors_on_healthy_days": dict(sorted(behavior_on_healthy.items(), key=lambda x: x[1], reverse=True)[:5]),
            "behaviors_on_issue_days": dict(sorted(behavior_on_issues.items(), key=lambda x: x[1], reverse=True)[:5]),
        }

    def _correlate_timing(self, journal: list, health: list) -> dict:
        """Analyze whether reflection timing correlates with health states."""
        journal_days = set(e.get("date", "") for e in journal)
        healthy_days = set()
        issue_days = set()

        for report in health:
            day = report.get("timestamp", "")[:10]
            if report.get("issues", 0) == 0:
                healthy_days.add(day)
            else:
                issue_days.add(day)

        reflections_on_healthy = len(journal_days & healthy_days)
        reflections_on_issues = len(journal_days & issue_days)
        total_days = len(journal_days)

        return {
            "total_reflection_days": total_days,
            "reflections_on_healthy_days": reflections_on_healthy,
            "reflections_on_issue_days": reflections_on_issues,
            "coverage_healthy": round(reflections_on_healthy / max(len(healthy_days), 1) * 100, 1),
            "coverage_issues": round(reflections_on_issues / max(len(issue_days), 1) * 100, 1),
        }

    def _generate_recommendations(self, emotions: dict, behaviors: dict, timing: dict) -> list:
        """Generate bilingual adaptive recommendations."""
        recs = []

        # Check emotion correlation
        healthy_emotions = emotions.get("emotions_on_healthy_days", {})
        issue_emotions = emotions.get("emotions_on_issue_days", {})

        top_healthy = list(healthy_emotions.keys())[:1]
        top_issue = list(issue_emotions.keys())[:1]

        if top_healthy:
            recs.append({
                "type": "amplify",
                "en": f"When ecosystem is healthy, you feel '{top_healthy[0]}'. These conditions are your growth environment — protect them.",
                "zh": f"當生態系統健康時，你感受到「{top_healthy[0]}」。這些條件是你的成長環境——保護它們。",
            })

        if top_issue and top_issue != top_healthy:
            recs.append({
                "type": "observe",
                "en": f"When ecosystem has issues, '{top_issue[0]}' emerges. This is not a problem to fix — it's a pattern to observe.",
                "zh": f"當生態系統有問題時，「{top_issue[0]}」會浮現。這不是要修復的問題——是要觀察的模式。",
            })

        # Check timing
        coverage_healthy = timing.get("coverage_healthy", 0)
        coverage_issues = timing.get("coverage_issues", 0)

        if coverage_healthy < 50 and coverage_healthy > 0:
            recs.append({
                "type": "consistency",
                "en": f"You reflect on only {coverage_healthy}% of healthy days. Consider a daily practice to build consistency.",
                "zh": f"你只在 {coverage_healthy}% 的健康日反思。考慮建立每日練習以增進一致性。",
            })

        # Always add one meta-recommendation
        recs.append({
            "type": "meta",
            "en": "The Panopticon observes without judgment. Continue watching the patterns — awareness itself is the practice.",
            "zh": "Panopticon 不帶批判地觀察。持續觀看模式——覺察本身就是練習。",
        })

        return recs

    def _load_journal(self, days: int) -> list:
        entries = []
        if not self.journal_dir.exists():
            return entries
        cutoff = datetime.now() - timedelta(days=days)
        for filepath in sorted(self.journal_dir.glob("*.json"), reverse=True):
            try:
                entry = json.loads(filepath.read_text(encoding="utf-8"))
                entry_date = entry.get("date", "")
                if entry_date and datetime.fromisoformat(entry_date) >= cutoff:
                    entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue
        return entries

    def _load_health(self, days: int) -> list:
        reports = []
        if not self.monitor_dir.exists():
            return reports
        for filepath in sorted(self.monitor_dir.glob("health_*.json"), reverse=True):
            try:
                reports.append(json.loads(filepath.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return reports[:days]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Panopticon Correlation Engine")
    parser.add_argument("--days", type=int, default=30, help="Analysis period")
    args = parser.parse_args()

    engine = CorrelationEngine()
    result = engine.full_analysis(args.days)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

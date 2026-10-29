"""Tests for the Core correlation engine."""
import json
import pytest
from datetime import datetime, date, timedelta

from core.feedback.correlator import CorrelationEngine


@pytest.fixture
def data_dir(tmp_path):
    """Create temp data with journal entries and health reports.

    Dates are generated relative to today — the journal loader only reads
    the last N days, so hardcoded dates would make the suite rot over time.
    """
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir()

    # Journal entries (dates relative to today)
    day = lambda offset: (date.today() - timedelta(days=offset)).isoformat()
    for d, text in [
        (day(3), "Feeling anxious about work"),
        (day(2), "Happy and curious about learning"),
        (day(1), "Calm morning reflection"),
        (day(0), "Anxious again, deadline approaching"),
    ]:
        (journal_dir / f"{d}.json").write_text(
            json.dumps({"date": d, "entry": text}), encoding="utf-8"
        )

    # Health reports (2 healthy, 1 with issues), timestamps matching journal dates
    reports = [
        {"timestamp": f"{day(3)}T01:00:00", "healthy": 8, "issues": 0, "repos": []},
        {"timestamp": f"{day(2)}T01:00:00", "healthy": 8, "issues": 0, "repos": []},
        {"timestamp": f"{day(1)}T01:00:00", "healthy": 7, "issues": 1, "repos": []},
    ]
    for i, report in enumerate(reports):
        stamp = report["timestamp"].replace("-", "").replace(":", "")
        (monitor_dir / f"health_{stamp}.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

    return tmp_path


class TestCorrelationEngine:
    def test_insufficient_data(self, tmp_path, monkeypatch):
        from core.feedback import correlator as corr_module
        monkeypatch.setattr(corr_module, "DATA_DIR", tmp_path)

        engine = CorrelationEngine()
        result = engine.full_analysis()
        assert result["status"] == "insufficient_data"

    def test_full_analysis_with_data(self, data_dir, monkeypatch):
        from core.feedback import correlator as corr_module
        monkeypatch.setattr(corr_module, "DATA_DIR", data_dir)

        engine = CorrelationEngine()
        result = engine.full_analysis(days=30)

        assert result["status"] == "ok"
        assert "emotion_correlation" in result
        assert "behavior_correlation" in result
        assert "timing_correlation" in result
        assert "recommendations" in result

    def test_emotions_correlated(self, data_dir, monkeypatch):
        from core.feedback import correlator as corr_module
        monkeypatch.setattr(corr_module, "DATA_DIR", data_dir)

        engine = CorrelationEngine()
        result = engine.full_analysis(days=30)

        emotions = result["emotion_correlation"]
        assert "emotions_on_healthy_days" in emotions
        assert "emotions_on_issue_days" in emotions

    def test_recommendations_are_bilingual(self, data_dir, monkeypatch):
        from core.feedback import correlator as corr_module
        monkeypatch.setattr(corr_module, "DATA_DIR", data_dir)

        engine = CorrelationEngine()
        result = engine.full_analysis(days=30)

        recs = result["recommendations"]
        assert len(recs) > 0
        for rec in recs:
            assert "en" in rec
            assert "zh" in rec
            assert len(rec["en"]) > 10
            assert len(rec["zh"]) > 5

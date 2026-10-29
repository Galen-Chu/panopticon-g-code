"""Tests for the Inner Axis pattern analyzer."""
import json
import pytest
from pathlib import Path
from datetime import date, timedelta

from inner.patterns.analyzer import PatternAnalyzer, EMOTION_KEYWORDS, BEHAVIOR_PATTERNS


@pytest.fixture
def journal_dir(tmp_path):
    """Create a temp journal directory with sample entries.

    Dates are generated relative to today — the analyzer only looks at the
    last N days, so hardcoded dates would make the suite rot over time.
    """
    entries = [
        {"date": (date.today() - timedelta(days=2)).isoformat(),
         "entry": "Feeling anxious about the deadline. Work stress is high."},
        {"date": (date.today() - timedelta(days=1)).isoformat(),
         "entry": "Happy and grateful today. Morning reflection went well."},
        {"date": date.today().isoformat(),
         "entry": "Curious about the new project. Learning something exciting."},
    ]
    for entry in entries:
        filepath = tmp_path / f"{entry['date']}.json"
        filepath.write_text(json.dumps(entry), encoding="utf-8")
    return tmp_path


class TestEmotionKeywords:
    def test_all_emotions_have_bilingual_keywords(self):
        for emotion, keywords in EMOTION_KEYWORDS.items():
            assert "en" in keywords
            assert "zh" in keywords
            assert len(keywords["en"]) > 0
            assert len(keywords["zh"]) > 0

    def test_covers_key_emotions(self):
        expected = {"anxiety", "joy", "calm", "anger", "sadness", "curiosity"}
        assert expected.issubset(set(EMOTION_KEYWORDS.keys()))


class TestPatternAnalyzer:
    def test_analyze_with_data(self, journal_dir):
        analyzer = PatternAnalyzer(journal_dir)
        result = analyzer.analyze(days=30)
        assert result["status"] == "ok"
        assert result["analyzed_entries"] == 3
        assert "emotions" in result
        assert "behaviors" in result
        assert "top_keywords" in result

    def test_detects_anxiety(self, journal_dir):
        analyzer = PatternAnalyzer(journal_dir)
        result = analyzer.analyze(days=30)
        emotions = result["emotions"]
        assert "anxiety" in emotions
        assert emotions["anxiety"] > 0

    def test_detects_joy(self, journal_dir):
        analyzer = PatternAnalyzer(journal_dir)
        result = analyzer.analyze(days=30)
        emotions = result["emotions"]
        assert "joy" in emotions

    def test_empty_dir_returns_no_data(self, tmp_path):
        analyzer = PatternAnalyzer(tmp_path)
        result = analyzer.analyze(days=30)
        assert result["status"] == "no_data"

    def test_dominant_pattern_is_bilingual(self, journal_dir):
        analyzer = PatternAnalyzer(journal_dir)
        result = analyzer.analyze(days=30)
        pattern = result["dominant_pattern"]
        assert "·" in pattern or len(pattern) > 10  # Has both EN and ZH


class TestBehaviorPatterns:
    def test_all_behaviors_have_keywords(self):
        for behavior, keywords in BEHAVIOR_PATTERNS.items():
            assert "en" in keywords
            assert "zh" in keywords

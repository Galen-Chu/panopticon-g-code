"""Tests for the Inner Axis pattern analyzer."""
import json
from datetime import date, timedelta

import pytest

from inner.patterns.analyzer import BEHAVIOR_PATTERNS, EMOTION_KEYWORDS, PatternAnalyzer


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
        for _emotion, keywords in EMOTION_KEYWORDS.items():
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
        for _behavior, keywords in BEHAVIOR_PATTERNS.items():
            assert "en" in keywords
            assert "zh" in keywords


class TestTrendDetection:
    """Direction matters: entries load newest-first, so lengths must be
    compared in chronological order or the labels come out inverted."""

    @staticmethod
    def _journal_with_lengths(directory, lengths_oldest_to_newest):
        n = len(lengths_oldest_to_newest)
        for i, length in enumerate(lengths_oldest_to_newest):
            offset = n - 1 - i  # i=0 is the oldest entry
            d = (date.today() - timedelta(days=offset)).isoformat()
            (directory / f"{d}.json").write_text(
                json.dumps({"date": d, "entry": "x" * length}), encoding="utf-8")
        return directory

    def test_deepening_when_entries_get_longer(self, tmp_path):
        journal = self._journal_with_lengths(tmp_path, [10, 12, 40, 45, 90, 100])
        result = PatternAnalyzer(journal).analyze(days=30)
        assert result["trends"]["trend"] == "deepening"

    def test_simplifying_when_entries_get_shorter(self, tmp_path):
        journal = self._journal_with_lengths(tmp_path, [100, 90, 45, 40, 12, 10])
        result = PatternAnalyzer(journal).analyze(days=30)
        assert result["trends"]["trend"] == "simplifying"

    def test_stable_when_lengths_similar(self, tmp_path):
        journal = self._journal_with_lengths(tmp_path, [50, 55, 48, 52, 50, 51])
        result = PatternAnalyzer(journal).analyze(days=30)
        assert result["trends"]["trend"] == "stable"


class TestKeywordBoundaries:
    """English keywords must not match as inner substrings."""

    @staticmethod
    def _journal(tmp_path, text):
        d = date.today().isoformat()
        (tmp_path / f"{d}.json").write_text(
            json.dumps({"date": d, "entry": text}), encoding="utf-8")
        return tmp_path

    def test_no_substring_false_positives(self, tmp_path):
        journal = self._journal(tmp_path, "I enjoy the download and uptime dashboard.")
        result = PatternAnalyzer(journal).analyze(days=30)
        assert "joy" not in result["emotions"]      # 'enjoy' ≠ joy
        assert "sadness" not in result["emotions"]  # 'down' removed entirely

    def test_inflections_still_count(self, tmp_path):
        journal = self._journal(tmp_path, "Feeling stressed and anxious today.")
        result = PatternAnalyzer(journal).analyze(days=30)
        assert result["emotions"].get("anxiety", 0) >= 2  # stressed + anxious

    def test_chinese_substring_still_matches(self, tmp_path):
        journal = self._journal(tmp_path, "今天感覺平靜，也有些焦慮。")
        result = PatternAnalyzer(journal).analyze(days=30)
        assert "calm" in result["emotions"]
        assert "anxiety" in result["emotions"]

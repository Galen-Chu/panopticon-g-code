"""Tests for the Inner Axis AI insight generator."""
import json
import pytest

from inner.insights.generator import InsightGenerator


class TestRuleBasedInsights:
    """Test the fallback rule-based insight generation (no API needed)."""

    def test_anxiety_pattern(self):
        gen = InsightGenerator(api_key="")  # No key = rule-based
        pattern = {"emotions": {"anxiety": 10}, "behaviors": {"work_related": 5}}
        result = gen._rule_based_insight(pattern)
        assert "anxiety" in result["en"].lower()
        assert "焦慮" in result["zh"]
        assert len(result["suggestion_en"]) > 10
        assert len(result["suggestion_zh"]) > 5

    def test_joy_pattern(self):
        gen = InsightGenerator(api_key="")
        pattern = {"emotions": {"joy": 8}, "behaviors": {}}
        result = gen._rule_based_insight(pattern)
        assert "joy" in result["en"].lower() or "healthy" in result["en"].lower()
        assert "喜悅" in result["zh"] or "健康" in result["zh"]

    def test_unknown_pattern(self):
        gen = InsightGenerator(api_key="")
        pattern = {"emotions": {"calm": 3}, "behaviors": {"body_awareness": 2}}
        result = gen._rule_based_insight(pattern)
        assert "calm" in result["en"].lower()
        # English emotion key appears in bilingual output (fallback behavior)
        assert "calm" in result["zh"]

    def test_empty_pattern(self):
        gen = InsightGenerator(api_key="")
        pattern = {"emotions": {}, "behaviors": {}}
        result = gen._rule_based_insight(pattern)
        assert len(result["en"]) > 10
        assert len(result["zh"]) > 5

    def test_deepening_trend(self):
        gen = InsightGenerator(api_key="")
        pattern = {
            "emotions": {"curiosity": 5},
            "behaviors": {},
            "trends": {"trend": "deepening"}
        }
        result = gen._rule_based_insight(pattern)
        assert "deepening" in result["en"].lower() or "growing" in result["en"].lower()
        assert "加深" in result["zh"] or "成長" in result["zh"]


class TestInsightGenerator:
    def test_generate_returns_structured_result(self, tmp_path, monkeypatch):
        from inner.insights import generator as gen_module
        monkeypatch.setattr(gen_module, "INSIGHTS_DIR", tmp_path)

        gen = InsightGenerator(api_key="")
        pattern = {"emotions": {"joy": 5}, "behaviors": {}, "dominant_pattern": "test"}
        result = gen.generate(pattern)

        assert result["source"] == "rules"
        assert "insight_en" in result
        assert "insight_zh" in result
        assert "suggestion_en" in result
        assert "suggestion_zh" in result
        assert result["timestamp"]

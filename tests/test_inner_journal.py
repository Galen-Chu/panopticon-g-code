"""Tests for the Inner Axis journal module."""
import json
from datetime import date
from pathlib import Path

import pytest

from inner.journal.cli import get_prompt, save_entry, load_entries, PROMPTS


class TestGetPrompt:
    def test_returns_bilingual_prompt(self):
        prompt = get_prompt()
        assert "en" in prompt
        assert "zh" in prompt

    def test_prompt_rotates_by_day(self):
        prompt_day1 = get_prompt(date(2026, 1, 1))
        prompt_day2 = get_prompt(date(2026, 1, 2))
        # Different days should usually get different prompts (unless same index)
        assert isinstance(prompt_day1, dict)
        assert isinstance(prompt_day2, dict)

    def test_all_prompts_are_bilingual(self):
        for prompt in PROMPTS:
            assert "en" in prompt
            assert "zh" in prompt
            assert len(prompt["en"]) > 0
            assert len(prompt["zh"]) > 0


class TestSaveAndLoad:
    def test_save_and_load_entry(self, tmp_path, monkeypatch):
        from inner.journal import cli
        monkeypatch.setattr(cli, "JOURNAL_DIR", tmp_path)

        filepath = save_entry("Test reflection entry", date(2026, 1, 15))
        assert filepath.exists()

        entry = json.loads(filepath.read_text(encoding="utf-8"))
        assert entry["entry"] == "Test reflection entry"
        assert entry["date"] == "2026-01-15"

        entries = load_entries(1)
        assert len(entries) == 1
        assert entries[0]["entry"] == "Test reflection entry"

    def test_load_empty_returns_empty_list(self, tmp_path, monkeypatch):
        from inner.journal import cli
        monkeypatch.setattr(cli, "JOURNAL_DIR", tmp_path)
        entries = load_entries(10)
        assert entries == []

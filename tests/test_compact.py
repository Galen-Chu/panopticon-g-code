"""Tests for the monthly data rollup."""
import json
from datetime import date

from outer.monitor.compact import compact_previous_month


def _write_report(directory, name, timestamp):
    path = directory / name
    path.write_text(json.dumps({"timestamp": timestamp, "total_repos": 10}),
                    encoding="utf-8")
    return path


class TestMonthlyRollup:
    def test_noop_mid_month(self, tmp_path):
        _write_report(tmp_path, "health_20261015_000000.json", "2026-10-15T00:00:00+00:00")
        result = compact_previous_month(tmp_path, today=date(2026, 11, 15))
        assert result is None
        assert (tmp_path / "health_20261015_000000.json").exists()

    def test_compacts_previous_month_on_the_first(self, tmp_path):
        oct1 = _write_report(tmp_path, "health_20261001_010000.json", "2026-10-01T01:00:00+00:00")
        oct2 = _write_report(tmp_path, "health_20261002_010000.json", "2026-10-02T01:00:00+00:00")
        nov1 = _write_report(tmp_path, "health_20261101_010000.json", "2026-11-01T01:00:00+00:00")

        result = compact_previous_month(tmp_path, today=date(2026, 11, 1))

        assert result == tmp_path / "monthly_202610.ndjson"
        assert not oct1.exists() and not oct2.exists()   # dailies removed
        assert nov1.exists()                             # current month untouched
        lines = result.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["timestamp"] == "2026-10-01T01:00:00+00:00"  # sorted

    def test_idempotent_and_self_healing(self, tmp_path):
        _write_report(tmp_path, "health_20261001_010000.json", "2026-10-01T01:00:00+00:00")
        _write_report(tmp_path, "health_20261002_010000.json", "2026-10-02T01:00:00+00:00")
        compact_previous_month(tmp_path, today=date(2026, 11, 1))

        # late arrivals after compaction: one duplicate, one new backfill
        _write_report(tmp_path, "health_20261001_010000.json", "2026-10-01T01:00:00+00:00")
        _write_report(tmp_path, "health_20261031_230000.json", "2026-10-31T23:00:00+00:00")

        result = compact_previous_month(tmp_path, today=date(2026, 11, 1))

        timestamps = [json.loads(line)["timestamp"]
                      for line in result.read_text(encoding="utf-8").splitlines()]
        assert timestamps == sorted(timestamps)
        assert len(timestamps) == 3            # backfill merged in…
        assert len(set(timestamps)) == 3       # …duplicates dropped

    def test_noop_when_nothing_to_do(self, tmp_path):
        result = compact_previous_month(tmp_path, today=date(2026, 11, 1))
        assert result is None

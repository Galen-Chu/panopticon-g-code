"""
Outer Axis — Monthly Data Rollup · 月度資料整併

On the first day of each month, the previous month's daily health
reports are merged into a single monthly_<YYYYMM>.ndjson and the
dailies are removed — bounded file count, full history retained.
Mirrors the vault's compile-monthly philosophy: CI does the mechanical
merge, humans (or LLMs) do the narrative.
"""
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

MONITOR_DIR = Path(__file__).parent.parent.parent / "data" / "monitor"


def compact_previous_month(monitor_dir: Path = None, today: date = None) -> Path:
    """Merge last month's health_*.json reports into monthly_<YYYYMM>.ndjson.

    No-op (returns None) unless today is the 1st of a month. Idempotent
    and self-healing: if the monthly file already exists, late-arriving
    dailies are merged in (deduped by timestamp, sorted) instead of
    being lost. Returns the monthly file path when compaction ran.
    """
    today = today or datetime.now(UTC).date()
    if today.day != 1:
        return None

    month = (today - timedelta(days=1)).strftime("%Y%m")
    directory = monitor_dir or MONITOR_DIR
    monthly = directory / f"monthly_{month}.ndjson"
    dailies = sorted(directory.glob(f"health_{month}*.json"))
    if not dailies and not monthly.exists():
        return None

    # key by timestamp → dedupe; late backfills overwrite same-timestamp copies
    entries = {}
    if monthly.exists():
        for line in monthly.read_text(encoding="utf-8").splitlines():
            if line.strip():
                report = json.loads(line)
                entries[report["timestamp"]] = report
    for path in dailies:
        report = json.loads(path.read_text(encoding="utf-8"))
        entries[report["timestamp"]] = report

    monthly.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entries[key], ensure_ascii=False) for key in sorted(entries)]
    monthly.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for path in dailies:
        path.unlink()

    print(f"  Compacted {len(dailies)} daily report(s) → {monthly.name}")
    return monthly


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    result = compact_previous_month()
    if result:
        print(f"  Monthly rollup written: {result}")
    else:
        print("  Not the 1st of the month (or nothing to compact) — no-op.")


if __name__ == "__main__":
    main()

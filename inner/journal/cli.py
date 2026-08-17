"""
Inner Axis — Self-Reflection Journal · 自我反思日誌

Daily consciousness observation prompts and entry management.
Part of the Panopticon G-Code dual-axis awareness system.
"""
import os
import json
from datetime import datetime, date
from pathlib import Path

# Journal storage directory (relative to project root)
JOURNAL_DIR = Path(__file__).parent.parent.parent / "data" / "journal"

# Bilingual daily prompts — rotate through the month
PROMPTS = [
    {"en": "What pattern did you notice in your thoughts today?",
     "zh": "今天你注意到自己的思考有什麼模式？"},
    {"en": "What emotion was most present, and what triggered it?",
     "zh": "今天最主要的情緒是什麼？什麼觸發了它？"},
    {"en": "Where did your attention go when it wandered?",
     "zh": "當注意力遊走時，它去了哪裡？"},
    {"en": "What did you observe about your reactions today?",
     "zh": "今天你觀察到自己有什麼反應模式？"},
    {"en": "What is one thing you see now that you didn't see yesterday?",
     "zh": "有什麼是你現在看到、但昨天沒看到的？"},
    {"en": "How did your body feel during moments of stress?",
     "zh": "在壓力時刻，你的身體有什麼感覺？"},
    {"en": "What did you avoid observing about yourself today?",
     "zh": "今天你迴避觀察自己什麼？"},
]


def get_prompt(for_date: date = None) -> dict:
    """Return the prompt for the given date (rotates daily)."""
    if for_date is None:
        for_date = date.today()
    index = for_date.timetuple().tm_yday % len(PROMPTS)
    return PROMPTS[index]


def save_entry(entry_text: str, for_date: date = None) -> Path:
    """Save a journal entry to the data directory."""
    if for_date is None:
        for_date = date.today()

    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    filepath = JOURNAL_DIR / f"{for_date.isoformat()}.json"

    entry = {
        "date": for_date.isoformat(),
        "timestamp": datetime.utcnow().isoformat(),
        "prompt": get_prompt(for_date),
        "entry": entry_text,
    }

    filepath.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return filepath


def load_entries(days: int = 30) -> list:
    """Load the last N days of journal entries."""
    entries = []
    if not JOURNAL_DIR.exists():
        return entries

    for filepath in sorted(JOURNAL_DIR.glob("*.json"), reverse=True):
        try:
            entry = json.loads(filepath.read_text(encoding="utf-8"))
            entries.append(entry)
            if len(entries) >= days:
                break
        except (json.JSONDecodeError, KeyError):
            continue

    return entries


def main():
    """CLI entry point — run daily via cron or GitHub Actions."""
    import argparse

    parser = argparse.ArgumentParser(description="Panopticon Inner Axis — Self-Reflection Journal")
    parser.add_argument("--today", action="store_true", help="Show today's prompt")
    parser.add_argument("--write", type=str, help="Write an entry directly")
    parser.add_argument("--review", type=int, metavar="N", help="Review last N entries")
    args = parser.parse_args()

    if args.today or not any(vars(args).values()):
        prompt = get_prompt()
        print(f"\n{'='*50}")
        print(f"  Panopticon Daily Reflection")
        print(f"  {date.today().isoformat()}")
        print(f"{'='*50}\n")
        print(f"  {prompt['en']}")
        print(f"  {prompt['zh']}\n")
        print(f"{'='*50}")
        print(f"  Usage: python -m inner.journal.cli --write 'your reflection'")
        print(f"{'='*50}\n")

    elif args.write:
        filepath = save_entry(args.write)
        print(f"Entry saved: {filepath}")

    elif args.review:
        entries = load_entries(args.review)
        for entry in entries:
            print(f"\n--- {entry['date']} ---")
            print(f"Prompt: {entry['prompt']['en']}")
            print(f"Entry: {entry['entry'][:200]}...")


if __name__ == "__main__":
    main()

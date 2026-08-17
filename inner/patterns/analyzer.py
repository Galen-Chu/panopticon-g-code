"""
Inner Axis — Pattern Recognition · 模式偵測

Analyzes journal entries to identify recurring thoughts, emotions,
and behavioral patterns over time.
"""
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Bilingual emotion keywords for pattern detection
EMOTION_KEYWORDS = {
    "anxiety": {"en": ["anxious", "worried", "nervous", "stress", "fear"],
                "zh": ["焦慮", "擔心", "緊張", "壓力", "恐懼"]},
    "joy": {"en": ["happy", "joy", "excited", "grateful", "delight"],
            "zh": ["開心", "快樂", "興奮", "感恩", "喜悅"]},
    "calm": {"en": ["calm", "peaceful", "relaxed", "still", "quiet"],
             "zh": ["平靜", "安寧", "放鬆", "安靜"]},
    "anger": {"en": ["angry", "frustrated", "irritated", "annoyed"],
              "zh": ["生氣", "沮喪", "煩躁", "惱怒"]},
    "sadness": {"en": ["sad", "down", "depressed", "lonely", "empty"],
                "zh": ["難過", "低落", "憂鬱", "孤獨", "空虛"]},
    "curiosity": {"en": ["curious", "wonder", "explore", "discover", "learn"],
                  "zh": ["好奇", "想知道", "探索", "發現", "學習"]},
    "focus": {"en": ["focus", "concentrate", "clear", "productive"],
              "zh": ["專注", "清晰", "效率", "投入"]},
    "avoidance": {"en": ["avoid", "procrastinate", "escape", "distract"],
                  "zh": ["逃避", "拖延", "分心", "迴避"]},
}

# Common behavior/action patterns
BEHAVIOR_PATTERNS = {
    "morning_reflection": {"en": ["morning", "wake", "early"],
                            "zh": ["早上", "醒來", "清晨"]},
    "evening_reflection": {"en": ["evening", "night", "before sleep", "end of day"],
                            "zh": ["晚上", "睡前", "夜裡", "今天結束"]},
    "work_related": {"en": ["work", "project", "code", "meeting", "deadline"],
                     "zh": ["工作", "專案", "程式", "會議", "截止"]},
    "relationship": {"en": ["friend", "family", "partner", "talk", "conversation"],
                     "zh": ["朋友", "家人", "伴侶", "對話", "聊天"]},
    "body_awareness": {"en": ["body", "tired", "energy", "breath", "sleep"],
                        "zh": ["身體", "累", "能量", "呼吸", "睡眠"]},
}


class PatternAnalyzer:
    """Detects emotional and behavioral patterns in journal entries."""

    def __init__(self, journal_dir: Path):
        self.journal_dir = journal_dir

    def analyze(self, days: int = 30) -> dict:
        """Run full pattern analysis on the last N days of entries."""
        entries = self._load_entries(days)

        if not entries:
            return {"status": "no_data", "message": "No journal entries to analyze"}

        emotions = self._detect_emotions(entries)
        behaviors = self._detect_behaviors(entries)
        keywords = self._extract_keywords(entries)
        trends = self._detect_trends(entries)

        return {
            "status": "ok",
            "analyzed_entries": len(entries),
            "period_days": days,
            "emotions": emotions,
            "behaviors": behaviors,
            "top_keywords": keywords,
            "trends": trends,
            "dominant_pattern": self._interpret_pattern(emotions, behaviors),
        }

    def _detect_emotions(self, entries: list) -> dict:
        """Count emotion keyword occurrences across all entries."""
        emotion_counts = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            count = 0
            for entry in entries:
                text = entry.get("entry", "").lower()
                for kw in keywords["en"]:
                    count += text.count(kw)
                for kw in keywords["zh"]:
                    count += entry.get("entry", "").count(kw)
            if count > 0:
                emotion_counts[emotion] = count
        return dict(sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True))

    def _detect_behaviors(self, entries: list) -> dict:
        """Detect behavioral patterns from entry text."""
        behavior_counts = {}
        for behavior, keywords in BEHAVIOR_PATTERNS.items():
            count = 0
            for entry in entries:
                text = entry.get("entry", "").lower()
                for kw in keywords["en"] + keywords["zh"]:
                    count += text.count(kw)
            if count > 0:
                behavior_counts[behavior] = count
        return dict(sorted(behavior_counts.items(), key=lambda x: x[1], reverse=True))

    def _extract_keywords(self, entries: list, top_n: int = 10) -> list:
        """Extract frequently occurring meaningful words."""
        # Combine all text
        all_text = " ".join(entry.get("entry", "") for entry in entries)

        # Simple word frequency (skip common stop words)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "of",
                      "in", "it", "I", "my", "and", "that", "for", "with", "not",
                      "this", "but", "have", "had", "you", "be", "at", "on", "so",
                      "的", "是", "了", "我", "有", "和", "在", "這", "也", "不", "就"}
        words = re.findall(r'[a-zA-Z一-鿿]{2,}', all_text.lower())
        meaningful = [w for w in words if w not in stop_words]
        return Counter(meaningful).most_common(top_n)

    def _detect_trends(self, entries: list) -> dict:
        """Detect simple trends (increasing/decreasing reflection length)."""
        if len(entries) < 2:
            return {"trend": "insufficient_data"}

        # Compare first half vs second half
        mid = len(entries) // 2
        first_half = [len(e.get("entry", "")) for e in entries[:mid]]
        second_half = [len(e.get("entry", "")) for e in entries[mid:]]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        if avg_second > avg_first * 1.2:
            trend = "deepening"  # entries getting longer
        elif avg_second < avg_first * 0.8:
            trend = "simplifying"  # entries getting shorter
        else:
            trend = "stable"

        return {
            "trend": trend,
            "avg_length_first_half": round(avg_first),
            "avg_length_second_half": round(avg_second),
        }

    def _interpret_pattern(self, emotions: dict, behaviors: dict) -> str:
        """Generate a bilingual interpretation of the dominant pattern."""
        if not emotions and not behaviors:
            return "No clear pattern detected yet · 尚未偵測到明確模式"

        top_emotion = list(emotions.keys())[0] if emotions else "unknown"
        top_behavior = list(behaviors.keys())[0] if behaviors else "unknown"

        return (f"Dominant emotion: {top_emotion}, dominant context: {top_behavior}. "
                f"This combination may reveal a recurring theme in your awareness. "
                f"主要情緒：{top_emotion}，主要情境：{top_behavior}。"
                f"這個組合可能揭示了覺察中反覆出現的主題。")

    def _load_entries(self, days: int) -> list:
        """Load journal entries from the last N days."""
        entries = []
        if not self.journal_dir.exists():
            return entries

        for filepath in sorted(self.journal_dir.glob("*.json"), reverse=True):
            try:
                entry = json.loads(filepath.read_text(encoding="utf-8"))
                # Check date within range
                entry_date = entry.get("date", "")
                if entry_date:
                    entry_dt = datetime.fromisoformat(entry_date)
                    cutoff = datetime.now() - timedelta(days=days)
                    if entry_dt >= cutoff:
                        entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

        return entries


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Panopticon Pattern Analyzer")
    parser.add_argument("--days", type=int, default=30, help="Analyze last N days")
    args = parser.parse_args()

    journal_dir = Path(__file__).parent.parent.parent / "data" / "journal"
    analyzer = PatternAnalyzer(journal_dir)
    result = analyzer.analyze(args.days)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

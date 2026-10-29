"""
Inner Axis — AI Insight Generator · AI 洞察生成

Uses Google Gemini to transform pattern analysis results into
bilingual, actionable insights. Falls back to rule-based
insights when the API is unavailable (logged, never silent).
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

INSIGHTS_DIR = Path(__file__).parent.parent.parent / "data" / "insights"

# gemini-1.5-pro 已下線、google-generativeai 舊 SDK 已淘汰 —— 與 sync-g-code
# 一致改用 google-genai SDK 與現行模型
GEMINI_MODEL = "gemini-3.6-flash"
RETRYABLE_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 15

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "en": {"type": "string", "description": "2-3 sentence insight in English"},
        "zh": {"type": "string", "description": "2-3 sentence insight in Traditional Chinese (繁體中文)"},
        "suggestion_en": {"type": "string", "description": "One actionable suggestion in English"},
        "suggestion_zh": {"type": "string", "description": "One actionable suggestion in Traditional Chinese (繁體中文)"},
    },
    "required": ["en", "zh", "suggestion_en", "suggestion_zh"],
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InsightGenerator:
    """Generates insights from pattern analysis using Gemini AI or rules."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.client = None

    def _init_gemini(self) -> bool:
        """Initialize the google-genai client if an API key is available."""
        if not self.api_key:
            return False
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            return True
        except ImportError:
            print("  ⚠ google-genai not installed — using rule-based insights")
            return False
        except Exception as e:
            print(f"  ⚠ Gemini client init failed ({e}) — using rule-based insights")
            return False

    def generate(self, pattern_data: dict) -> dict:
        """
        Generate an insight from pattern analysis results.

        Uses Gemini AI when available; falls back to rule-based insights.
        """
        timestamp = _utcnow().isoformat()

        if self._init_gemini():
            insight_text, source = self._gemini_insight(pattern_data)
        else:
            insight_text, source = self._rule_based_insight(pattern_data), "rules"

        result = {
            "timestamp": timestamp,
            "source": source,
            "pattern_input": pattern_data.get("dominant_pattern", ""),
            "insight_en": insight_text.get("en", ""),
            "insight_zh": insight_text.get("zh", ""),
            "suggestion_en": insight_text.get("suggestion_en", ""),
            "suggestion_zh": insight_text.get("suggestion_zh", ""),
        }

        # Save to file
        INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = INSIGHTS_DIR / f"insight_{_utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        return result

    def _gemini_insight(self, pattern_data: dict) -> tuple:
        """Generate insight using Gemini AI. Returns (insight, source)."""
        from google.genai import errors as genai_errors
        from google.genai import types

        prompt = self._build_prompt(pattern_data)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        )

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL, contents=prompt, config=config)
                parsed = json.loads(response.text)
                missing = [k for k in RESPONSE_SCHEMA["required"] if not parsed.get(k)]
                if missing:
                    raise ValueError(f"missing keys: {', '.join(missing)}")
                return parsed, "gemini"
            except genai_errors.APIError as e:
                code = getattr(e, "code", None)
                if code not in RETRYABLE_CODES or attempt == MAX_ATTEMPTS:
                    print(f"  ⚠ Gemini API failed (HTTP {code}) — using rule-based insights")
                    break
                print(f"  ⚠ Gemini API transient error (HTTP {code}), "
                      f"retry {attempt}/{MAX_ATTEMPTS - 1} in {BACKOFF_SECONDS}s…")
                time.sleep(BACKOFF_SECONDS)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"  ⚠ Gemini response unparsable ({e}) — using rule-based insights")
                break

        return self._rule_based_insight(pattern_data), "rules"

    def _build_prompt(self, pattern_data: dict) -> str:
        """Build a bilingual prompt for Gemini."""
        emotions = json.dumps(pattern_data.get("emotions", {}), ensure_ascii=False)
        behaviors = json.dumps(pattern_data.get("behaviors", {}), ensure_ascii=False)
        trends = json.dumps(pattern_data.get("trends", {}), ensure_ascii=False)
        keywords = [kw for kw, _ in pattern_data.get("top_keywords", [])[:5]]

        return f"""
You are a Panopticon awareness guide. Analyze these self-reflection
patterns and provide actionable insights.

Pattern data:
- Emotions detected: {emotions}
- Behavioral contexts: {behaviors}
- Reflection trend: {trends}
- Top keywords: {keywords}

Tone: Rational, technical, grounding. No mystical language.
"""

    def _rule_based_insight(self, pattern_data: dict) -> dict:
        """Generate insight using predefined rules (no AI needed)."""
        emotions = pattern_data.get("emotions", {})
        behaviors = pattern_data.get("behaviors", {})
        trends = pattern_data.get("trends", {}).get("trend", "unknown")

        top_emotion = list(emotions.keys())[0] if emotions else "unknown"
        top_behavior = list(behaviors.keys())[0] if behaviors else "unknown"

        # Build bilingual insight
        if top_emotion == "anxiety":
            insight_en = f"Your dominant emotional pattern is anxiety, often occurring in {top_behavior} contexts. This suggests a stress-response cycle that may benefit from grounding practices."
            insight_zh = f"你的主導情緒模式是焦慮，常出現在{top_behavior}相關的情境。這暗示一個壓力反應循環，可能受益於接地練習。"
            sugg_en = "Try a 5-minute breathing exercise before entering the triggering context."
            sugg_zh = "在進入觸發情境前，嘗試五分鐘的呼吸練習。"

        elif top_emotion == "joy":
            insight_en = f"Joy is your most frequent emotional state, particularly in {top_behavior} contexts. This indicates a healthy engagement pattern."
            insight_zh = f"喜悅是你最頻繁的情緒狀態，特別是在{top_behavior}情境中。這顯示健康的參與模式。"
            sugg_en = "Note what conditions enable this joy — they are your growth accelerators."
            sugg_zh = "記錄促成這份喜悅的條件——它們是你的成長加速器。"

        elif top_emotion == "curiosity":
            insight_en = f"Curiosity drives your observations, especially around {top_behavior}. This is a learning-oriented awareness pattern."
            insight_zh = f"好奇心驅動你的觀察，特別是在{top_behavior}方面。這是一個學習導向的覺察模式。"
            sugg_en = "Channel this curiosity into a specific exploration project this week."
            sugg_zh = "本週將這份好奇心導向一個具體的探索專案。"

        elif top_emotion == "avoidance":
            insight_en = f"Avoidance appears frequently in your reflections, often connected to {top_behavior}. This pattern deserves compassionate attention."
            insight_zh = f"逃避在你的反思中頻繁出現，常與{top_behavior}相關。這個模式值得溫柔的關注。"
            sugg_en = "Identify one small step toward the thing you're avoiding — not to overcome, but to observe."
            sugg_zh = "找出一步你可以對正在逃避的事物採取的小行動——不是為了克服，而是為了觀察。"

        else:
            insight_en = f"Your awareness shows {top_emotion} as the dominant pattern in {top_behavior} contexts. Continue observing without judgment."
            insight_zh = f"你的覺察顯示{top_emotion}是{top_behavior}情境中的主導模式。繼續不帶批判地觀察。"
            sugg_en = "Write one sentence about what you want to observe more closely tomorrow."
            sugg_zh = "寫一句話描述明天想更仔細觀察什麼。"

        # Add trend interpretation
        if trends == "deepening":
            insight_en += " Your reflections are deepening over time — a sign of growing self-awareness."
            insight_zh += " 你的反思隨時間加深——這是自我覺察成長的跡象。"
        elif trends == "simplifying":
            insight_en += " Your reflections are becoming more concise — distilling to essentials."
            insight_zh += " 你的反思變得更精簡——提煉到本質。"

        return {
            "en": insight_en,
            "zh": insight_zh,
            "suggestion_en": sugg_en,
            "suggestion_zh": sugg_zh,
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Panopticon AI Insight Generator")
    parser.add_argument("--analyze", action="store_true", help="Run pattern analysis then generate insight")
    parser.add_argument("--from-json", type=str, help="Generate insight from a pattern JSON file")
    args = parser.parse_args()

    generator = InsightGenerator()

    if args.from_json:
        pattern_data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    elif args.analyze:
        from inner.patterns.analyzer import PatternAnalyzer
        journal_dir = Path(__file__).parent.parent.parent / "data" / "journal"
        analyzer = PatternAnalyzer(journal_dir)
        pattern_data = analyzer.analyze()
    else:
        print("Usage: python -m inner.insights.generator --analyze")
        return

    result = generator.generate(pattern_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

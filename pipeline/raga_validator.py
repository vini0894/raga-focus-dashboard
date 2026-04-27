"""
Raga-mood fit validator using Claude API + local CSV cache.

Answers: "Is Raga X appropriate for [mood] music?"
Returns: fit (strong/ok/caution/avoid), reason, alternatives.

Cache-first: results stored in data/raga_fit_cache.csv.
Claude is only called on cache miss — zero cost on repeated runs.

Usage:
    from raga_validator import validate_raga_for_mood
    result = validate_raga_for_mood("bhairavi", "sleep")
    # {"fit": "avoid", "reason": "...", "alternatives": ["darbari", "malkauns"], "cached": True}
"""

import json
import csv
import os
from pathlib import Path
from datetime import date

HERE = Path(__file__).parent
DATA_DIR = HERE.parent / "data"
CACHE_CSV = DATA_DIR / "raga_fit_cache.csv"
CACHE_HEADERS = ["raga", "mood", "fit", "reason", "alternatives", "cached_on"]

# Classical raga knowledge — cached system prompt so repeated calls are cheap
_SYSTEM_PROMPT = """You are an expert in Hindustani classical music and its therapeutic/meditative application in YouTube content.

Your task: evaluate whether a specific raga is appropriate for a given emotional/mood context in music content.

## Classical raga reference (Hindustani convention)

| Raga | Time | Mood | Sleep/rest? | Anxiety/calm? | Notes |
|---|---|---|---|---|---|
| Yaman | Evening | Peace, expansion | ✅ Strong | ✅ Strong | Most versatile calm raga |
| Bhupali | Evening | Serenity | ✅ Strong | ✅ Strong | Simple, open, very accessible |
| Darbari Kanada | Deep night | Grandeur, introspection | ✅ Strong | ✅ ok | Best for insomnia, midnight |
| Malkauns | Midnight | Depth, stillness | ✅ Strong | ⚠️ Heavy | Profound; can feel intense |
| Bageshri | Late night | Longing, tenderness | ✅ ok | ✅ ok | Gentle night raga |
| Kafi | Late evening | Romance, wistfulness | ⚠️ ok | ✅ ok | Slightly bittersweet |
| Puriya | Evening | Pathos, yearning | ⚠️ Caution | ✅ ok | Can feel melancholic |
| Bhimpalasi | Afternoon | Longing | ❌ Avoid | ✅ ok | Wrong time for sleep |
| Bhairavi | Morning | Devotional, tender | ❌ Avoid for late sleep | ✅ ok | Good for dawn/morning |
| Bilawal | Morning | Cheerful, bright | ❌ Avoid | ❌ Avoid | Too uplifting for calm |
| Todi | Morning | Yearning, searching | ❌ Avoid | ⚠️ Caution | Intense; not for sleep |
| Hamir | Late evening | Majestic | ⚠️ Caution | ✅ ok | Rich but slightly grand |
| Chandra | Night | Lunar, meditative | ✅ Strong | ✅ Strong | Rare; very suitable |

## Fit levels
- **strong**: Classical convention and mood perfectly aligned. Recommend without hesitation.
- **ok**: Works with minor caveats. Fine to use.
- **caution**: Possible but not ideal. Worth testing. Flag the caveat.
- **avoid**: Wrong time-of-day character or emotional tone for this mood. Suggest alternatives.

## Response format — JSON only, no markdown
{
  "fit": "strong|ok|caution|avoid",
  "reason": "One clear sentence. State the time-of-day, mood character, and why it does or does not match.",
  "alternatives": ["raga1", "raga2"]
}
- alternatives: only include if fit is "caution" or "avoid". Use lowercase raga names.
- reason: max 20 words. Direct. No hedging."""


def _load_cache() -> dict:
    if not CACHE_CSV.exists():
        return {}
    with open(CACHE_CSV, newline="") as f:
        return {(r["raga"].lower(), r["mood"].lower()): r for r in csv.DictReader(f)}


def _write_cache(cache: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(CACHE_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CACHE_HEADERS)
        w.writeheader()
        for row in cache.values():
            w.writerow(row)


def _call_claude(raga: str, mood: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f'Evaluate Raga {raga.title()} for "{mood}" music content.'}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if model wraps output
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def validate_raga_for_mood(raga: str, mood: str, force_refresh: bool = False) -> dict:
    """
    Returns fit signal for (raga, mood) pair.
    Reads from raga_fit_cache.csv first; calls Claude only on miss.

    Return shape:
        {fit: str, reason: str, alternatives: list[str], cached: bool}
    """
    raga = raga.strip().lower()
    mood = mood.strip().lower()

    cache = _load_cache()
    key = (raga, mood)

    if not force_refresh and key in cache:
        row = cache[key]
        alts = [a.strip() for a in row["alternatives"].split("|") if a.strip()]
        return {"fit": row["fit"], "reason": row["reason"], "alternatives": alts, "cached": True}

    try:
        result = _call_claude(raga, mood)
    except Exception as e:
        return {"fit": "unknown", "reason": f"Validator unavailable: {e}", "alternatives": [], "cached": False}

    fit = result.get("fit", "caution")
    reason = result.get("reason", "")
    alternatives = result.get("alternatives", [])

    cache[key] = {
        "raga": raga,
        "mood": mood,
        "fit": fit,
        "reason": reason,
        "alternatives": "|".join(alternatives),
        "cached_on": date.today().isoformat(),
    }
    _write_cache(cache)

    return {"fit": fit, "reason": reason, "alternatives": alternatives, "cached": False}


def mood_from_problem_kw(problem_kw: str) -> str:
    """Extract canonical mood bucket from a problem keyword string."""
    p = problem_kw.lower()
    if any(x in p for x in ("sleep", "insomnia", "asleep", "deep rest", "rest music")):
        return "sleep"
    if any(x in p for x in ("anxiety", "anxious", "worry", "worried", "panic")):
        return "anxiety"
    if any(x in p for x in ("stress", "stressed")):
        return "stress"
    if any(x in p for x in ("overthink", "racing thoughts", "mind")):
        return "overthinking"
    if any(x in p for x in ("focus", "adhd", "concentration", "brain fog")):
        return "focus"
    if any(x in p for x in ("meditat",)):
        return "meditation"
    if any(x in p for x in ("emotional", "emotion", "grief", "sad", "lonely")):
        return "emotional"
    if any(x in p for x in ("morning", "wake", "energi")):
        return "morning"
    if any(x in p for x in ("unwind", "evening", "wind down")):
        return "unwind"
    return p  # pass through — Claude handles it

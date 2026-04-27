"""
Raga-mood fit lookup — CSV-backed, human-curated.

This module does NOT call any LLM API. The fit knowledge lives in
data/raga_fit_cache.csv, which is curated by Claude in chat (the user
pastes new (raga, mood) questions to Claude, gets a structured verdict,
appends it to the CSV).

Usage:
    from raga_validator import lookup_raga_fit, mood_from_problem_kw, build_ask_prompt

    result = lookup_raga_fit("bhairavi", "sleep")
    # → {"fit": "avoid", "reason": "...", "alternatives": ["darbari", "malkauns"]}
    # → None if (raga, mood) not in cache

    mood = mood_from_problem_kw("deep rest music")  # → "sleep"

    prompt = build_ask_prompt("bhairavi", "sleep")  # ready-to-paste text for Claude chat
"""

import csv
from pathlib import Path
from typing import Optional

HERE = Path(__file__).parent
DATA_DIR = HERE.parent / "data"
CACHE_CSV = DATA_DIR / "raga_fit_cache.csv"
CACHE_HEADERS = ["raga", "mood", "fit", "reason", "alternatives", "cached_on"]


def lookup_raga_fit(raga: str, mood: str) -> Optional[dict]:
    """Read fit verdict from CSV cache. Returns None if not cached."""
    if not CACHE_CSV.exists():
        return None
    raga = raga.strip().lower()
    mood = mood.strip().lower()
    with open(CACHE_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["raga"].strip().lower() == raga and row["mood"].strip().lower() == mood:
                alts = [a.strip() for a in row.get("alternatives", "").split("|") if a.strip()]
                return {
                    "fit":          row["fit"],
                    "reason":       row["reason"],
                    "alternatives": alts,
                    "cached_on":    row.get("cached_on", ""),
                }
    return None


def mood_from_problem_kw(problem_kw: str) -> str:
    """
    Extract canonical mood bucket from a problem keyword string.

    Compound moods (time + mood) take precedence — they map to different
    raga sets than the generic mood. Example: "morning anxiety" requires
    morning ragas (Bilawal, Bhairavi) which are 'avoid' for generic anxiety.
    """
    p = (problem_kw or "").lower()
    is_morning = any(x in p for x in ("morning", "wake", "dawn", "sunrise", "early"))
    is_night   = any(x in p for x in ("night", "midnight", "late-night", "late night", "insomnia"))

    if any(x in p for x in ("anxiety", "anxious", "worry", "worried", "panic", "nervous")):
        if is_morning: return "morning_anxiety"
        if is_night:   return "night_anxiety"
        return "anxiety"
    if any(x in p for x in ("overthink", "racing thoughts", "overactive", "racing mind")):
        if is_morning: return "morning_overthinking"
        if is_night:   return "night_overthinking"
        return "overthinking"
    if any(x in p for x in ("stress", "stressed", "tension")):
        if is_morning: return "morning_stress"
        return "stress"
    if any(x in p for x in ("sleep", "insomnia", "asleep", "deep rest", "rest music")):
        return "sleep"
    if any(x in p for x in ("focus", "adhd", "concentration", "brain fog")):
        return "focus"
    if "meditat" in p:
        return "meditation"
    if any(x in p for x in ("emotional", "emotion", "grief", "sad", "lonely")):
        return "emotional"
    if any(x in p for x in ("morning", "wake", "energi", "dawn", "sunrise")):
        return "morning"
    if any(x in p for x in ("unwind", "evening", "wind down")):
        return "unwind"
    return p


def build_ask_prompt(raga: str, mood: str) -> str:
    """
    Return a ready-to-paste prompt for Claude chat. User pastes this into
    their Claude conversation, gets back the JSON, then appends to CSV.
    """
    raga_clean = raga.strip().lower().removeprefix("raga ")
    return (
        f"Validate raga fit for our YouTube content:\n\n"
        f"- Raga: **{raga_clean.title()}**\n"
        f"- Target mood: **{mood}** music\n\n"
        f"Reply in this exact JSON shape (no markdown):\n"
        f'{{"fit": "strong|ok|caution|avoid", '
        f'"reason": "one sentence explaining why", '
        f'"alternatives": ["raga1", "raga2"]}}\n\n'
        f"Then append the row to `raga-focus-dashboard/data/raga_fit_cache.csv`."
    )


def append_to_cache(raga: str, mood: str, fit: str, reason: str, alternatives: list, cached_on: str = ""):
    """Append a new fit verdict to the cache CSV. Used when curating new entries."""
    from datetime import date
    raga = raga.strip().lower()
    mood = mood.strip().lower()
    cached_on = cached_on or date.today().isoformat()

    DATA_DIR.mkdir(exist_ok=True)
    file_exists = CACHE_CSV.exists()
    with open(CACHE_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(CACHE_HEADERS)
        w.writerow([raga, mood, fit, reason, "|".join(alternatives), cached_on])

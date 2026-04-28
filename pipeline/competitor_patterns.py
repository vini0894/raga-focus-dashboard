"""
Competitor title pattern adaptation.

Given a candidate's mood, find the highest-view competitor title that targeted
the same mood, extract its structural template, and substitute our candidate's
keywords (raga, hz, instrument) into the proven structure.

Source data: data/competitor_raga_usage.csv (refreshed by competitor_raga_intel.py).

Why this matters: competitor patterns are empirical evidence of what's clicking
on YouTube right now. A 176K-view title structure beats classical theory for
title engineering. We borrow the structure, swap in our keywords.

Caveat: with only ~12 named-raga data points, any single pattern is one
data point of evidence. The function returns the source title + view count
so callers can surface this transparency in UI.

Usage:
    from competitor_patterns import find_competitor_pattern, apply_pattern_to_candidate

    result = apply_pattern_to_candidate(
        comp={"raga": {"name": "bhupali"}, "hz": {"hz": "174Hz"}, "instrument": {"name": "Tanpura"}},
        mood="night_anxiety",
    )
    # → {"title": "Calm an Overactive Mind 🌙 | 174Hz Tanpura Raga Bhupali for Deep Nervous System Healing",
    #    "source_title": "Calm an Overactive Mind 🌙 | 210Hz Chandra Raga for Deep Nervous System Healing",
    #    "source_views": 176761, "source_channel": "Raga Heal"}
    # → None if no competitor data for this mood
"""

import csv
import re
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
USAGE_CSV = HERE.parent / "data" / "competitor_raga_usage.csv"

# Common Hindustani instruments — used to detect/swap competitor instrument with ours
KNOWN_INSTRUMENTS = [
    "Bansuri", "Sitar", "Veena", "Sarangi", "Sarod", "Tanpura",
    "Dilruba", "Esraj", "Santoor", "Shehnai", "Tabla", "Flute",
]


def _load_competitor_usage() -> list:
    if not USAGE_CSV.exists():
        return []
    with open(USAGE_CSV, newline="") as f:
        return list(csv.DictReader(f))


def find_competitor_pattern(mood: str) -> Optional[dict]:
    """
    Return the highest-view competitor title for this mood.

    Fallback rules (do NOT cross time-of-day boundaries — a morning_anxiety
    pattern's "Morning Anxiety?" hook is semantically wrong for night_anxiety):
      1. Exact match on mood
      2. If mood is compound (e.g. morning_anxiety), try other compounds with
         the SAME time prefix (morning_*) before giving up
      3. If mood is base (e.g. anxiety), only match other base moods — never
         pull from compounds

    Returns dict {title, views, channel, raga, mood_matched} or None.
    """
    rows = _load_competitor_usage()
    if not rows:
        return None

    mood_l = mood.lower()
    matches = [r for r in rows if r.get("mood", "").lower() == mood_l]

    if not matches:
        time_prefix_match = re.match(r"^(morning_|night_|evening_)", mood_l)
        if time_prefix_match:
            # Compound mood — only fall back to other compounds with same prefix
            prefix = time_prefix_match.group(1)
            matches = [r for r in rows if r.get("mood", "").lower().startswith(prefix)]
        else:
            # Base mood — only fall back to other base moods (no compounds)
            matches = [r for r in rows
                       if r.get("mood", "").lower() != mood_l
                       and not re.match(r"^(morning_|night_|evening_)", r.get("mood", "").lower())]

    if not matches:
        return None

    best = max(matches, key=lambda r: int(r.get("views", 0) or 0))
    return {
        "title":        best["title"],
        "views":        int(best["views"] or 0),
        "channel":      best["channel"],
        "raga":         best["raga"],
        "mood_matched": best["mood"],
    }


# Spelling variants — map canonical (CSV) → alternate spellings to match in title text
_RAGA_SPELLING_VARIANTS = {
    "bilawal":  ["bilawal", "bilaval"],
    "bhairav":  ["bhairav"],
    "bhairavi": ["bhairavi"],
}


def apply_pattern_to_candidate(comp: dict, mood: str) -> Optional[dict]:
    """
    Find the best competitor title for this mood, then substitute the candidate's
    raga / hz / instrument into the same structural template.

    Returns dict {title, source_title, source_views, source_channel, source_raga,
    mood_matched} — or None if no competitor data available.
    """
    pattern = find_competitor_pattern(mood)
    if not pattern:
        return None

    template = pattern["title"]
    new_title = template

    # 1. Swap competitor's raga → ours (try all known spelling variants)
    our_raga = (comp.get("raga", {}).get("name", "") or "").strip()
    comp_raga = pattern["raga"]
    if our_raga and comp_raga and our_raga.lower() != comp_raga.lower():
        spellings = _RAGA_SPELLING_VARIANTS.get(comp_raga.lower(), [comp_raga.lower()])
        for sp in spellings:
            new_title = re.sub(rf"\b{re.escape(sp)}\b", our_raga.title(), new_title, flags=re.IGNORECASE)

    # 2. Swap competitor's Hz → ours (matches "210Hz", "432 Hz", etc.)
    our_hz = (comp.get("hz", {}).get("hz", "") or "").strip()
    if our_hz:
        new_title = re.sub(r"\d+(?:\.\d+)?\s*Hz", our_hz, new_title, count=1, flags=re.IGNORECASE)

    # 3. Swap competitor's instrument → ours (first match only)
    our_instr = (comp.get("instrument", {}).get("name", "") or "").strip()
    if our_instr:
        for ci in KNOWN_INSTRUMENTS:
            if re.search(rf"\b{ci}\b", new_title, re.IGNORECASE) and our_instr.lower() != ci.lower():
                new_title = re.sub(rf"\b{ci}\b", our_instr.title(), new_title, count=1, flags=re.IGNORECASE)
                break

    return {
        "title":          new_title,
        "source_title":   template,
        "source_views":   pattern["views"],
        "source_channel": pattern["channel"],
        "source_raga":    pattern["raga"],
        "mood_matched":   pattern["mood_matched"],
    }

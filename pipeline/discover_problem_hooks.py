"""
Raga Focus — Problem Hook Discovery from Competitor Titles

Extracts candidate problem-hook keywords from competitor RSS that aren't yet
in our bank. These become the "DISCOVERED — validate these" section of the
daily proposal.

Workflow:
  1. Pull competitor titles (last 30 days) from RSS
  2. Strip instrument/Hz/raga/wave words → leaves the problem-hook portion
  3. Drop phrases already in keyword_bank.csv or invalidated_keywords.csv
  4. Sort by competitor view count (high view = more likely to be a real keyword)
  5. Output top N candidates for the user to test in VidIQ
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Set

from signals import fetch_all_competitor_uploads
from keyword_bank import load_bank

from paths import DATA_DIR
INVALIDATED_CSV = DATA_DIR / "invalidated_keywords.csv"


# Patterns that mean "this isn't a problem keyword"
INSTRUMENT_TOKENS  = {"sitar", "bansuri", "sarangi", "dilruba", "veena", "sarod",
                      "santoor", "esraj", "tanpura", "tabla", "shehnai",
                      "bamboo", "flute", "drum", "instrumental"}
WAVE_TOKENS        = {"alpha", "beta", "theta", "delta", "gamma", "binaural",
                      "wave", "waves"}
TIME_TOKENS        = {"hour", "minutes", "min", "session", "1hr", "2hr"}
NOISE_TOKENS       = {"the", "a", "an", "of", "for", "with", "to",
                      "raga", "ragas", "music", "&", "and"}
HZ_RE              = re.compile(r"\d{2,4}\s*hz", re.IGNORECASE)
PIPE_SPLIT_RE      = re.compile(r"\s*[\|·•]\s*")


def _strip_signal_tokens(phrase: str) -> str:
    """Remove instrument/wave/Hz/time tokens from a phrase. Keep the problem-hook core."""
    p = phrase.lower()
    p = HZ_RE.sub(" ", p)
    words = re.findall(r"[a-zA-Z']+", p)
    keep = [w for w in words
            if w not in INSTRUMENT_TOKENS
            and w not in WAVE_TOKENS
            and w not in TIME_TOKENS]
    return " ".join(keep).strip()


def _candidate_phrases_from_title(title: str) -> List[str]:
    """Return possible problem-hook candidate phrases from a single competitor title."""
    candidates = []
    # Split on pipes (Raga Heal & Shanti use | a lot)
    parts = PIPE_SPLIT_RE.split(title)
    for part in parts:
        part = part.strip().rstrip("?:")
        if not part:
            continue
        stripped = _strip_signal_tokens(part)
        # Drop pure-noise residue
        if not stripped or len(stripped.split()) < 1:
            continue
        # Drop if it's just a noise token
        words = stripped.split()
        if all(w in NOISE_TOKENS for w in words):
            continue
        # Append "music" suffix if the core looks like a problem (it's how YouTube users actually search)
        if not stripped.endswith("music") and not stripped.endswith("meditation") and not stripped.endswith("reset"):
            candidates.append(f"{stripped} music")
        candidates.append(stripped)
    return candidates


def _load_invalidated() -> Set[str]:
    """Phrases we've tried and failed — skip surfacing these."""
    if not INVALIDATED_CSV.exists():
        return set()
    out = set()
    with open(INVALIDATED_CSV) as f:
        for row in csv.DictReader(f):
            out.add(row.get("phrase", "").strip().lower())
    return out


def _bank_phrases() -> Set[str]:
    """Phrases already in keyword_bank.csv — already known."""
    bank = load_bank()
    out = set()
    for slot_entries in bank.values():
        for entry in slot_entries:
            out.add(entry.get("phrase", "").strip().lower())
    return out


def discover(top_n: int = 8) -> List[Dict]:
    """Return top N untested problem-hook candidates extracted from competitor titles."""
    known = _bank_phrases() | _load_invalidated()

    competitor_data = fetch_all_competitor_uploads(days=30)

    # Tally each candidate phrase across all competitor uploads
    counts = {}  # phrase -> {n_uses, sources, latest_days_ago}
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            for cand in _candidate_phrases_from_title(u["title"]):
                if cand in known:
                    continue
                if cand not in counts:
                    counts[cand] = {
                        "phrase":        cand,
                        "uses":          0,
                        "sources":       [],
                        "latest_days":   999,
                    }
                counts[cand]["uses"] += 1
                counts[cand]["latest_days"] = min(counts[cand]["latest_days"], u.get("days_ago", 999))
                if comp_name not in counts[cand]["sources"]:
                    counts[cand]["sources"].append(comp_name)

    # Filter: only keep phrases that actually look like problem keywords
    # (≥ 2 words, ≥ 1 competitor use)
    candidates = [
        c for c in counts.values()
        if len(c["phrase"].split()) >= 2
    ]

    # Rank: more uses + more recent = better
    candidates.sort(key=lambda c: (-c["uses"], c["latest_days"]))
    return candidates[:top_n]


# ═══════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("─── Discovered problem-hook candidates from competitor RSS ───")
    print("(Untested phrases — paste these in VidIQ to validate)\n")
    for i, c in enumerate(discover(top_n=12), 1):
        sources = ", ".join(c["sources"])
        print(f"  {i:>2}. {c['phrase']:<45} "
              f"used {c['uses']}x · latest {c['latest_days']}d ago · {sources}")

"""
Raga Focus — Keyword Bank Loader

Single source of truth for all VidIQ-scored phrases:
    raga-focus-dashboard/data/keyword_bank.csv

Schema (7 columns):
    phrase, slot, vidiq_score, vidiq_comp, source, first_added, last_score_check

  slot ∈ {problem, raga, hz, instrument, wave, tag}

Pipeline reads this on every run. Append via persistence.py (auto-banked from
chat-pasted scores) or pipeline/add_keyword.py (manual CLI).

Static musicology (raga time-of-day, Hz meaning, wave outcomes/matches,
tonal-fit matrix) lives in config.py — code, because it's static knowledge
keyed on phrase, not data we collect.
"""

import csv
from pathlib import Path
from typing import Dict, List

from paths import DATA_DIR
BANK_CSV = DATA_DIR / "keyword_bank.csv"


def load_all() -> List[Dict]:
    """Return every row from keyword_bank.csv as a list of dicts."""
    if not BANK_CSV.exists():
        return []
    with open(BANK_CSV) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        score = r.get("vidiq_score", "").strip()
        r["vidiq_score"] = int(score) if score.isdigit() else None
    return rows


def load_by_slot(slot: str) -> List[Dict]:
    """Return all rows where slot matches. Sorted by score DESC then phrase ASC."""
    rows = [r for r in load_all() if r.get("slot", "").strip() == slot]
    rows.sort(key=lambda r: (-(r["vidiq_score"] or -1), r["phrase"]))
    return rows


def load_bank() -> Dict[str, List[Dict]]:
    """Return {slot: [list of rows]}. Backwards-compat shim for older callers."""
    bank = {"problem": [], "raga": [], "hz": [], "instrument": [], "wave": [], "tag": []}
    for r in load_all():
        slot = r.get("slot", "").strip()
        if slot in bank:
            bank[slot].append(r)
    return bank


def get_alternatives(slot: str, **filters) -> List[Dict]:
    """Filtered fetch (e.g. get_alternatives('hz', vidiq_comp='Low'))."""
    rows = load_by_slot(slot)
    for k, v in filters.items():
        rows = [r for r in rows if r.get(k, "") == v]
    return rows


def append_keyword(phrase: str, slot: str, vidiq_score=None,
                   vidiq_comp: str = "", source: str = "manual"):
    """Append a new validated keyword. Caller passes raw values; we normalise."""
    from datetime import date
    BANK_CSV.parent.mkdir(parents=True, exist_ok=True)
    new_file = not BANK_CSV.exists()
    today = date.today().isoformat()
    with open(BANK_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["phrase", "slot", "vidiq_score", "vidiq_comp",
                        "source", "first_added", "last_score_check"])
        w.writerow([
            phrase.strip().lower(), slot.strip(),
            "" if vidiq_score is None else int(vidiq_score),
            vidiq_comp,
            source,
            today,
            today if vidiq_score is not None else "",
        ])

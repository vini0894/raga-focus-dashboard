"""
Backfill shipped_titles.csv from the live RSS catalog.

Run once: python3 pipeline/backfill_shipped_titles.py
Safe to re-run — deduplicates by (shipped_on, title).
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sys as _bsys
_bsys.path.insert(0, str(HERE.parent))
import storage

from signals import load_own_catalog
from config import PROBLEM_HOOKS, INSTRUMENT_META

DATA_DIR = HERE.parent / "data"
SHIPPED_CSV = DATA_DIR / "shipped_titles.csv"

HEADER = ["shipped_on", "brief_id", "title", "title_length",
          "slot_count", "lead_hook", "instrument", "hz", "raga", "wave", "problem_kw"]


def _extract_instrument(title_lower: str) -> str:
    for inst in INSTRUMENT_META.values():
        for alias in inst["aliases"]:
            if alias in title_lower:
                return inst["name"]
    return ""


def _extract_problem_kw(title_lower: str) -> str:
    best = ""
    for p in PROBLEM_HOOKS:
        kw = p["kw"].lower()
        tokens = [t for t in kw.split() if len(t) >= 3]
        if tokens and all(t in title_lower for t in tokens):
            if len(kw) > len(best):
                best = kw
    return best


def backfill():
    catalog = load_own_catalog()

    # Load existing rows to avoid duplicates
    existing = {(r.get("shipped_on", ""), r.get("title", "")) for r in storage.read_shipped_titles()}

    new_rows = []
    for v in catalog:
        title = v["title"]
        shipped_on = str(v["publish_date"])
        if (shipped_on, title) in existing:
            continue

        title_lower = title.lower()
        parts = [p.strip() for p in title.split("|") if p.strip()]
        new_rows.append({
            "shipped_on":   shipped_on,
            "brief_id":     v.get("video_id", ""),
            "title":        title,
            "title_length": len(title),
            "slot_count":   len(parts),
            "lead_hook":    parts[0] if parts else "",
            "instrument":   _extract_instrument(title_lower),
            "hz":           "",
            "raga":         "",
            "wave":         "",
            "problem_kw":   _extract_problem_kw(title_lower),
        })

    if not new_rows:
        print("Nothing new to backfill.")
        return

    for row in new_rows:
        storage.append_shipped_title(row)
    storage.invalidate_cache()

    print(f"Backfilled {len(new_rows)} videos into shipped_titles.csv")
    for r in new_rows:
        print(f"  {r['shipped_on']} | prob={r['problem_kw']:<25} | inst={r['instrument']:<10} | {r['title'][:55]}")


if __name__ == "__main__":
    backfill()

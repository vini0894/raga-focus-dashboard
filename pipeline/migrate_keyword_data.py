#!/usr/bin/env python3
"""
One-time migration: KEYWORD_DATA.md → data/keyword_bank.csv + invalidated_keywords.csv

Parses every keyword/tag table in KEYWORD_DATA.md, classifies each row by slot
(problem/instrument/hz/wave/raga/tag), and seeds the canonical keyword bank.

After migration, the pipeline reads from the CSV — no more hardcoded
PROBLEM_HOOKS in config.py needed.

Usage:
    python3 pipeline/migrate_keyword_data.py
    python3 pipeline/migrate_keyword_data.py --dry-run   # show what'd be migrated
"""

import argparse
import csv
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYWORD_MD = ROOT / "KEYWORD_DATA.md"
DATA_DIR = ROOT / "raga-focus-dashboard/data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BANK_CSV = DATA_DIR / "keyword_bank.csv"
INVALIDATED_CSV = DATA_DIR / "invalidated_keywords.csv"

MIN_SCORE = 60

# Heuristics for slot classification
HZ_PATTERN = re.compile(r"\b(\d{2,4})\s*hz\b", re.IGNORECASE)
WAVE_NAMES = {"alpha", "beta", "theta", "delta", "gamma", "binaural"}
INSTRUMENT_NAMES = {"bansuri", "sarangi", "dilruba", "sitar", "veena", "sarod",
                    "santoor", "esraj", "tanpura", "tabla", "shehnai",
                    "bamboo flute", "swaramandal"}
RAGA_PREFIX = re.compile(r"^raga\s+", re.IGNORECASE)


def classify_slot(keyword: str, table_type: str) -> str:
    """Return one of: problem, wave, raga, hz, instrument, tag."""
    k = keyword.lower().strip()

    if RAGA_PREFIX.match(k):
        return "raga"
    if HZ_PATTERN.search(k):
        return "hz"
    if any(w in k for w in WAVE_NAMES):
        return "wave"
    if any(i in k.split() or k.startswith(i + " ") or k == i + " music" for i in INSTRUMENT_NAMES):
        return "instrument"
    if table_type == "tag":
        return "tag"
    return "problem"


def parse_score(score_str: str):
    """Extract numeric score from formats like '70 HIGH', '**83 HIGH** ⭐⭐⭐', '59 MEDIUM'."""
    if not score_str:
        return None, ""
    cleaned = re.sub(r"\*+", "", score_str)
    m = re.search(r"(\d+)\s*(HIGH|MEDIUM|MED|LOW)?", cleaned, re.IGNORECASE)
    if not m:
        return None, ""
    score = int(m.group(1))
    level = (m.group(2) or "").upper().replace("MED", "MEDIUM")
    return score, level


def parse_comp(comp_str: str):
    """Normalize competition strings."""
    if not comp_str:
        return ""
    cleaned = re.sub(r"\*+", "", comp_str).strip()
    return cleaned


def parse_keyword_table_row(cells, table_type):
    """
    Keyword table: | Keyword | Volume | Competition | Score | Avg Views | Top Creator | Notes |
    Tag table:     | Tag | Score | Use? |   OR   | Tag | Score | Best use |
    """
    if table_type == "keyword" and len(cells) >= 7:
        return {
            "phrase":   cells[0],
            "volume":   cells[1],
            "comp":     parse_comp(cells[2]),
            "score":    cells[3],
            "avg_views":cells[4],
            "top_creator": cells[5],
            "notes":    cells[6],
        }
    elif table_type == "tag" and len(cells) >= 2:
        return {
            "phrase":  cells[0],
            "score":   cells[1],
            "comp":    "",
            "notes":   cells[2] if len(cells) >= 3 else "",
            "volume":  "",
            "avg_views":"",
            "top_creator":"",
        }
    return None


def detect_table_type(header_cells):
    """Look at the first column header — Keyword vs Tag."""
    if not header_cells:
        return None
    h = header_cells[0].lower().strip()
    if "keyword" in h:
        return "keyword"
    if "tag" in h:
        return "tag"
    return None


def parse_tables(md_text: str):
    """Walk the markdown and yield (row_dict, table_type) for every data row."""
    lines = md_text.splitlines()
    in_table = False
    current_type = None
    rows = []

    for line in lines:
        stripped = line.strip()

        if not stripped.startswith("|"):
            in_table = False
            current_type = None
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]

        # Skip table-divider rows like |---|---|
        if all(set(c) <= set("-: ") for c in cells):
            continue

        if not in_table:
            # First "|"-row of a new table = the header
            current_type = detect_table_type(cells)
            in_table = True
            continue

        # Data row
        if current_type:
            row = parse_keyword_table_row(cells, current_type)
            if row:
                rows.append((row, current_type))

    return rows


def migrate(dry_run=False):
    if not KEYWORD_MD.exists():
        print(f"❌ {KEYWORD_MD} not found")
        return

    md_text = KEYWORD_MD.read_text()
    rows = parse_tables(md_text)
    print(f"  Found {len(rows)} rows across all tables")

    promoted = []
    invalidated = []
    skipped = []

    for row, table_type in rows:
        phrase = row["phrase"].strip()
        # Skip header-like artifacts or empty
        if not phrase or phrase.lower() in {"keyword", "tag", "category"}:
            continue
        # Strip markdown emphasis from phrase too
        phrase = re.sub(r"\*+", "", phrase).strip()

        score, level = parse_score(row["score"])
        if score is None:
            skipped.append((phrase, "no score"))
            continue

        slot = classify_slot(phrase, table_type)

        record = {
            "phrase":          phrase,
            "slot":            slot,
            "vidiq_score":     score,
            "vidiq_comp":      row["comp"],
            "mood_bucket":     "",
            "hz_intent":       "",
            "discovered_from": f"KEYWORD_DATA.md migration ({row.get('top_creator', '')})".strip(" ()"),
            "added_date":      date.today().isoformat(),
        }

        if score >= MIN_SCORE:
            promoted.append(record)
        else:
            invalidated.append({
                "phrase":      phrase,
                "slot":        slot,
                "vidiq_score": score,
                "tested_on":   date.today().isoformat(),
                "notes":       (row.get("notes") or "")[:200],
            })

    if dry_run:
        print(f"\n  [DRY RUN] Would promote {len(promoted)} keywords:")
        for r in promoted[:15]:
            print(f"    [{r['slot']:10s}] {r['vidiq_score']:>3}  {r['phrase']}")
        if len(promoted) > 15:
            print(f"    ... and {len(promoted) - 15} more")
        print(f"\n  [DRY RUN] Would invalidate {len(invalidated)} keywords:")
        for r in invalidated[:5]:
            print(f"    [{r['slot']:10s}] {r['vidiq_score']:>3}  {r['phrase']}")
        return

    # Write keyword_bank.csv (overwrite — fresh seed)
    bank_header = ["phrase", "slot", "vidiq_score", "vidiq_comp",
                   "mood_bucket", "hz_intent", "discovered_from", "added_date"]
    with open(BANK_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=bank_header)
        w.writeheader()
        # Dedupe by (phrase, slot)
        seen = set()
        for r in promoted:
            key = (r["phrase"].lower(), r["slot"])
            if key in seen:
                continue
            seen.add(key)
            w.writerow(r)
    print(f"  ✓ keyword_bank.csv  → {BANK_CSV} ({len(promoted)} entries)")

    # Write invalidated_keywords.csv (overwrite — fresh seed)
    inv_header = ["phrase", "slot", "vidiq_score", "tested_on", "notes"]
    with open(INVALIDATED_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=inv_header)
        w.writeheader()
        seen = set()
        for r in invalidated:
            key = (r["phrase"].lower(), r["slot"])
            if key in seen:
                continue
            seen.add(key)
            w.writerow(r)
    print(f"  ✓ invalidated_keywords.csv  → {INVALIDATED_CSV} ({len(invalidated)} entries)")

    # Quick summary by slot
    print(f"\n  Summary (validated bank):")
    by_slot = {}
    for r in promoted:
        by_slot[r["slot"]] = by_slot.get(r["slot"], 0) + 1
    for slot, n in sorted(by_slot.items(), key=lambda x: -x[1]):
        print(f"    {slot:10s}  {n}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Show what'd be migrated without writing")
    args = ap.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

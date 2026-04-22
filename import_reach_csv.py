"""Import YouTube Studio Reach CSV exports into REACH_HISTORY.csv.

Usage:
    python import_reach_csv.py

Behavior:
- Scans data/reach_exports/*.csv
- For each file, parses the capture date from filename (reach_YYYY-MM-DD.csv)
  falling back to the file's mtime if the filename isn't dated.
- Appends one row per video per capture to data/REACH_HISTORY.csv
- Skips rows that already exist (keyed on video_id + capture_date)
- Non-destructive: never overwrites historical data.
"""
from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
EXPORTS_DIR = DASHBOARD_DIR / "data" / "reach_exports"
HISTORY_FILE = DASHBOARD_DIR / "data" / "REACH_HISTORY.csv"

HISTORY_COLS = [
    "capture_date",
    "video_id",
    "title",
    "publish_date",
    "views",
    "watch_hours",
    "subscribers_gained",
    "impressions",
    "ctr_pct",
    "avg_view_duration_sec",
    "avg_view_pct",
]


def parse_capture_date(path: Path) -> str:
    """Extract YYYY-MM-DD from filename (reach_YYYY-MM-DD.csv), else use mtime."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if m:
        return m.group(1)
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def parse_duration_to_seconds(s: str) -> int:
    """Convert H:MM:SS or MM:SS to seconds."""
    if not s:
        return 0
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = parts
            return int(h) * 3600 + int(m) * 60 + int(sec)
        if len(parts) == 2:
            m, sec = parts
            return int(m) * 60 + int(sec)
    except ValueError:
        return 0
    return 0


def parse_float(s: str) -> float:
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def parse_int(s: str) -> int:
    try:
        return int(float(str(s).replace(",", "").strip()))
    except (ValueError, AttributeError):
        return 0


def parse_publish_date(s: str) -> str:
    """Studio emits 'Apr 5, 2026' → convert to 2026-04-05."""
    if not s:
        return ""
    try:
        return datetime.strptime(s.strip(), "%b %d, %Y").date().isoformat()
    except ValueError:
        return s.strip()


def load_existing_history() -> set[tuple[str, str]]:
    """Return set of (capture_date, video_id) already in history."""
    if not HISTORY_FILE.exists():
        return set()
    seen = set()
    with HISTORY_FILE.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            seen.add((row["capture_date"], row["video_id"]))
    return seen


def append_history(new_rows: list[dict]) -> None:
    """Append rows, creating the file with header if needed."""
    exists = HISTORY_FILE.exists()
    with HISTORY_FILE.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_COLS)
        if not exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)


def import_csv(path: Path, seen: set[tuple[str, str]]) -> list[dict]:
    capture_date = parse_capture_date(path)
    new_rows = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_id = row.get("Content", "").strip()
            # Skip the "Total" summary row and any empty rows
            if not video_id or video_id.lower() == "total":
                continue
            # Skip if already imported this exact (date, video_id)
            if (capture_date, video_id) in seen:
                continue
            new_rows.append({
                "capture_date": capture_date,
                "video_id": video_id,
                "title": row.get("Video title", "").strip(),
                "publish_date": parse_publish_date(row.get("Video publish time", "")),
                "views": parse_int(row.get("Views", "0")),
                "watch_hours": parse_float(row.get("Watch time (hours)", "0")),
                "subscribers_gained": parse_int(row.get("Subscribers", "0")),
                "impressions": parse_int(row.get("Impressions", "0")),
                "ctr_pct": parse_float(row.get("Impressions click-through rate (%)", "0")),
                "avg_view_duration_sec": parse_duration_to_seconds(row.get("Average view duration", "0:00")),
                "avg_view_pct": parse_float(row.get("Average percentage viewed (%)", "0")),
            })
    return new_rows


def main() -> int:
    if not EXPORTS_DIR.exists():
        print(f"❌ Exports folder missing: {EXPORTS_DIR}")
        print(f"   Create it and drop Studio CSV exports there (name: reach_YYYY-MM-DD.csv).")
        return 1

    csv_files = sorted(EXPORTS_DIR.glob("*.csv"))
    if not csv_files:
        print(f"⚠️  No CSV files found in {EXPORTS_DIR}")
        return 0

    seen = load_existing_history()
    print(f"📂 Found {len(csv_files)} CSV file(s) · history has {len(seen)} existing row(s)")

    total_new = 0
    for path in csv_files:
        new_rows = import_csv(path, seen)
        if new_rows:
            append_history(new_rows)
            # Update seen set so subsequent files in this run don't re-add
            for r in new_rows:
                seen.add((r["capture_date"], r["video_id"]))
            print(f"  ✅ {path.name}: +{len(new_rows)} rows (capture {new_rows[0]['capture_date']})")
            total_new += len(new_rows)
        else:
            print(f"  ⏭  {path.name}: no new rows (already imported)")

    print(f"\n✨ Done. {total_new} new row(s) appended to {HISTORY_FILE.relative_to(DASHBOARD_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

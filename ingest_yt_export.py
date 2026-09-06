"""Single entry point to ingest a YouTube Studio per-video CSV export into all stores.

Supersedes import_reach_csv.py by handling the full fan-out:
  1. Archives raw  -> data/reach_exports/reach_YYYY-MM-DD.csv
  2. Public store  -> data/REACH_HISTORY.csv            (NO revenue, git-tracked)
  3. Revenue store -> data/private/revenue_history.csv   (revenue, gitignored)
  4. Totals store  -> data/private/channel_totals_history.csv  (Total row, gitignored)
  5. Index         -> data/private/SNAPSHOTS_INDEX.md    (human-readable manifest)

All appends are idempotent (keyed on capture_date [+ video_id]); re-running is safe.

Usage:
    python ingest_yt_export.py path/to/export.csv [more.csv ...]   # explicit files
    python ingest_yt_export.py path/to/export.csv --date 2026-06-25  # force date
    python ingest_yt_export.py --scan-downloads                     # auto-find in ~/Downloads
    python ingest_yt_export.py --scan-archive                       # re-ingest data/reach_exports/

Capture date resolution: --date arg > filename date (many formats) > file mtime.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
DATA = DASHBOARD_DIR / "data"
EXPORTS_DIR = DATA / "reach_exports"
PRIVATE = DATA / "private"
HISTORY_FILE = DATA / "REACH_HISTORY.csv"
REVENUE_FILE = PRIVATE / "revenue_history.csv"
TOTALS_FILE = PRIVATE / "channel_totals_history.csv"
INDEX_FILE = PRIVATE / "SNAPSHOTS_INDEX.md"
DOWNLOADS = Path.home() / "Downloads"
DEFAULT_WINDOW_DAYS = 28  # Studio exports are a trailing 28-day rolling window

HISTORY_COLS = ["capture_date", "video_id", "title", "publish_date", "views",
                "engaged_views", "watch_hours", "subscribers_gained", "impressions",
                "ctr_pct", "avg_view_duration_sec", "avg_view_pct"]
REVENUE_COLS = ["capture_date", "video_id", "title", "publish_date", "views",
                "estimated_revenue_usd"]
TOTALS_COLS = ["capture_date", "window_days", "n_videos", "views", "engaged_views", "watch_hours",
               "subscribers_gained", "revenue_usd", "impressions", "ctr_pct",
               "avd_sec", "avd_pct", "rev_per_day"]

MONTHS = {m.lower(): i for i, m in enumerate(
    ["", "January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items()) if m})


# ---------- parsing helpers ----------
def _f(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _i(s):
    try:
        return int(float(str(s).replace(",", "").strip()))
    except (ValueError, AttributeError):
        return 0


def dur_to_sec(s):
    if not s:
        return 0
    p = str(s).split(":")
    try:
        p = [int(x) for x in p]
    except ValueError:
        return 0
    while len(p) < 3:
        p = [0] + p
    return p[0] * 3600 + p[1] * 60 + p[2]


def pub_date(s):
    s = (s or "").strip().strip('"')
    if not s:
        return ""
    try:
        return datetime.strptime(s, "%b %d, %Y").date().isoformat()
    except ValueError:
        return s


def parse_capture_date(path: Path, default_year=2026) -> str | None:
    """Resolve YYYY-MM-DD from many messy filename styles, else mtime."""
    stem = path.stem.lower()
    # ISO date already present
    m = re.search(r"(\d{4}-\d{2}-\d{2})", stem)
    if m:
        return m.group(1)
    # "25th june" / "22 june" / "june 22" / "21june" / "3 june"
    mname = "|".join([k for k in MONTHS if k])
    m = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s*[- ]?\s*({mname})", stem)
    if not m:
        m2 = re.search(rf"({mname})\s*[- ]?\s*(\d{{1,2}})(?:st|nd|rd|th)?", stem)
        if m2:
            mon, day = MONTHS[m2.group(1)], int(m2.group(2))
            return f"{default_year}-{mon:02d}-{day:02d}"
    if m:
        day, mon = int(m.group(1)), MONTHS[m.group(2)]
        return f"{default_year}-{mon:02d}-{day:02d}"
    return None  # caller decides whether to fall back to mtime



# ---------- column aliases ----------
# YouTube renamed Studio export columns around 2026-08-31:
#   "Impressions"                        -> "Thumbnail impressions"
#   "Impressions click-through rate (%)" -> "Thumbnail click-through rate (%)"
IMPR_COLS = ("Impressions", "Thumbnail impressions")
# "Engaged views" arrived 2026-08-31, when public Views switched to counting at PLAY
# START. Older exports counted Views at the engaged threshold, so views IS the
# engaged figure there — that fallback keeps the series comparable across the change.
ENGAGED_COLS = ("Engaged views",)
CTR_COLS = ("Impressions click-through rate (%)", "Thumbnail click-through rate (%)")


def _col(row, names, default=""):
    for n in names:
        if row.get(n) not in (None, ""):
            return row[n]
    return default


def is_studio_export(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8-sig") as f:
            header = f.readline()
        return ("Video title" in header and "Estimated revenue" in header
                and any(c in header for c in IMPR_COLS))
    except Exception:
        return False


# ---------- store I/O ----------
def _seen_keyed(file: Path, *cols) -> set:
    if not file.exists():
        return set()
    seen = set()
    with file.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            seen.add(tuple(row[c] for c in cols))
    return seen


def _append(file: Path, cols, rows):
    file.parent.mkdir(parents=True, exist_ok=True)
    new = not file.exists()
    with file.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def ingest_one(path: Path, force_date=None, window_days=DEFAULT_WINDOW_DAYS) -> dict:
    cap = force_date or parse_capture_date(path)
    if cap is None:
        cap = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
        dated = "mtime"
    else:
        dated = "filename" if not force_date else "arg"

    # 1. archive raw (canonical name) if not already there
    archived = EXPORTS_DIR / f"reach_{cap}.csv"
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if path.resolve() != archived.resolve() and not archived.exists():
        shutil.copy2(path, archived)

    hist_seen = _seen_keyed(HISTORY_FILE, "capture_date", "video_id")
    rev_seen = _seen_keyed(REVENUE_FILE, "capture_date", "video_id")
    tot_seen = _seen_keyed(TOTALS_FILE, "capture_date")

    hist_rows, rev_rows, total_row, n_videos = [], [], None, 0
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            vid = (row.get("Content") or "").strip()
            if not vid:
                continue
            if vid.lower() == "total":
                total_row = row
                continue
            n_videos += 1
            title = (row.get("Video title") or "").strip()
            pub = pub_date(row.get("Video publish time", ""))
            views = _i(row.get("Views", "0"))
            if (cap, vid) not in hist_seen:
                hist_rows.append({
                    "capture_date": cap, "video_id": vid, "title": title,
                    "publish_date": pub, "views": views,
                    "engaged_views": _i(_col(row, ENGAGED_COLS, views)),
                    "watch_hours": _f(row.get("Watch time (hours)", "0")),
                    "subscribers_gained": _i(row.get("Subscribers", "0")),
                    "impressions": _i(_col(row, IMPR_COLS, "0")),
                    "ctr_pct": _f(_col(row, CTR_COLS, "0")),
                    "avg_view_duration_sec": dur_to_sec(row.get("Average view duration", "0:00")),
                    "avg_view_pct": _f(row.get("Average percentage viewed (%)", "0")),
                })
            if (cap, vid) not in rev_seen:
                rev_rows.append({
                    "capture_date": cap, "video_id": vid, "title": title,
                    "publish_date": pub, "views": views,
                    "estimated_revenue_usd": _f(row.get("Estimated revenue (USD)", "0")),
                })

    tot_rows = []
    if total_row is not None and (cap,) not in tot_seen:
        rev = _f(total_row.get("Estimated revenue (USD)", "0"))
        tot_rows.append({
            "capture_date": cap, "window_days": window_days, "n_videos": n_videos,
            "views": _i(total_row.get("Views", "0")),
            # Engaged views is the ONLY denominator comparable across 2026-08-24, when
            # YouTube moved public view counting to play-start. Storing `views` alone
            # understated channel RPM by 17% at the 2026-09-06 capture (1.17x gap) and
            # the gap widens as the two counts diverge. Falls back to views for
            # pre-change exports, where the two are genuinely equal.
            "engaged_views": _i(total_row.get("Engaged views") or total_row.get("Views", "0")),
            "watch_hours": _f(total_row.get("Watch time (hours)", "0")),
            "subscribers_gained": _i(total_row.get("Subscribers", "0")),
            "revenue_usd": round(rev, 3),
            "impressions": _i(_col(total_row, IMPR_COLS, "0")),
            "ctr_pct": _f(_col(total_row, CTR_COLS, "0")),
            "avd_sec": dur_to_sec(total_row.get("Average view duration", "0:00")),
            "avd_pct": _f(total_row.get("Average percentage viewed (%)", "0")),
            "rev_per_day": round(rev / window_days, 2),
        })

    _append(HISTORY_FILE, HISTORY_COLS, hist_rows)
    _append(REVENUE_FILE, REVENUE_COLS, rev_rows)
    _append(TOTALS_FILE, TOTALS_COLS, tot_rows)
    return {"capture": cap, "dated_by": dated, "hist": len(hist_rows),
            "rev": len(rev_rows), "tot": len(tot_rows), "file": path.name}


def rebuild_index():
    if not TOTALS_FILE.exists():
        return
    with TOTALS_FILE.open(encoding="utf-8-sig") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: r["capture_date"])
    lines = ["# Snapshot Index (private — contains revenue)\n",
             f"_Auto-generated by ingest_yt_export.py · {len(rows)} snapshots · "
             "trailing 28-day rolling windows unless flagged ⚠_\n",
             "| Date | Window | Videos | Views | Watch hrs | Rev $ | Rev/day | Impr (M) | CTR% | AVD% | Subs |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        wd = int(float(r.get("window_days", 28)))
        win = f"{wd}d" if wd == 28 else f"⚠{wd}d"
        lines.append(
            f"| {r['capture_date']} | {win} | {r['n_videos']} | {int(float(r['views'])):,} | "
            f"{float(r['watch_hours']):,.0f} | {float(r['revenue_usd']):,.0f} | "
            f"{float(r['rev_per_day']):,.1f} | {float(r['impressions'])/1e6:.1f} | "
            f"{float(r['ctr_pct']):.2f} | {float(r['avd_pct']):.1f} | {int(float(r['subscribers_gained'])):,} |")
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def discover_downloads() -> list[Path]:
    pats = ["*yt*.csv", "*YT*.csv", "*[Yy][Tt] data*.csv"]
    found = {}
    for p in pats:
        for f in DOWNLOADS.glob(p):
            if is_studio_export(f):
                found[f.resolve()] = f
    return sorted(found.values())


def main():
    ap = argparse.ArgumentParser(description="Ingest YouTube Studio per-video CSV exports.")
    ap.add_argument("files", nargs="*", help="Paths to raw Studio CSV export(s).")
    ap.add_argument("--date", help="Force capture date YYYY-MM-DD (single file only).")
    ap.add_argument("--scan-downloads", action="store_true", help="Auto-find YT exports in ~/Downloads.")
    ap.add_argument("--scan-archive", action="store_true", help="Re-ingest data/reach_exports/*.csv.")
    ap.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    ap.add_argument("--no-warehouse", action="store_true", help="Skip the DuckDB warehouse rebuild at the end.")
    args = ap.parse_args()

    targets: list[Path] = [Path(f) for f in args.files]
    if args.scan_downloads:
        targets += discover_downloads()
    if args.scan_archive:
        targets += sorted(EXPORTS_DIR.glob("reach_*.csv"))
    # de-dup, keep only existing Studio exports
    seen, clean = set(), []
    for t in targets:
        rp = t.resolve()
        if rp in seen or not t.exists():
            continue
        seen.add(rp)
        if not is_studio_export(t):
            print(f"  ⏭  skip (not a Studio per-video export): {t.name}")
            continue
        clean.append(t)

    if not clean:
        print("⚠️  No valid Studio exports to ingest. Use --scan-downloads or pass file paths.")
        return 0
    if args.date and len(clean) != 1:
        print("❌ --date can only be used with exactly one file.")
        return 1

    print(f"📥 Ingesting {len(clean)} export(s)…")
    th = tr = tt = 0
    for path in clean:
        r = ingest_one(path, force_date=args.date, window_days=args.window_days)
        flag = "" if r["dated_by"] != "mtime" else " ⚠️(dated by mtime — pass --date if wrong)"
        print(f"  ✅ {r['file']:<32} → {r['capture']}  +{r['hist']} hist / +{r['rev']} rev / +{r['tot']} tot{flag}")
        th += r["hist"]; tr += r["rev"]; tt += r["tot"]

    rebuild_index()
    print(f"\n✨ Done. +{th} public rows · +{tr} revenue rows · +{tt} totals rows")
    print(f"   Public : {HISTORY_FILE.relative_to(DASHBOARD_DIR)}")
    print(f"   Private: {REVENUE_FILE.relative_to(DASHBOARD_DIR)} · {TOTALS_FILE.name}")
    print(f"   Index  : {INDEX_FILE.relative_to(DASHBOARD_DIR)}")

    # ---- rebuild the query layer so CSVs and the warehouse never drift ----
    wh = Path(__file__).resolve().parent.parent / "tools" / "build_warehouse.py"
    if wh.exists() and not args.no_warehouse:
        print("\n🏗  Rebuilding warehouse (CSVs → DuckDB)…")
        subprocess.run([sys.executable, str(wh)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

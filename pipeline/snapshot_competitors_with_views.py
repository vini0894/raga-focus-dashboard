#!/usr/bin/env python3
"""
Enhanced competitor snapshot — captures titles + VIEWS + likes + duration via YT Data API.

Writes to:
    raga-focus-dashboard/data/competitor_snapshots_v2.csv

Use this for weekly planning competitor analysis. Old RSS-based
snapshot_competitors.py captures titles only (for A/B-change detection);
this version captures the full metric set for inspiration mining.

Usage:
    python3 pipeline/snapshot_competitors_with_views.py
    python3 pipeline/snapshot_competitors_with_views.py --top-only  # only show ranked top 20

Outputs CSV columns:
    snapshot_date, competitor, competitor_subs, video_id, title, published, days_ago,
    views, likes, duration_iso, duration_min, views_per_sub, is_longform
"""
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Repo paths
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from auth import yt_data as _yt_data
from pipeline.config import COMPETITORS

DATA_DIR = ROOT / "data"
OUT_CSV = DATA_DIR / "competitor_snapshots_v2.csv"

HEADERS = [
    "snapshot_date", "competitor", "competitor_subs",
    "video_id", "title", "published", "days_ago",
    "views", "likes", "duration_iso", "duration_min",
    "views_per_sub", "is_longform",
]


def parse_duration_min(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    return h * 60 + mins


def days_since(pub_iso: str, today: date) -> int:
    try:
        d = datetime.strptime(pub_iso[:10], "%Y-%m-%d").date()
        return (today - d).days
    except Exception:
        return -1


def fetch_competitor_videos(yd, channel_id: str, limit: int = 50):
    """Pull last N uploads with full stats for a channel."""
    # 1. channel info
    ch = yd.channels().list(part="contentDetails,statistics", id=channel_id).execute()
    if not ch.get("items"):
        return None, []
    item = ch["items"][0]
    subs = int(item["statistics"].get("subscriberCount", 0))
    uploads_id = item["contentDetails"]["relatedPlaylists"]["uploads"]

    # 2. playlistItems (chronological)
    vids = []
    next_token = None
    while len(vids) < limit:
        kwargs = dict(part="contentDetails,snippet", playlistId=uploads_id, maxResults=min(50, limit - len(vids)))
        if next_token:
            kwargs["pageToken"] = next_token
        pl = yd.playlistItems().list(**kwargs).execute()
        for it in pl.get("items", []):
            vids.append({
                "video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "published": it["snippet"]["publishedAt"][:10],
            })
        next_token = pl.get("nextPageToken")
        if not next_token:
            break

    # 3. batch fetch stats (max 50 IDs per call)
    for i in range(0, len(vids), 50):
        batch_ids = [v["video_id"] for v in vids[i:i + 50]]
        v = yd.videos().list(part="statistics,contentDetails", id=",".join(batch_ids)).execute()
        stats_map = {}
        for s in v.get("items", []):
            stats_map[s["id"]] = {
                "views": int(s["statistics"].get("viewCount", 0)),
                "likes": int(s["statistics"].get("likeCount", 0)),
                "duration": s["contentDetails"]["duration"],
            }
        for vid in vids[i:i + 50]:
            sm = stats_map.get(vid["video_id"], {})
            vid["views"] = sm.get("views", 0)
            vid["likes"] = sm.get("likes", 0)
            vid["duration"] = sm.get("duration", "")

    return subs, vids


def main():
    show_top_only = "--top-only" in sys.argv
    yd = _yt_data()
    today = date.today()

    all_rows = []
    for name, cid in COMPETITORS.items():
        print(f"📡 Fetching {name} ({cid})...")
        subs, vids = fetch_competitor_videos(yd, cid, limit=50)
        if subs is None:
            print(f"  ⚠️ Failed to fetch")
            continue
        print(f"  ✓ Subs={subs:,}, pulled {len(vids)} videos")
        for v in vids:
            dur_min = parse_duration_min(v.get("duration", ""))
            d_ago = days_since(v["published"], today)
            views = v.get("views", 0)
            row = {
                "snapshot_date": today.isoformat(),
                "competitor": name,
                "competitor_subs": subs,
                "video_id": v["video_id"],
                "title": v["title"],
                "published": v["published"],
                "days_ago": d_ago,
                "views": views,
                "likes": v.get("likes", 0),
                "duration_iso": v.get("duration", ""),
                "duration_min": dur_min,
                "views_per_sub": round(views / max(subs, 1), 4),
                "is_longform": dur_min >= 30,
            }
            all_rows.append(row)

    # Write CSV (append-friendly: include capture date)
    write_header = not OUT_CSV.exists()
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        if write_header:
            w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"\n✅ Wrote {len(all_rows)} rows to {OUT_CSV}")

    # Print top performers for quick inspection
    print(f"\n{'='*100}")
    print(f"TOP COMPETITOR LONG-FORM VIDEOS (≥30 min, last 60 days, by views)")
    print(f"{'='*100}\n")
    longform_recent = [r for r in all_rows if r["is_longform"] and 0 <= r["days_ago"] <= 60]
    longform_recent.sort(key=lambda r: -r["views"])

    print(f'{"Date":12}{"Days":>5}{"Views":>10}{"V/Sub":>8}  Competitor                      Title')
    print('-' * 130)
    for r in longform_recent[:25]:
        comp_label = f'{r["competitor"]} ({r["competitor_subs"]:,})'
        print(f'{r["published"]:12}{r["days_ago"]:>5}{r["views"]:>10,}{r["views_per_sub"]:>8.2f}  {comp_label:32}  {r["title"][:75]}')

    # Highlight "outlier" candidates — views/sub > 0.30 in last 30 days (replica-worthy)
    print(f"\n{'='*100}")
    print(f"⭐ REPLICA-WORTHY OUTLIERS (V/Sub ≥ 0.30 in last 30 days)")
    print(f"{'='*100}\n")
    outliers = [r for r in all_rows if r["is_longform"] and 0 <= r["days_ago"] <= 30 and r["views_per_sub"] >= 0.30]
    outliers.sort(key=lambda r: -r["views_per_sub"])
    if not outliers:
        print("  (none — no fresh outliers in last 30 days)")
    else:
        for r in outliers[:10]:
            comp_label = f'{r["competitor"]} ({r["competitor_subs"]:,})'
            print(f'  V/Sub={r["views_per_sub"]:.2f} · {r["views"]:,} views in {r["days_ago"]}d · {comp_label}\n     → "{r["title"]}"')

    return all_rows


if __name__ == "__main__":
    main()

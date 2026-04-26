#!/usr/bin/env python3
"""
Daily snapshot of competitor titles → detect title changes (= inferred A/B tests).

Run daily (manual or cron). Writes to:
    raga-focus-dashboard/data/competitor_snapshots.csv

When a video's title changes vs the prior snapshot, that means the competitor
either ran an A/B test (and the new title is the winner) or rebranded.
Either way, it's strong signal about what's working.

Usage:
    python3 snapshot_competitors.py
"""

import csv
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import COMPETITORS

from paths import DATA_DIR
SNAPSHOT_CSV = DATA_DIR / "competitor_snapshots.csv"
CHANGES_LOG = DATA_DIR / "competitor_title_changes.csv"


def fetch_titles(channel_id):
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"  ⚠️ {channel_id}: {e}")
        return []
    root = ET.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    out = []
    for entry in root.findall("atom:entry", ns):
        vid = entry.find("yt:videoId", ns).text
        title = (entry.find("atom:title", ns).text or "").strip()
        out.append({"video_id": vid, "title": title})
    return out


def load_prior_snapshot():
    """Return dict: video_id -> latest known title."""
    if not SNAPSHOT_CSV.exists():
        return {}
    latest_by_id = {}
    with open(SNAPSHOT_CSV) as f:
        for row in csv.DictReader(f):
            # We want the most recent snapshot per video_id
            latest_by_id[row["video_id"]] = row
    return {vid: r["title"] for vid, r in latest_by_id.items()}


def main():
    today = date.today().isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prior = load_prior_snapshot()
    changes = []

    new_rows = []
    for comp_name, channel_id in COMPETITORS.items():
        print(f"[{today}] Snapshotting {comp_name} …")
        videos = fetch_titles(channel_id)
        for v in videos:
            new_rows.append({
                "snapshot_date": today,
                "competitor":    comp_name,
                "video_id":      v["video_id"],
                "title":         v["title"],
            })
            old = prior.get(v["video_id"])
            if old and old != v["title"]:
                changes.append({
                    "detected_on": today,
                    "competitor":  comp_name,
                    "video_id":    v["video_id"],
                    "old_title":   old,
                    "new_title":   v["title"],
                })

    # Append snapshot
    new_file = not SNAPSHOT_CSV.exists()
    with open(SNAPSHOT_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["snapshot_date", "competitor", "video_id", "title"])
        for r in new_rows:
            w.writerow([r["snapshot_date"], r["competitor"], r["video_id"], r["title"]])
    print(f"  ✓ {len(new_rows)} titles snapshotted to {SNAPSHOT_CSV.name}")

    # Append detected changes (these = inferred A/B test winners)
    if changes:
        new_file = not CHANGES_LOG.exists()
        with open(CHANGES_LOG, "a", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["detected_on", "competitor", "video_id", "old_title", "new_title"])
            for c in changes:
                w.writerow([c["detected_on"], c["competitor"], c["video_id"], c["old_title"], c["new_title"]])
        print(f"\n  ⭐ {len(changes)} TITLE CHANGES DETECTED (inferred A/B winners):")
        for c in changes:
            print(f"     [{c['competitor']}] {c['video_id']}")
            print(f"       OLD: {c['old_title']}")
            print(f"       NEW: {c['new_title']}")
    else:
        print(f"  No title changes detected vs prior snapshot.")


if __name__ == "__main__":
    main()

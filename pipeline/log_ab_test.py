#!/usr/bin/env python3
"""
Quick CLI to log a concluded YouTube A/B title test result.

Appends to data/ab_results.csv (always-fresh source). The pipeline reads
this file via historical.py to drive hook-template recommendations.

Usage:
    python3 log_ab_test.py --video_id 5UGTuyNHHHE --winner A_seo --margin 0.75
    python3 log_ab_test.py --video_id ABC --winner B_question --margin 0.30 --notes "Question hook beat SEO on grief topic"

Or interactively:
    python3 log_ab_test.py
"""

import argparse
import csv
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from paths import DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
AB_CSV = DATA_DIR / "ab_results.csv"

CHANNEL_ID = "UCtNMs5bRntzvvzjSrTJIo_Q"
VALID_WINNERS = {"A_seo", "B_question", "C_outcome"}


def fetch_title_from_rss(video_id):
    """Best-effort: pull current title from channel RSS."""
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        for entry in root.findall("atom:entry", ns):
            vid_elem = entry.find("yt:videoId", ns)
            if vid_elem is not None and vid_elem.text == video_id:
                return entry.find("atom:title", ns).text
    except Exception:
        pass
    return ""


def append_result(row):
    new_file = not AB_CSV.exists()
    with open(AB_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["concluded_on", "video_id", "winner", "win_margin", "winner_title", "loser_title", "notes"])
        w.writerow([
            row["concluded_on"], row["video_id"], row["winner"], row["win_margin"],
            row["winner_title"], row["loser_title"], row["notes"],
        ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video_id", help="YouTube video ID (the one whose test concluded)")
    ap.add_argument("--winner",   choices=sorted(VALID_WINNERS), help="Which variant won")
    ap.add_argument("--margin",   type=float, help="Win margin as decimal (e.g. 0.75 = SEO won 3:1)")
    ap.add_argument("--winner_title", default="", help="Optional — the winning title text")
    ap.add_argument("--loser_title",  default="", help="Optional — the losing title text")
    ap.add_argument("--notes", default="", help="Optional notes")
    args = ap.parse_args()

    # Interactive fallback
    video_id = args.video_id or input("video_id: ").strip()
    winner = args.winner or input(f"winner ({'/'.join(sorted(VALID_WINNERS))}): ").strip()
    if winner not in VALID_WINNERS:
        sys.exit(f"❌ winner must be one of {VALID_WINNERS}")
    margin = args.margin if args.margin is not None else float(input("margin (e.g. 0.75): ").strip())

    # Auto-fetch winning title from RSS
    winner_title = args.winner_title or fetch_title_from_rss(video_id)
    if not winner_title:
        winner_title = input("winner_title (couldn't fetch from RSS, paste manually): ").strip()

    loser_title = args.loser_title
    notes = args.notes

    row = {
        "concluded_on":  date.today().isoformat(),
        "video_id":      video_id,
        "winner":        winner,
        "win_margin":    margin,
        "winner_title":  winner_title,
        "loser_title":   loser_title,
        "notes":         notes,
    }
    append_result(row)
    print(f"✓ Logged to {AB_CSV}")
    print(f"  {row}")


if __name__ == "__main__":
    main()

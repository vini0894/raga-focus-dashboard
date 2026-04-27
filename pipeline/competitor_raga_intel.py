"""
Competitor raga intelligence — fetches recent uploads from each channel in
COMPETITORS, extracts (raga, mood) pairs from titles + view counts, and
cross-references against raga_fit_cache.csv.

Outputs:
    data/competitor_raga_usage.csv — raw extracted pairs (raga, mood, views, title, channel, pub_date)
    data/competitor_raga_findings.md — human-readable report flagging:
        · Pairs not yet in cache (with view count = empirical evidence)
        · Pairs where competitor evidence contradicts cache verdict
        · Pairs where competitor evidence confirms cache verdict (validation)

Usage:
    python3 competitor_raga_intel.py

Run monthly. New "ask-Claude" prompts get appended to findings.md so you
can paste them into chat and add verdicts to raga_fit_cache.csv.
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import COMPETITORS
from raga_validator import lookup_raga_fit, mood_from_problem_kw

DATA_DIR = HERE.parent / "data"
USAGE_CSV    = DATA_DIR / "competitor_raga_usage.csv"
FINDINGS_MD  = DATA_DIR / "competitor_raga_findings.md"
USAGE_HEADER = ["channel", "video_id", "published", "views", "title", "raga", "mood"]

# Ragas we know about (lowercase, no "raga " prefix)
RAGAS = [
    "yaman", "bhupali", "darbari", "malkauns", "bageshri", "kafi", "puriya",
    "bhimpalasi", "bhairavi", "bilawal", "bilaval", "todi", "hamir",
    "chandra", "marwa", "bhairav", "kirwani", "hamsadhwani", "charukesi",
    "bhairagi", "rageshree", "shree", "multani", "khamaj", "des",
]

# Mood detection keywords (richer than mood_from_problem_kw — operates on full titles)
MOOD_KWS = {
    "sleep":         ["sleep", "insomnia", "asleep", "deep rest", "rest music", "bedtime"],
    "anxiety":       ["anxiety", "anxious", "panic"],
    "stress":        ["stress", "tension", "exhaust", "burnout", "cortisol"],
    "overthinking":  ["overthink", "overactive", "racing", "rumin", "calm your mind", "calm an"],
    "focus":         ["focus", "concentr", "mental clarity", "brain fog", "clear mind", "restore focus"],
    "meditation":    ["meditat", "spiritual", "dhyan", "sacred"],
    "emotional":     ["emotional", "grief", "sad", "heart", "release", "tender"],
    "morning":       ["morning", "sunrise", "wake", "dawn", "prabhat", "suprabhat", "udaya"],
    "unwind":        ["unwind", "wind down", "evening", "relax"],
    "nervous_system": ["nervous system", "vagus", "somatic"],
    "detox":         ["detox", "digital detox", "dopamine", "negative thoughts", "screen time"],
}


def extract_raga_from_title(title: str) -> Optional[str]:
    """Find the first explicitly-named raga in a title. Returns lowercase raga name."""
    t = title.lower()
    # Pattern 1: "raga X" or "raag X"
    for r in RAGAS:
        if re.search(rf"\b(raga|raag)\s+{r}\b", t):
            return r.replace("bilaval", "bilawal")
    # Pattern 2: "X raga"
    for r in RAGAS:
        if re.search(rf"\b{r}\s+raga\b", t):
            return r.replace("bilaval", "bilawal")
    # Pattern 3: bare raga name (only for distinctive ones unlikely to be other words)
    for r in ["chandra", "bhairavi", "darbari", "malkauns"]:
        if re.search(rf"\b{r}\b", t):
            return r
    return None


def extract_moods_from_title(title: str) -> List[str]:
    """Find all moods referenced in a title. Returns list of mood keys."""
    t = title.lower()
    found = []
    for mood, kws in MOOD_KWS.items():
        if any(kw in t for kw in kws):
            found.append(mood)
    return found


def compose_compound_mood(moods: List[str]) -> List[str]:
    """
    Given a list of moods detected in title, derive compound moods like
    morning_anxiety, night_anxiety. Returns expanded mood list.
    """
    out = list(moods)
    if "morning" in moods:
        for m in ("anxiety", "overthinking", "stress"):
            if m in moods:
                out.append(f"morning_{m}")
    return out


def fetch_competitor_uploads_with_stats(channel_id: str, max_results: int = 50) -> List[dict]:
    """Pull uploads + view counts via YouTube Data API. Returns list of dicts."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("ERROR: google-api-python-client not installed", file=sys.stderr)
        return []

    token_path = HERE.parent / "token.json"
    if not token_path.exists():
        token_path = HERE.parent.parent / "token.json"
    if not token_path.exists():
        print(f"ERROR: token.json not found", file=sys.stderr)
        return []

    creds = Credentials.from_authorized_user_file(str(token_path))
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="contentDetails", id=channel_id).execute()
    if not ch.get("items"):
        return []
    upl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yt.playlistItems().list(part="snippet,contentDetails", playlistId=upl, maxResults=max_results).execute()
    items = pl.get("items", [])
    ids = [it["contentDetails"]["videoId"] for it in items]
    if not ids:
        return []
    stats = yt.videos().list(part="statistics", id=",".join(ids)).execute()
    vstats = {v["id"]: v["statistics"] for v in stats.get("items", [])}
    out = []
    for it in items:
        vid = it["contentDetails"]["videoId"]
        out.append({
            "video_id":  vid,
            "title":     it["snippet"]["title"],
            "published": it["contentDetails"]["videoPublishedAt"][:10],
            "views":     int(vstats.get(vid, {}).get("viewCount", 0)),
        })
    return out


def run():
    print("Fetching competitor uploads…")
    all_pairs = []
    for name, channel_id in COMPETITORS.items():
        print(f"  · {name}…")
        uploads = fetch_competitor_uploads_with_stats(channel_id)
        for u in uploads:
            raga = extract_raga_from_title(u["title"])
            if not raga:
                continue
            moods = compose_compound_mood(extract_moods_from_title(u["title"]))
            for mood in moods:
                all_pairs.append({
                    "channel":   name,
                    "video_id":  u["video_id"],
                    "published": u["published"],
                    "views":     u["views"],
                    "title":     u["title"],
                    "raga":      raga,
                    "mood":      mood,
                })
    print(f"Extracted {len(all_pairs)} (raga, mood) data points across {len(COMPETITORS)} competitors")

    # Write raw usage CSV
    DATA_DIR.mkdir(exist_ok=True)
    with open(USAGE_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=USAGE_HEADER)
        w.writeheader()
        for p in all_pairs:
            w.writerow(p)
    print(f"  → {USAGE_CSV.name}")

    # Aggregate by (raga, mood) for findings report
    agg = defaultdict(lambda: {"count": 0, "views": 0, "channels": set(), "titles": []})
    for p in all_pairs:
        k = (p["raga"], p["mood"])
        agg[k]["count"] += 1
        agg[k]["views"] += p["views"]
        agg[k]["channels"].add(p["channel"])
        agg[k]["titles"].append(f"[{p['published']}] {p['channel']} · {p['views']:,}v · {p['title']}")

    # Cross-reference against cache
    new_pairs, contradictions, validations = [], [], []
    for (raga, mood), d in sorted(agg.items(), key=lambda x: -x[1]["views"]):
        cached = lookup_raga_fit(raga, mood)
        record = {"raga": raga, "mood": mood, "views": d["views"], "count": d["count"],
                  "channels": d["channels"], "titles": d["titles"], "cached": cached}
        if not cached:
            new_pairs.append(record)
        elif cached["fit"] in ("avoid", "caution") and d["views"] >= 10_000:
            contradictions.append(record)
        elif cached["fit"] in ("strong", "ok") and d["views"] >= 5_000:
            validations.append(record)

    # Write findings report
    lines = []
    lines.append(f"# Competitor Raga Intelligence — Findings\n")
    lines.append(f"_Generated from {len(all_pairs)} (raga, mood) data points across {len(COMPETITORS)} competitors._\n")
    lines.append(f"_Source: latest 50 uploads per channel via YouTube Data API._\n\n")
    lines.append("---\n\n")

    lines.append(f"## 🆕 New pairs not yet in `raga_fit_cache.csv` ({len(new_pairs)})\n\n")
    if new_pairs:
        lines.append("Ask Claude for verdicts on these and append to the cache.\n\n")
        for r in new_pairs:
            lines.append(f"### `{r['raga']}` × `{r['mood']}` — {r['views']:,} total views ({r['count']} videos)\n")
            for t in r["titles"][:3]:
                lines.append(f"- {t}\n")
            lines.append(f"\n**Ask-Claude prompt:**\n```\nValidate raga fit: Raga {r['raga'].title()} for \"{r['mood']}\" music content. Reply in JSON: {{\"fit\": \"strong|ok|caution|avoid\", \"reason\": \"one sentence\", \"alternatives\": [\"raga1\"]}}\n```\n\n")
    else:
        lines.append("_(none — cache covers all current competitor patterns)_\n\n")

    lines.append(f"## ⚠️ Contradictions — competitor empirically contradicts cache ({len(contradictions)})\n\n")
    if contradictions:
        lines.append("Cache says avoid/caution but competitor has high views with this pair. Re-examine.\n\n")
        for r in contradictions:
            lines.append(f"### `{r['raga']}` × `{r['mood']}` — cache: **{r['cached']['fit']}** · empirical: **{r['views']:,} views**\n")
            lines.append(f"- Cache reason: _{r['cached']['reason']}_\n")
            for t in r["titles"][:3]:
                lines.append(f"- Evidence: {t}\n")
            lines.append("\n")
    else:
        lines.append("_(none)_\n\n")

    lines.append(f"## ✅ Validations — competitor empirically confirms cache ({len(validations)})\n\n")
    if validations:
        for r in validations:
            lines.append(f"- `{r['raga']}` × `{r['mood']}` — cache **{r['cached']['fit']}** · {r['views']:,} views confirm\n")
        lines.append("\n")
    else:
        lines.append("_(none yet — most cache entries lack 5K+ view validation)_\n\n")

    FINDINGS_MD.write_text("".join(lines))
    print(f"  → {FINDINGS_MD.name}")
    print()
    print(f"Summary: {len(new_pairs)} new · {len(contradictions)} contradictions · {len(validations)} validations")


if __name__ == "__main__":
    run()

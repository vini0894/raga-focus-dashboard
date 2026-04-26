"""
Raga Focus — Competitor Intelligence Layer

Beyond "did they post the same keyword in last 7d", we now extract:

  1. TOP WINNERS — competitor videos ranked by views/day (proven at scale)
  2. RISING — competitor videos with high views/day in last 7-14 days (what's hot NOW)
  3. INSPIRATION — competitor titles topically similar to a candidate keyword
  4. WINNING PATTERNS — what structural elements (Hz, raga naming, question hooks)
     appear in top performers vs flops

Used by generate_ideas.py to surface competitor-validated patterns in every proposal.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from signals import fetch_all_competitor_uploads


# ─────────────────────────────────────────────────────────
# View-per-day calculation (the "is this working" signal)
# ─────────────────────────────────────────────────────────
def _vpd(views: int, days_ago: int) -> float:
    """Views per day. Use max(1, days) to avoid divide-by-zero on same-day uploads."""
    return views / max(1, days_ago)


def get_top_winners(competitor_data: Dict, top_n: int = 10, min_days_age: int = 2):
    """Top competitor videos by total view count (proven at scale).
    Skips videos under 2 days old (haven't accumulated yet)."""
    all_videos = []
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            if u.get("days_ago", 0) < min_days_age:
                continue
            all_videos.append({**u, "competitor": comp_name,
                              "views": u.get("views", 0)})
    all_videos.sort(key=lambda v: -v.get("views", 0))
    return all_videos[:top_n]


def get_rising(competitor_data: Dict, days: int = 14, top_n: int = 5):
    """Recent uploads ranked by views/day. What's hot right now."""
    rising = []
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            if u.get("days_ago", 999) > days:
                continue
            if u.get("days_ago", 0) < 1:
                continue  # need at least 1 day to compute rate
            views = u.get("views", 0)
            if not views:
                continue
            rising.append({
                **u,
                "competitor": comp_name,
                "vpd": round(_vpd(views, u["days_ago"]), 0),
            })
    rising.sort(key=lambda v: -v.get("vpd", 0))
    return rising[:top_n]


# ─────────────────────────────────────────────────────────
# Topic-similarity inspiration matching
# ─────────────────────────────────────────────────────────
_NOISE = {"music", "for", "the", "a", "an", "with", "to", "of", "and", "&",
          "session", "raga", "ragas", "hour", "min", "minutes", "hr",
          "1", "2", "wave", "waves", "indian", "classical", "instrumental"}


def _meaningful_tokens(text: str) -> set:
    return set(w for w in re.findall(r"[a-zA-Z]+", text.lower())
              if w not in _NOISE and len(w) > 2)


def get_inspiration_for(problem_kw: str, competitor_data: Dict, top_n: int = 5):
    """Find competitor videos whose titles share theme with our candidate's problem.

    Returns videos sorted by view count, scored for topic-similarity AND performance.
    """
    candidate_tokens = _meaningful_tokens(problem_kw)
    if not candidate_tokens:
        return []

    matches = []
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            title_tokens = _meaningful_tokens(u["title"])
            common = candidate_tokens & title_tokens
            if not common:
                continue
            views = u.get("views", 0)
            days = u.get("days_ago", 999)
            matches.append({
                **u,
                "competitor":      comp_name,
                "shared_tokens":   list(common),
                "views":           views,
                "vpd":             round(_vpd(views, days), 0) if views else 0,
            })
    # Sort by total views (proven at scale wins)
    matches.sort(key=lambda v: -v.get("views", 0))
    return matches[:top_n]


# ─────────────────────────────────────────────────────────
# Winning pattern extraction
# ─────────────────────────────────────────────────────────
HZ_RE      = re.compile(r"\d{2,4}\s*hz", re.IGNORECASE)
QUESTION_RE = re.compile(r"\?")
RAGA_RE    = re.compile(r"\braga[ng]?\s+\w+", re.IGNORECASE)


def extract_winning_patterns(competitor_data: Dict, top_n_winners: int = 10):
    """Find structural patterns in top performers vs the rest."""
    winners = get_top_winners(competitor_data, top_n=top_n_winners)
    all_videos = []
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" not in u:
                all_videos.append(u)

    if not winners or not all_videos:
        return {}

    def _has_hz(t):       return bool(HZ_RE.search(t))
    def _has_q(t):        return bool(QUESTION_RE.search(t))
    def _has_raga(t):     return bool(RAGA_RE.search(t))

    def _rate(videos, fn):
        return round(100 * sum(1 for v in videos if fn(v["title"])) / len(videos), 1)

    return {
        "winner_count":         len(winners),
        "all_count":            len(all_videos),
        "winners_with_hz_pct":  _rate(winners, _has_hz),
        "all_with_hz_pct":      _rate(all_videos, _has_hz),
        "winners_with_q_pct":   _rate(winners, _has_q),
        "all_with_q_pct":       _rate(all_videos, _has_q),
        "winners_with_raga_pct":_rate(winners, _has_raga),
        "all_with_raga_pct":    _rate(all_videos, _has_raga),
    }


# ─────────────────────────────────────────────────────────
# CLI test
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Pulling competitor RSS …")
    data = fetch_all_competitor_uploads(days=60)

    print("\n━━━ TOP 10 WINNERS (by total views) ━━━")
    for i, v in enumerate(get_top_winners(data, top_n=10), 1):
        print(f"  #{i:2}  {v['views']:>8,} views  ({v['days_ago']:>3}d ago)  "
              f"[{v['competitor']}]  {v['title']}")

    print("\n━━━ TOP 5 RISING (last 14d, by views/day) ━━━")
    for i, v in enumerate(get_rising(data, days=14, top_n=5), 1):
        print(f"  #{i}  {v['vpd']:>5.0f}/day  ({v['days_ago']}d, {v['views']:,} total)  "
              f"[{v['competitor']}]  {v['title']}")

    print("\n━━━ INSPIRATION for 'relaxing instrumental music' ━━━")
    insp = get_inspiration_for("relaxing instrumental music", data, top_n=5)
    if insp:
        for v in insp:
            print(f"  {v['views']:>7,} views  [{v['competitor']}]  {v['title']}")
            print(f"    shared themes: {v['shared_tokens']}")
    else:
        print("  No topical matches in competitor recent catalog")

    print("\n━━━ WINNING STRUCTURAL PATTERNS ━━━")
    patterns = extract_winning_patterns(data, top_n_winners=10)
    print(f"  Hz in title — winners: {patterns['winners_with_hz_pct']}%  vs all: {patterns['all_with_hz_pct']}%")
    print(f"  Question (?) — winners: {patterns['winners_with_q_pct']}%  vs all: {patterns['all_with_q_pct']}%")
    print(f"  Named Raga  — winners: {patterns['winners_with_raga_pct']}%  vs all: {patterns['all_with_raga_pct']}%")

"""
Raga Focus — Pipeline Live Signals

Fetches fresh data each run. NO caching of dates/recency — every call
recomputes from source-of-truth (REACH_HISTORY.csv + competitor RSS).
"""

import csv
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import COMPETITORS, INSTRUMENTS, FREQUENCIES, RAGAS, WAVE_FRAMES, RAGA_FOCUS_CHANNEL_ID

from paths import DATA_DIR
REACH_CSV = DATA_DIR / "REACH_HISTORY.csv"


# ─────────────────────────────────────────────────────────
# Own catalog — RSS first (always-fresh) + REACH_HISTORY for analytics
# ─────────────────────────────────────────────────────────
def _load_reach_csv():
    """Internal: REACH_HISTORY.csv → dict by video_id with analytics."""
    by_id = {}
    if not REACH_CSV.exists():
        return by_id
    with open(REACH_CSV) as f:
        for row in csv.DictReader(f):
            vid = row.get("video_id")
            if not vid:
                continue
            try:
                by_id[vid] = {
                    "video_id":     vid,
                    "title":        row["title"],
                    "publish_date": datetime.strptime(row["publish_date"], "%Y-%m-%d").date(),
                    "views":        int(float(row.get("views", 0) or 0)),
                    "impressions":  int(float(row.get("impressions", 0) or 0)),
                    "ctr_pct":      float(row.get("ctr_pct", 0) or 0),
                    "avd_pct":      float(row.get("avg_view_pct", 0) or 0),
                }
            except (KeyError, ValueError):
                continue
    return by_id


def _fetch_own_rss():
    """Internal: pull own-channel RSS for freshest titles + IDs."""
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={RAGA_FOCUS_CHANNEL_ID}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        return []
    root = ET.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    rows = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.find("atom:title", ns).text or "").strip()
        pub_str = entry.find("atom:published", ns).text
        pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        vid_elem = entry.find("yt:videoId", ns)
        vid = vid_elem.text if vid_elem is not None else None
        rows.append({
            "video_id":     vid,
            "title":        title,
            "publish_date": pub.date(),
            "views":        0,        # unknown from RSS
            "impressions":  0,        # unknown from RSS
            "ctr_pct":      0.0,      # unknown from RSS
            "avd_pct":      0.0,      # unknown from RSS
        })
    return rows


def load_own_catalog():
    """Merge own-channel RSS (always fresh) with REACH_HISTORY (analytics).
    RSS catches new videos immediately. REACH adds CTR/AVD where available."""
    reach = _load_reach_csv()
    rss = _fetch_own_rss()
    by_id = dict(reach)  # start with analytics
    for r in rss:
        if r["video_id"] and r["video_id"] not in by_id:
            by_id[r["video_id"]] = r  # add RSS-only entries (newest videos)
    return sorted(by_id.values(), key=lambda v: v["publish_date"], reverse=True)


# ─────────────────────────────────────────────────────────
# Recency helpers — compute fresh from catalog
# ─────────────────────────────────────────────────────────
def days_since(date_obj, today=None):
    today = today or datetime.now().date()
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    return (today - date_obj).days


def find_in_titles(catalog, needle, within_days=None, today=None):
    """Return list of (days_ago, title) tuples where needle (case-insensitive) appears in title."""
    today = today or datetime.now().date()
    needle = needle.lower()
    matches = []
    for v in catalog:
        if needle in v["title"].lower():
            d = days_since(v["publish_date"], today)
            if within_days is None or d <= within_days:
                matches.append((d, v["title"]))
    return sorted(matches)


# Stop-words for theme-token analysis (these don't count as "themes")
_THEME_STOPWORDS = {
    "music", "for", "the", "a", "an", "with", "to", "of", "and", "&",
    "session", "raga", "ragas", "hour", "min", "minutes", "hr", "1",
    "wave", "waves", "indian", "classical", "instrumental", "no",
    "your", "you", "this", "that", "in", "on", "at",
    # too-generic in our niche — would over-flag almost every title
    "subliminal", "binaural", "beats", "deep", "mind", "calm", "quiet",
}


def _meaningful_tokens(text: str):
    """Extract meaningful theme tokens from a title — skip stopwords + Hz numbers + instrument names + raga names."""
    import re
    instruments = {i["name"].lower() for i in INSTRUMENTS}
    instrument_aliases = set()
    for i in INSTRUMENTS:
        for a in i.get("aliases", []):
            instrument_aliases.add(a.lower())
    waves_l = {w["wave"].lower() for w in WAVE_FRAMES}
    raga_names = {r["name"].lower() for r in RAGAS}
    # Strip Hz patterns
    cleaned = re.sub(r"\d{2,4}\s*hz", " ", text.lower())
    words = re.findall(r"[a-zA-Z]+", cleaned)
    out = []
    for w in words:
        if w in _THEME_STOPWORDS:
            continue
        if w in instruments or w in instrument_aliases:
            continue
        if w in waves_l:
            continue
        if w in raga_names:
            continue
        if len(w) <= 2:
            continue
        out.append(w)
    return out


def theme_overlap_with_recent(catalog, problem_kw: str, within_days: int = 5, today=None):
    """Return overlapping theme tokens between candidate problem keyword and recent titles.

    Returns: list of (overlapping_token, days_ago, title) tuples.
    Used by scoring to penalize candidates whose theme was just covered.
    """
    today = today or datetime.now().date()
    candidate_tokens = set(_meaningful_tokens(problem_kw))
    if not candidate_tokens:
        return []

    overlaps = []
    for v in catalog:
        d = days_since(v["publish_date"], today)
        if d > within_days:
            continue
        title_tokens = set(_meaningful_tokens(v["title"]))
        common = candidate_tokens & title_tokens
        if common:
            for token in common:
                overlaps.append((token, d, v["title"]))
    return sorted(overlaps, key=lambda x: x[1])


def instrument_last_used(catalog, instrument, today=None):
    """Days since this instrument was last used on our channel. None if never."""
    today = today or datetime.now().date()
    aliases = next((i["aliases"] for i in INSTRUMENTS if i["name"] == instrument), [instrument.lower()])
    last = None
    for v in catalog:
        for alias in aliases:
            if alias in v["title"].lower():
                d = days_since(v["publish_date"], today)
                if last is None or d < last:
                    last = d
                break
    return last


def hz_last_used(catalog, hz, today=None):
    today = today or datetime.now().date()
    needle = hz.lower().replace(" ", "")
    last = None
    for v in catalog:
        if needle in v["title"].lower().replace(" ", ""):
            d = days_since(v["publish_date"], today)
            if last is None or d < last:
                last = d
    return last


def raga_last_used(catalog, raga_name, today=None):
    today = today or datetime.now().date()
    pattern = re.compile(rf"\braga\s+{raga_name.lower()}\b|\b{raga_name.lower()}\s+raga\b")
    last = None
    for v in catalog:
        if pattern.search(v["title"].lower()):
            d = days_since(v["publish_date"], today)
            if last is None or d < last:
                last = d
    return last


def wave_last_used(catalog, wave, today=None):
    today = today or datetime.now().date()
    needle = f"{wave.lower()} wave"
    last = None
    for v in catalog:
        if needle in v["title"].lower():
            d = days_since(v["publish_date"], today)
            if last is None or d < last:
                last = d
    return last


# ─────────────────────────────────────────────────────────
# Competitor RSS — fresh each run
# ─────────────────────────────────────────────────────────
def fetch_competitor_uploads(channel_id, days=30):
    """Return [{title, published, days_ago, video_id}] for last N days from RSS."""
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        return [{"error": str(e)}]
    root = ET.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "yt":   "http://www.youtube.com/xml/schemas/2015"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text or ""
        pub_str = entry.find("atom:published", ns).text
        pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        vid_el = entry.find("yt:videoId", ns)
        vid = vid_el.text if vid_el is not None else ""
        if pub >= cutoff:
            out.append({
                "title":     title,
                "days_ago":  (datetime.now(timezone.utc) - pub).days,
                "published": pub.date().isoformat(),
                "video_id":  vid,
            })
    return sorted(out, key=lambda x: x.get("days_ago", 99))


def _enrich_with_stats(uploads_by_competitor):
    """Batch-call YouTube Data API to add views/likes/duration to each upload.
    Falls back silently if creds unavailable (offline, or no token)."""
    try:
        from pathlib import Path as _P
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as _Req
        from googleapiclient.discovery import build as _build

        # Try every reasonable token location for both bundled and standalone layouts
        here = _P(__file__).resolve().parent       # pipeline/
        parent = here.parent                       # raga-focus-dashboard/ (bundled) or project root (standalone)
        token_paths = [
            parent / "token.json",                                       # bundled: dashboard/token.json
            parent / "raga-focus-dashboard" / "token.json",              # standalone with pipeline at root
            parent / "youtube-mcp" / "token.json",                       # standalone, MCP token
            parent.parent / "raga-focus-dashboard" / "token.json",       # extra safety
            parent.parent / "youtube-mcp" / "token.json",                # extra safety
        ]
        SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
        creds = None
        for tp in token_paths:
            if tp.exists():
                creds = Credentials.from_authorized_user_file(str(tp), SCOPES)
                break
        if not creds:
            return uploads_by_competitor
        if not creds.valid and creds.refresh_token:
            creds.refresh(_Req())

        yd = _build("youtube", "v3", credentials=creds, cache_discovery=False)

        # Collect all video IDs across competitors (max 50 per API call)
        all_ids = []
        for uploads in uploads_by_competitor.values():
            for u in uploads:
                if u.get("video_id"):
                    all_ids.append(u["video_id"])
        all_ids = list(dict.fromkeys(all_ids))  # dedupe, preserve order

        stats = {}
        for i in range(0, len(all_ids), 50):
            batch = all_ids[i:i + 50]
            resp = yd.videos().list(part="statistics,contentDetails", id=",".join(batch)).execute()
            for item in resp.get("items", []):
                s = item.get("statistics", {})
                stats[item["id"]] = {
                    "views":    int(s.get("viewCount", 0)),
                    "likes":    int(s.get("likeCount", 0)),
                    "duration": item.get("contentDetails", {}).get("duration", ""),
                }

        # Merge stats into uploads
        for uploads in uploads_by_competitor.values():
            for u in uploads:
                vid = u.get("video_id")
                if vid in stats:
                    u.update(stats[vid])
        return uploads_by_competitor
    except Exception as _e:
        # Never fail the pipeline if enrichment hits an issue — just return raw
        return uploads_by_competitor


def fetch_all_competitor_uploads(days=30, enrich=True):
    """Returns {competitor_name: [uploads]}.
    If `enrich=True` (default), enriches each upload with views/likes/duration
    via the YouTube Data API."""
    raw = {name: fetch_competitor_uploads(cid, days) for name, cid in COMPETITORS.items()}
    if enrich:
        raw = _enrich_with_stats(raw)
    return raw


def competitor_instrument_uses(competitor_data, instrument, within_days=30):
    """Count uses of this instrument across all competitors in window."""
    aliases = next((i["aliases"] for i in INSTRUMENTS if i["name"] == instrument), [instrument.lower()])
    count = 0
    most_recent = None
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            if u["days_ago"] > within_days:
                continue
            title_l = u["title"].lower()
            if any(alias in title_l for alias in aliases):
                count += 1
                if most_recent is None or u["days_ago"] < most_recent:
                    most_recent = u["days_ago"]
    return count, most_recent


def competitor_problem_uses(competitor_data, problem_kw, within_days=14):
    """Find competitor uploads matching the problem keyword in window."""
    out = []
    needle = problem_kw.lower()
    # Strip "music" suffix for broader match
    short_needle = needle.replace(" music", "").strip()
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            if u["days_ago"] > within_days:
                continue
            title_l = u["title"].lower()
            if short_needle in title_l:
                out.append({"competitor": comp_name, **u})
    return out


# ─────────────────────────────────────────────────────────
# Rescue candidates
# ─────────────────────────────────────────────────────────
def find_rescue_candidates(catalog, min_avd=20, max_ctr=2.0, max_impr=1500):
    """High AVD% but low CTR — buried by packaging, not content."""
    out = []
    for v in catalog:
        if v["avd_pct"] >= min_avd and v["ctr_pct"] <= max_ctr and v["impressions"] <= max_impr:
            out.append(v)
    return sorted(out, key=lambda v: -v["avd_pct"])

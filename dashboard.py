"""Raga Focus — Channel Intelligence Dashboard (v0 prototype)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from auth import yt_data as _yt_data, yt_analytics as _yt_analytics, iso_date as _iso
from production_queue import get_all_videos as get_production_queue
try:
    from production_queue import set_video_status, STATUS_VALUES
except ImportError:
    # Graceful fallback if production_queue.py hasn't redeployed yet.
    STATUS_VALUES = ["not_started", "in_progress", "published"]
    def set_video_status(*_args, **_kwargs):
        pass

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Raga Focus — Intelligence Dashboard",
    page_icon="🎵",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Password gate (for shared/cloud deployment)
# -----------------------------------------------------------------------------
def _check_password() -> bool:
    """Display a password prompt and return True once the correct password is entered."""
    # If no password configured in secrets, skip the gate (local dev)
    expected = None
    try:
        if "app" in st.secrets and "password" in st.secrets["app"]:
            expected = st.secrets["app"]["password"]
    except Exception:
        expected = None

    if not expected:
        return True  # no gate when running locally without secrets

    if st.session_state.get("password_correct"):
        return True

    st.markdown("## 🔒 Raga Focus Dashboard")
    st.caption("Enter password to access the dashboard.")
    with st.form("password_form", clear_on_submit=False):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock")
        if submitted:
            if entered == expected:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    return False


if not _check_password():
    st.stop()


COMPETITORS = {
    "Raga Heal": "UCnCW6fiX-6Jykcl2NBQBIbQ",
    "Shanti Instrumentals": "UCGVIda_EdGStdRAFMBh6LAA",
}

REACH_DATA_FILE = Path(__file__).parent / "data" / "REACH_DATA.md"
REACH_HISTORY_FILE = Path(__file__).parent / "data" / "REACH_HISTORY.csv"
KEYWORD_DATA_FILE = Path(__file__).parent / "data" / "KEYWORD_DATA.md"

# CTR / retention benchmarks for the Indian-classical focus/meditation niche
CTR_FLOOR = 2.0   # below = bad
CTR_HEALTHY = 3.0
CTR_EXCELLENT = 6.0
RETENTION_FLOOR = 10.0
RETENTION_HEALTHY = 20.0
RETENTION_EXCELLENT = 35.0


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def parse_iso_duration(iso: str) -> str:
    """Convert ISO 8601 duration (PT1H30M21S) to human-readable (1h 30m 21s or 55:31)."""
    if not iso or not iso.startswith("PT"):
        return iso or "—"
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return iso
    h, mnt, s = m.groups()
    h = int(h) if h else 0
    mnt = int(mnt) if mnt else 0
    s = int(s) if s else 0
    if h:
        return f"{h}h {mnt:02d}m {s:02d}s"
    else:
        return f"{mnt}m {s:02d}s"


def format_minutes_to_hours(minutes: int | float) -> str:
    """Convert raw minutes count into a 'X h Y min' string."""
    if not minutes:
        return "0 min"
    total_min = int(minutes)
    if total_min < 60:
        return f"{total_min} min"
    hours = total_min // 60
    mins = total_min % 60
    return f"{hours}h {mins}min"


# -----------------------------------------------------------------------------
# Data loaders (cached so the dashboard is snappy)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_my_channel_info():
    ch = _yt_data().channels().list(part="snippet,statistics", mine=True).execute()
    c = ch["items"][0]
    return {
        "id": c["id"],
        "title": c["snippet"]["title"],
        "published": c["snippet"]["publishedAt"][:10],
        "subs": int(c["statistics"].get("subscriberCount", 0)),
        "total_views": int(c["statistics"].get("viewCount", 0)),
        "video_count": int(c["statistics"].get("videoCount", 0)),
    }


@st.cache_data(ttl=600)
def load_channel_period_summary(days: int = 28):
    """One-row period totals (no day dimension) — for proper period-level
    retention which can't be derived by averaging daily averageViewPercentage."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    r = (
        _yt_analytics()
        .reports()
        .query(
            ids="channel==MINE",
            startDate=_iso(start),
            endDate=_iso(end),
            metrics="views,averageViewPercentage,subscribersGained,subscribersLost",
        )
        .execute()
    )
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    rows = r.get("rows") or [[0] * len(cols)]
    return dict(zip(cols, rows[0]))


@st.cache_data(ttl=600)
def load_channel_traffic_sources(days: int = 28):
    """Channel-wide traffic source breakdown for the period."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    r = (
        _yt_analytics()
        .reports()
        .query(
            ids="channel==MINE",
            startDate=_iso(start),
            endDate=_iso(end),
            metrics="views",
            dimensions="insightTrafficSourceType",
            sort="-views",
        )
        .execute()
    )
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    return pd.DataFrame(r.get("rows", []), columns=cols)


@st.cache_data(ttl=600)
def load_channel_overview(days: int = 28):
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    r = (
        _yt_analytics()
        .reports()
        .query(
            ids="channel==MINE",
            startDate=_iso(start),
            endDate=_iso(end),
            metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained,likes,shares,comments",
            dimensions="day",
            sort="day",
        )
        .execute()
    )
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    df = pd.DataFrame(r.get("rows", []), columns=cols)
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
    return df


@st.cache_data(ttl=600)
def load_daily_views_all_videos(days: int = 180):
    """Daily views per video across the last N days (one row per day × video).

    YouTube Analytics API doesn't support `day,video` as combined dimensions in
    one query, so we loop over each uploaded video and concatenate the results.
    """
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    ya = _yt_analytics()
    yd = _yt_data()

    # Get all uploaded video IDs
    ch = yd.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids = []
    page = None
    while True:
        pl = yd.playlistItems().list(
            part="contentDetails", playlistId=uploads, maxResults=50, pageToken=page
        ).execute()
        video_ids += [i["contentDetails"]["videoId"] for i in pl["items"]]
        page = pl.get("nextPageToken")
        if not page:
            break

    rows = []
    for vid in video_ids:
        try:
            r = ya.reports().query(
                ids="channel==MINE",
                startDate=_iso(start),
                endDate=_iso(end),
                metrics="views",
                dimensions="day",
                filters=f"video=={vid}",
                sort="day",
            ).execute()
            for day_val, views in r.get("rows", []):
                rows.append({"video": vid, "day": day_val, "views": views})
        except Exception:
            # Video may have no analytics yet (too new); skip.
            continue

    df = pd.DataFrame(rows)
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
    return df


@st.cache_data(ttl=600)
def load_all_my_videos():
    yd = _yt_data()
    ch = yd.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids = []
    page = None
    while True:
        pl = yd.playlistItems().list(
            part="contentDetails", playlistId=uploads, maxResults=50, pageToken=page
        ).execute()
        video_ids += [i["contentDetails"]["videoId"] for i in pl["items"]]
        page = pl.get("nextPageToken")
        if not page:
            break

    rows = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        v = yd.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(batch)
        ).execute()
        for item in v.get("items", []):
            sn = item.get("snippet", {})
            st_ = item.get("statistics", {})
            cd = item.get("contentDetails", {})
            if not sn or not cd:
                continue  # skip deleted / private / region-blocked videos
            rows.append({
                "video_id": item["id"],
                "title": sn.get("title", ""),
                "published": sn.get("publishedAt", "")[:10],
                "duration": cd.get("duration", ""),
                "views": int(st_.get("viewCount", 0)),
                "likes": int(st_.get("likeCount", 0)),
                "comments": int(st_.get("commentCount", 0)),
            })
    return pd.DataFrame(rows).sort_values("published", ascending=False)


@st.cache_data(ttl=600)
def load_video_retention_28d():
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=28)
    r = (
        _yt_analytics()
        .reports()
        .query(
            ids="channel==MINE",
            startDate=_iso(start),
            endDate=_iso(end),
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
            dimensions="video",
            sort="-views",
            maxResults=50,
        )
        .execute()
    )
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    return pd.DataFrame(r.get("rows", []), columns=cols)


@st.cache_data(ttl=3600)
def load_competitor_stats():
    yd = _yt_data()
    rows = []
    for name, cid in COMPETITORS.items():
        ch = yd.channels().list(part="snippet,statistics", id=cid).execute()
        c = ch["items"][0]
        rows.append({
            "Channel": name,
            "Subscribers": int(c["statistics"].get("subscriberCount", 0)),
            "Total Views": int(c["statistics"].get("viewCount", 0)),
            "Videos": int(c["statistics"].get("videoCount", 0)),
            "Started": c["snippet"]["publishedAt"][:10],
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def load_competitor_latest_videos(channel_id: str, limit: int = 5):
    yd = _yt_data()
    ch = yd.channels().list(part="contentDetails", id=channel_id).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yd.playlistItems().list(
        part="contentDetails,snippet", playlistId=uploads, maxResults=limit
    ).execute()
    vids = [i["contentDetails"]["videoId"] for i in pl["items"]]
    v = yd.videos().list(part="snippet,statistics,contentDetails", id=",".join(vids)).execute()
    rows = []
    for item in v.get("items", []):
        sn = item.get("snippet", {})
        st_ = item.get("statistics", {})
        cd = item.get("contentDetails", {})
        if not sn or not cd:
            continue
        rows.append({
            "Published": sn.get("publishedAt", "")[:10],
            "Title": sn.get("title", "")[:75],
            "Views": int(st_.get("viewCount", 0)),
            "Likes": int(st_.get("likeCount", 0)),
            "Duration": parse_iso_duration(cd.get("duration", "")),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def load_video_detail(video_id: str):
    """Full metadata + 28d analytics + traffic sources for one video."""
    yd = _yt_data()
    ya = _yt_analytics()

    # Metadata
    v = yd.videos().list(part="snippet,statistics,contentDetails", id=video_id).execute()
    if not v.get("items"):
        return None
    item = v["items"][0]
    sn = item.get("snippet", {})
    st_ = item.get("statistics", {})
    cd = item.get("contentDetails", {})

    detail = {
        "video_id": video_id,
        "title": sn.get("title", ""),
        "description": sn.get("description", ""),
        "tags": sn.get("tags", []),
        "published": sn.get("publishedAt", "")[:10],
        "duration": cd.get("duration", ""),
        "lifetime_views": int(st_.get("viewCount", 0)),
        "lifetime_likes": int(st_.get("likeCount", 0)),
        "lifetime_comments": int(st_.get("commentCount", 0)),
    }

    # 28d analytics
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=28)
    detail["analytics_error"] = None
    try:
        r = ya.reports().query(
            ids="channel==MINE",
            startDate=_iso(start), endDate=_iso(end),
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,shares,comments",
            filters=f"video=={video_id}",
        ).execute()
        cols = [h["name"] for h in r.get("columnHeaders", [])]
        rows = r.get("rows") or []
        if rows:
            detail["analytics_28d"] = dict(zip(cols, rows[0]))
        else:
            # API succeeded but returned no rows — common for very new
            # videos or videos with zero activity in the window.
            detail["analytics_28d"] = {}
            detail["analytics_error"] = "no_rows"
    except Exception as e:
        detail["analytics_28d"] = {}
        detail["analytics_error"] = f"api_error: {type(e).__name__}: {e}"

    # Traffic sources
    try:
        r = ya.reports().query(
            ids="channel==MINE",
            startDate=_iso(start), endDate=_iso(end),
            metrics="views,estimatedMinutesWatched,averageViewDuration",
            dimensions="insightTrafficSourceType",
            filters=f"video=={video_id}",
            sort="-views",
        ).execute()
        cols = [h["name"] for h in r.get("columnHeaders", [])]
        detail["traffic_sources"] = [dict(zip(cols, row)) for row in r.get("rows", [])]
    except Exception:
        detail["traffic_sources"] = []

    return detail


# Keyword database parsed from KEYWORD_DATA.md
@st.cache_data(ttl=600)
def load_keyword_database():
    """Parse KEYWORD_DATA.md and return dict of {keyword_lower: {score, verdict, notes}}."""
    db = {}
    if not KEYWORD_DATA_FILE.exists():
        return db
    text = KEYWORD_DATA_FILE.read_text()

    # Parse HIGH-scoring tables (Validated / HIGH rows)
    # Match table rows with a keyword and score
    # Patterns like: | ADHD focus music | 86 | Medium | 70 HIGH | ...
    high_pattern = re.compile(
        r"\|\s*([a-zA-Z0-9 _/+&'\"\.\-]+?)\s*\|\s*(\d+)\s*\|\s*(Low|Medium|High)\s*\|\s*(\d+)\s+(HIGH|Medium|Low)"
    )
    for m in high_pattern.finditer(text):
        kw, volume, comp, score, label = m.groups()
        key = kw.strip().lower()
        if key and not any(stop in key for stop in ["keyword", "tag"]):
            db[key] = {
                "volume": int(volume),
                "competition": comp,
                "score": int(score),
                "label": label.upper(),
                "verdict": "✅ HIGH" if label.upper() == "HIGH" else f"⚠️ {label}",
            }

    # Tag-score table rows: | pomodoro music | 77 | note |
    tag_pattern = re.compile(r"\|\s*([a-zA-Z0-9 _/+&'\"\.\-]+?)\s*\|\s*(\d+)\s*\|\s+(.+?)\s*\|")
    for m in tag_pattern.finditer(text):
        kw, score, note = m.groups()
        key = kw.strip().lower()
        if (
            key
            and key not in db
            and len(key) > 3
            and not any(stop in key for stop in ["tag", "keyword", "score", "verdict", "volume"])
        ):
            score_int = int(score)
            db[key] = {
                "volume": None,
                "competition": None,
                "score": score_int,
                "label": "HIGH" if score_int >= 60 else ("MEDIUM" if score_int >= 40 else "LOW"),
                "verdict": "✅ HIGH" if score_int >= 60 else ("⚠️ MEDIUM" if score_int >= 40 else "🚫 LOW"),
                "notes": note.strip()[:80],
            }

    # Invalidated/blacklist section — parse rows that explicitly say "DO NOT USE" or score < 30
    invalid_pattern = re.compile(
        r"\|\s*([a-zA-Z0-9 _/+&'\"\.\-]+?)\s*\|\s*(\d+|0)\s*\|\s*\d+\s+Low\s*\|"
    )
    for m in invalid_pattern.finditer(text):
        kw, score = m.groups()
        key = kw.strip().lower()
        if key and key not in db:
            db[key] = {
                "volume": int(score),
                "score": int(score),
                "label": "INVALIDATED",
                "verdict": "🚫 Invalidated (0 volume)",
            }

    return db


def analyze_keywords(text: str, db: dict) -> list[dict]:
    """Return list of matched keywords with their scores, highest-score first."""
    if not text or not db:
        return []
    text_lower = text.lower()
    matches = []
    for kw, data in db.items():
        if kw in text_lower:
            matches.append({"keyword": kw, **data})
    # Sort by score desc
    matches.sort(key=lambda x: x.get("score", 0), reverse=True)
    return matches


def generate_recommendations(detail: dict, reach_row: pd.Series | None, kw_matches: list) -> list[str]:
    """Produce a prioritized list of actionable bullet recommendations."""
    recs = []
    analytics = detail.get("analytics_28d", {})
    views = analytics.get("views", 0) or 0
    avg_pct = analytics.get("averageViewPercentage", 0) or 0
    subs_gained = analytics.get("subscribersGained", 0) or 0
    traffic = detail.get("traffic_sources", [])

    # Impressions / CTR (from REACH_DATA.md)
    impressions = None
    ctr = None
    if reach_row is not None:
        impr_str = str(reach_row.get("Impressions", "")).strip().lower()
        if "k" in impr_str:
            try:
                impressions = int(float(impr_str.replace("k", "")) * 1000)
            except Exception:
                impressions = None
        else:
            try:
                impressions = int(impr_str)
            except Exception:
                impressions = None

        ctr_str = str(reach_row.get("CTR", "")).replace("%", "").strip()
        try:
            ctr = float(ctr_str)
        except Exception:
            ctr = None

    # RULE 1: Low CTR → thumbnail problem
    if ctr is not None:
        if ctr < CTR_FLOOR:
            recs.append(f"🔴 **CTR is {ctr:.1f}% (below {CTR_FLOOR}% floor)** → Thumbnail likely weak. Redo thumbnail with the validated moon+sky+instrument system. This is your #1 priority.")
        elif ctr < CTR_HEALTHY:
            recs.append(f"🟡 **CTR is {ctr:.1f}% (healthy is {CTR_HEALTHY}%+)** → Thumbnail is okay but not attractive. Consider testing a clearer benefit-hook overlay (e.g., 'MORNING FOCUS').")
        elif ctr >= CTR_EXCELLENT:
            recs.append(f"🟢 **CTR is {ctr:.1f}% — excellent!** This thumbnail/title combo works. Replicate the pattern on future videos.")

    # RULE 2: Low retention → content/title mismatch
    if avg_pct and avg_pct < RETENTION_FLOOR:
        recs.append(f"🔴 **Retention is {avg_pct:.1f}% (below {RETENTION_FLOOR}% floor)** → Viewers expect something different from what the video delivers. Either rename the title to match the actual vibe, or flag this video to stop promoting.")
    elif avg_pct and avg_pct < RETENTION_HEALTHY:
        recs.append(f"🟡 **Retention is {avg_pct:.1f}% (healthy is {RETENTION_HEALTHY}%+)** → Title/thumbnail may be over-promising. Review intro — is the music energetic when title says 'calm'?")
    elif avg_pct and avg_pct >= RETENTION_EXCELLENT:
        recs.append(f"🟢 **Retention is {avg_pct:.1f}% — excellent!** This is the audience your title is attracting. Make more videos for this same intent.")

    # RULE 3: Low impressions → SEO problem
    if impressions is not None and impressions < 500:
        recs.append(f"🔴 **Only {impressions:,} impressions** → YouTube isn't surfacing this video. Title likely has no high-volume keywords. Check the keyword analysis below — is there a HIGH-score anchor term?")
    elif impressions is not None and impressions < 2000:
        recs.append(f"🟡 **{impressions:,} impressions** → Low-to-moderate surfacing. Add 2-3 validated high-score keywords to the title or description.")

    # RULE 4: High views but 0 subs → identity problem
    if views > 30 and subs_gained == 0:
        recs.append(f"🟡 **{views} views in 28d but ZERO subs gained** → Video solves an acute problem but doesn't build an ongoing identity. Viewers use once, leave. Consider reframing as 'for [identity]' (overthinkers, creative pros) instead of 'for [problem]' (burnout, stuck).")

    # RULE 5: Subs converting well
    if views > 0 and subs_gained and (subs_gained / max(views, 1)) > 0.03:
        conversion = (subs_gained / views) * 100
        recs.append(f"🟢 **{conversion:.1f}% sub conversion rate** (any rate above 3% is exceptional). This video has strong identity appeal. Make 3-5 more videos with the same framing.")

    # RULE 6: Traffic source analysis
    if traffic:
        sources = {t["insightTrafficSourceType"]: t["views"] for t in traffic}
        total_views_tracked = sum(sources.values())
        search_pct = (sources.get("YT_SEARCH", 0) / total_views_tracked * 100) if total_views_tracked else 0
        browse_pct = (sources.get("BROWSE", 0) / total_views_tracked * 100) if total_views_tracked else 0
        suggested_pct = (sources.get("RELATED_VIDEO", 0) / total_views_tracked * 100) if total_views_tracked else 0

        if total_views_tracked >= 10:
            if search_pct < 5 and sources.get("YT_SEARCH", 0) == 0:
                recs.append("🟡 **Zero views from Search** → Title/tags don't match any searchable intent. Add validated HIGH-score keywords. Check keyword section below.")
            if browse_pct == 0:
                recs.append("🟡 **Zero views from Browse feed** → YouTube hasn't decided to recommend this on the home feed. Usually fixes itself after 14 days if retention is strong.")
            if suggested_pct > 40:
                recs.append(f"🟢 **{suggested_pct:.0f}% of views from 'Related video' (Suggested)** → YouTube is pairing you with similar videos. This is the discovery mechanism that scales.")

    # RULE 7: Keyword coverage
    if kw_matches:
        high_count = sum(1 for m in kw_matches if m["label"] == "HIGH")
        invalid_count = sum(1 for m in kw_matches if m["label"] == "INVALIDATED")
        if high_count == 0:
            recs.append("🔴 **Title/description contains NO validated HIGH-score keywords** → Rewrite to include at least 1-2. Priority: 'anxiety relief music', 'overthinking music', 'ADHD focus music', 'tabla music', 'deep work music'.")
        elif high_count >= 2:
            recs.append(f"🟢 **{high_count} HIGH-score keywords detected in metadata** → Good SEO coverage.")
        if invalid_count > 0:
            invalids = ", ".join(m["keyword"] for m in kw_matches if m["label"] == "INVALIDATED")
            recs.append(f"🟡 **Invalidated phrases detected: {invalids}** → These have 0 search volume. Not harmful but wasted opportunity — replace with HIGH-score synonyms.")

    # RULE 8: Description length
    desc_len = len(detail.get("description", ""))
    if desc_len < 500:
        recs.append(f"🟡 **Description is only {desc_len} chars** → YouTube uses description heavily for ranking. Target 1200+ chars with chapters, benefits, and hashtags.")

    # RULE 9: Tags
    tags = detail.get("tags", [])
    if len(tags) == 0:
        recs.append("🟡 **No tags set** → Not fatal (Raga Heal uses zero tags on their 997K video) but adding 15-20 validated tags gives you more SEO surface.")
    elif len(tags) > 35:
        recs.append(f"🟡 **{len(tags)} tags set** → YouTube only indexes first ~500 chars. Keep 15-20 highest-value tags and drop the rest.")

    if not recs:
        recs.append("✅ No critical issues detected. Keep monitoring metrics.")
    return recs


@st.cache_data(ttl=600)
def load_reach_history():
    """Load REACH_HISTORY.csv — time-series of impressions/CTR per video."""
    if not REACH_HISTORY_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(REACH_HISTORY_FILE)
    if not df.empty:
        df["capture_date"] = pd.to_datetime(df["capture_date"])
    return df


def get_latest_reach_per_video() -> pd.DataFrame:
    """Return latest CTR/impressions snapshot per video from REACH_HISTORY.csv."""
    hist = load_reach_history()
    if hist.empty:
        return pd.DataFrame()
    latest = hist.sort_values("capture_date").groupby("video_id").tail(1)
    return latest[["video_id", "capture_date", "views", "impressions", "ctr_pct"]].copy()


def parse_reach_data():
    """Parse REACH_DATA.md to extract impressions / CTR for our videos."""
    if not REACH_DATA_FILE.exists():
        return pd.DataFrame()
    text = REACH_DATA_FILE.read_text()
    # Match table rows: | N | Title | `ID` | Dur | Pub | Impr | CTR | Views | Unique |
    pattern = re.compile(
        r"\|\s*\d+\s*\|\s*(.*?)\s*\|\s*`([^`]+)`\s*\|\s*([\d:]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|"
    )
    rows = []
    for m in pattern.finditer(text):
        title, vid, dur, pub, impr, ctr, views, unique = m.groups()
        rows.append({
            "video_id": vid,
            "Impressions": impr.strip(),
            "CTR": ctr.strip(),
            "Views (Reach)": int(views),
            "Unique Viewers": unique.strip(),
        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.title("🎵 Raga Focus — Channel Intelligence Dashboard")
st.caption("v0 prototype · data cached 10 min · refresh browser to force reload")

# Sidebar
with st.sidebar:
    st.header("Controls")
    period = st.selectbox("Time period", [7, 14, 28, 90], index=2, format_func=lambda x: f"Last {x} days")
    if st.button("🔄 Clear cache & refresh"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Dashboard reads from YouTube API via the authenticated MCP server + REACH_DATA.md for manual reach captures.")

# Tabs
tab_overview, tab_daily, tab_videos, tab_detail, tab_competitors, tab_briefs, tab_idea_gen, tab_title_builder, tab_playlists = st.tabs(
    ["📊 Overview", "📈 Daily Views", "📺 Videos", "🔍 Video Detail", "⚔️ Competitors", "🧠 Brief Queue", "🧪 A/B Insights", "🔤 Title Builder", "🎵 Playlists"]
)

# -----------------------------------------------------------------------------
# Tab: Overview
# -----------------------------------------------------------------------------
with tab_overview:
    with st.spinner("Loading channel info..."):
        info = load_my_channel_info()
        # The catalog (uploads playlist) refreshes faster than the
        # channel-level statistics fields, which can lag by hours.
        # Compute counts from the catalog so all tabs agree.
        catalog = load_all_my_videos()

    fresh_video_count = len(catalog) if not catalog.empty else info["video_count"]
    fresh_total_views = int(catalog["views"].sum()) if not catalog.empty else info["total_views"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Subscribers", f"{info['subs']:,}")
    col2.metric("Total Views", f"{fresh_total_views:,}")
    col3.metric("Videos Published", fresh_video_count)
    col4.metric("Channel Age", f"{(date.today() - pd.to_datetime(info['published']).date()).days} days")

    st.divider()

    with st.spinner(f"Loading last {period} days..."):
        df = load_channel_overview(period)
        period_summary = load_channel_period_summary(period)
        traffic_sources = load_channel_traffic_sources(period)

    if df.empty:
        st.info("No analytics data yet for this period.")
    else:
        total_watch_min = int(df['estimatedMinutesWatched'].sum())
        avg_dur_sec = int(df['averageViewDuration'].mean())
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
        sub_col1.metric(f"Views ({period}d)", f"{int(df['views'].sum()):,}")
        sub_col2.metric(f"Watch time ({period}d)", format_minutes_to_hours(total_watch_min))
        sub_col3.metric(f"Subs gained ({period}d)", int(df["subscribersGained"].sum()))
        sub_col4.metric(f"Avg view duration", f"{avg_dur_sec / 60:.1f} min")

        # Second row — channel-health metrics from API.
        retention_pct = float(period_summary.get("averageViewPercentage", 0) or 0)

        TRAFFIC_LABELS = {
            "YT_SEARCH": "🔍 YouTube Search",
            "BROWSE": "🏠 Browse feed",
            "RELATED_VIDEO": "▶️ Suggested",
            "SUBSCRIBER": "🔔 Subscriber feed",
            "NO_LINK_OTHER": "↪️ Direct / other",
            "EXT_URL": "🌐 External",
            "YT_CHANNEL": "📺 Channel page",
            "YT_OTHER_PAGE": "📄 Other YT page",
            "PLAYLIST": "📋 Playlist",
            "END_SCREEN": "🎬 End screen",
            "NOTIFICATION": "🔔 Notification",
            "SHORTS": "📱 Shorts feed",
        }

        if not traffic_sources.empty:
            top_row = traffic_sources.iloc[0]
            top_source_raw = top_row["insightTrafficSourceType"]
            top_source = TRAFFIC_LABELS.get(top_source_raw, top_source_raw)
            top_source_views = int(top_row["views"])
            total_source_views = int(traffic_sources["views"].sum())
            top_pct = (top_source_views / total_source_views * 100) if total_source_views else 0
            top_source_display = f"{top_source}"
            top_source_help = f"{top_pct:.0f}% of views ({top_source_views:,} of {total_source_views:,}) came from this source over the last {period} days."
        else:
            top_source_display = "—"
            top_source_help = "No traffic source data yet."
            top_pct = 0

        h_col1, h_col2 = st.columns(2)
        h_col1.metric(
            f"Retention ({period}d)",
            f"{retention_pct:.1f}%",
            help=(
                "Channel-wide average view percentage — how much of each video the average viewer watches. "
                "Niche benchmark for long-form meditation/focus music: 15-25% healthy, 30%+ excellent. "
                "Below 10% = title/thumbnail attracting wrong audience."
            ),
        )
        h_col2.metric(
            f"Top traffic source ({period}d)",
            top_source_display,
            delta=f"{top_pct:.0f}% of views" if top_pct else None,
            delta_color="off",
            help=top_source_help,
        )

        fig = px.line(
            df, x="day", y="views",
            title=f"Daily views — last {period} days",
            markers=True,
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0), template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
        st.plotly_chart(fig, width="stretch")

        # Convert watch minutes to hours for the chart
        df_chart = df.copy()
        df_chart["watch_hours"] = (df_chart["estimatedMinutesWatched"] / 60).round(2)
        fig2 = px.bar(
            df_chart, x="day", y="watch_hours",
            title=f"Daily watch time (hours) — last {period} days",
            labels={"watch_hours": "Hours watched", "day": ""},
        )
        fig2.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, width="stretch")

    # -------------------------------------------------------------------------
    # CTR Health Panel (reads REACH_HISTORY.csv — latest capture per video)
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("🎯 CTR Health — thumbnail performance")

    reach_latest = get_latest_reach_per_video()
    if reach_latest.empty:
        st.info(
            "No reach data yet. Drop a Studio CSV export into `data/reach_exports/` and run "
            "`python3 import_reach_csv.py` to populate this panel."
        )
    else:
        # Attach titles
        vids_meta = load_all_my_videos()[["video_id", "title"]]
        health = reach_latest.merge(vids_meta, on="video_id", how="left")
        health["title"] = health["title"].fillna(health["video_id"])

        # Filter to videos with meaningful impression volume (noise-reduction)
        MIN_IMPR = 300
        reliable = health[health["impressions"] >= MIN_IMPR].copy()
        noisy = health[health["impressions"] < MIN_IMPR].copy()

        # Classify
        def classify(ctr):
            if ctr < CTR_FLOOR:
                return "🔴 Below floor"
            elif ctr < CTR_HEALTHY:
                return "🟡 Okay"
            elif ctr < CTR_EXCELLENT:
                return "🟢 Healthy"
            else:
                return "🔥 Excellent"

        reliable["status"] = reliable["ctr_pct"].apply(classify)

        # Summary cards
        counts = reliable["status"].value_counts().to_dict()
        capture_dates = reach_latest["capture_date"].dropna()
        latest_capture = capture_dates.max().date() if not capture_dates.empty else "—"

        st.caption(
            f"Based on latest capture per video ({latest_capture}). "
            f"Classifying only videos with ≥{MIN_IMPR} impressions ({len(reliable)} of {len(health)} videos) "
            f"to avoid noise from low-surface videos."
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 Excellent (≥6%)", counts.get("🔥 Excellent", 0))
        c2.metric("🟢 Healthy (3-6%)", counts.get("🟢 Healthy", 0))
        c3.metric("🟡 Okay (2-3%)", counts.get("🟡 Okay", 0))
        c4.metric("🔴 Below floor (<2%)", counts.get("🔴 Below floor", 0))

        # Channel weighted CTR (total clicks / total impressions)
        total_impr = int(reliable["impressions"].sum())
        # Approx clicks = impressions * ctr_pct/100
        reliable["est_clicks"] = reliable["impressions"] * reliable["ctr_pct"] / 100
        channel_ctr = (reliable["est_clicks"].sum() / total_impr * 100) if total_impr else 0

        st.markdown(
            f"**Channel-weighted CTR:** {channel_ctr:.2f}%  ·  "
            f"**Total impressions tracked:** {total_impr:,}  ·  "
            f"**Niche benchmark:** 3–6%"
        )

        # Two tables side by side: top performers + bottom performers
        col_top, col_bot = st.columns(2)

        with col_top:
            st.markdown("**🟢 Top 5 CTR (high-confidence)**")
            top5 = reliable.nlargest(5, "ctr_pct")[["title", "ctr_pct", "impressions", "views"]].copy()
            top5["title"] = top5["title"].apply(lambda t: (t[:55] + "…") if len(t) > 55 else t)
            top5 = top5.rename(columns={
                "title": "Title", "ctr_pct": "CTR %",
                "impressions": "Impressions", "views": "Views",
            })
            top5["CTR %"] = top5["CTR %"].apply(lambda x: f"{x:.2f}%")
            top5["Impressions"] = top5["Impressions"].apply(lambda x: f"{int(x):,}")
            st.dataframe(top5, width="stretch", hide_index=True)

        with col_bot:
            st.markdown("**🔴 Bottom 5 CTR — thumbnail/title rewrite candidates**")
            bot5 = reliable.nsmallest(5, "ctr_pct")[["title", "ctr_pct", "impressions", "views"]].copy()
            bot5["title"] = bot5["title"].apply(lambda t: (t[:55] + "…") if len(t) > 55 else t)
            bot5 = bot5.rename(columns={
                "title": "Title", "ctr_pct": "CTR %",
                "impressions": "Impressions", "views": "Views",
            })
            bot5["CTR %"] = bot5["CTR %"].apply(lambda x: f"{x:.2f}%")
            bot5["Impressions"] = bot5["Impressions"].apply(lambda x: f"{int(x):,}")
            st.dataframe(bot5, width="stretch", hide_index=True)

        # CTR bar chart — all reliable videos, colored by status
        st.markdown("**CTR per video (impressions ≥300)**")
        chart_df = reliable.sort_values("ctr_pct", ascending=True).copy()
        chart_df["short_title"] = chart_df["title"].apply(lambda t: (t[:50] + "…") if len(t) > 50 else t)
        fig_ctr = px.bar(
            chart_df, x="ctr_pct", y="short_title", orientation="h",
            color="status",
            color_discrete_map={
                "🔴 Below floor": "#EF553B",
                "🟡 Okay": "#FFA15A",
                "🟢 Healthy": "#00CC96",
                "🔥 Excellent": "#19D3F3",
            },
            title="CTR % per video",
            labels={"ctr_pct": "CTR %", "short_title": ""},
            hover_data={"impressions": True, "views": True},
        )
        fig_ctr.add_vline(x=CTR_FLOOR, line_dash="dash", line_color="#EF553B", annotation_text=f"{CTR_FLOOR}% floor")
        fig_ctr.add_vline(x=CTR_HEALTHY, line_dash="dash", line_color="#00CC96", annotation_text=f"{CTR_HEALTHY}% healthy")
        fig_ctr.add_vline(x=CTR_EXCELLENT, line_dash="dash", line_color="#19D3F3", annotation_text=f"{CTR_EXCELLENT}% excellent")
        fig_ctr.update_layout(
            height=max(350, 30 * len(chart_df)),
            margin=dict(l=0, r=0, t=40, b=0),
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="left", x=0),
        )
        st.plotly_chart(fig_ctr, width="stretch")

        # Noisy videos — too few impressions to judge
        if not noisy.empty:
            with st.expander(f"⚪ {len(noisy)} videos with <{MIN_IMPR} impressions (insufficient data to judge)"):
                noisy_show = noisy[["title", "ctr_pct", "impressions", "views"]].copy()
                noisy_show["title"] = noisy_show["title"].apply(lambda t: (t[:70] + "…") if len(t) > 70 else t)
                noisy_show = noisy_show.rename(columns={
                    "title": "Title", "ctr_pct": "CTR %",
                    "impressions": "Impressions", "views": "Views",
                })
                noisy_show["CTR %"] = noisy_show["CTR %"].apply(lambda x: f"{x:.2f}%")
                noisy_show = noisy_show.sort_values("Impressions", ascending=False)
                st.dataframe(noisy_show, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Tab: Daily Views (historical per-video + channel totals)
# -----------------------------------------------------------------------------
with tab_daily:
    st.subheader("📈 What's earning views right now")
    st.caption("Per-video momentum view. Δ = absolute view count change vs. the prior equal-length period. Sparkline = last 14 days. Analytics API has a 24-48h lag, so today and yesterday may read low.")

    lookback = st.selectbox(
        "Lookback window",
        [1, 3, 7, 14, 28, 60],
        index=2,
        format_func=lambda x: "Yesterday" if x == 1 else f"Last {x} days",
        key="daily_lookback",
    )

    # Load 2x lookback (for prior-period Δ) and at least 28 days (for 14d sparkline + comparison).
    load_window = max(28, lookback * 2)
    with st.spinner(f"Loading {load_window} days of daily data..."):
        per_vid = load_daily_views_all_videos(load_window)
        all_vids = load_all_my_videos()

    if per_vid.empty:
        st.info("No per-video daily data available yet.")
    else:
        # Attach titles + publish dates
        meta = all_vids[["video_id", "title", "published"]].rename(columns={"video_id": "video"})
        per_vid = per_vid.merge(meta, on="video", how="left")
        per_vid["title"] = per_vid["title"].fillna(per_vid["video"])

        today = pd.Timestamp(date.today())
        cur_start = today - pd.Timedelta(days=lookback)
        prev_start = today - pd.Timedelta(days=lookback * 2)
        spark_start = today - pd.Timedelta(days=14)
        # "Latest day" = the most recent date with any reported data (works
        # around the 24-48h API lag — naive "yesterday" often returns 0s).
        latest_day = per_vid["day"].max() if not per_vid.empty else None

        # Aggregate per video: current-period views, prior-period views, sparkline, days since publish
        rows = []
        for vid, grp in per_vid.groupby("video"):
            grp = grp.sort_values("day")
            cur = int(grp[grp["day"] >= cur_start]["views"].sum())
            prev = int(grp[(grp["day"] >= prev_start) & (grp["day"] < cur_start)]["views"].sum())
            yday = int(grp[grp["day"] == latest_day]["views"].sum()) if latest_day is not None else 0
            # Build a 14-day sparkline (zero-fill missing days so the line doesn't lie).
            # Defensive: collapse any same-day duplicates with .groupby(level=0).sum()
            # before reindex — duplicates trip "cannot reindex on an axis with
            # duplicate labels" (seen when the metadata merge introduces dupes
            # or when the analytics API returns multiple rows for one video×day).
            spark = (
                grp[grp["day"] >= spark_start]
                .set_index("day")["views"]
                .groupby(level=0).sum()
                .reindex(pd.date_range(spark_start, today - pd.Timedelta(days=1)), fill_value=0)
                .tolist()
            )
            title = grp["title"].iloc[0]
            published = grp["published"].iloc[0]
            days_since_publish = (
                (today.date() - pd.to_datetime(published).date()).days
                if pd.notna(published) else None
            )
            rows.append({
                "Title": (title[:55] + "…") if len(title) > 55 else title,
                "video": vid,
                "Yesterday": yday,
                "Views": cur,
                "Δ vs. prior": cur - prev,
                "Days since publish": days_since_publish,
                "Trend (14d)": spark,
            })

        table_df = pd.DataFrame(rows)
        # Drop dead videos (no views in window AND no prior views) — reduces noise
        table_df = table_df[(table_df["Views"] > 0) | (table_df["Δ vs. prior"] != 0)]
        table_df = table_df.sort_values("Views", ascending=False).reset_index(drop=True)

        # Hide the redundant "Yesterday" column when the lookback already IS 1 day.
        display_cols = ["Title", "Yesterday", "Views", "Δ vs. prior", "Days since publish", "Trend (14d)"]
        if lookback == 1:
            display_cols.remove("Yesterday")

        # --- Headline table
        st.markdown("#### 🔥 Earning right now")
        if table_df.empty:
            st.info(f"No videos earned views in the last {lookback} days.")
        else:
            latest_label = (
                f"Latest day ({latest_day.strftime('%b %d')})"
                if latest_day is not None else "Latest day"
            )
            st.dataframe(
                table_df[display_cols],
                width="stretch",
                hide_index=True,
                column_config={
                    "Yesterday": st.column_config.NumberColumn(
                        latest_label, format="%d",
                        help="Views on the most recent date with reported data. The YouTube Analytics API has a 24-48h lag, so this is usually 1-2 days behind today.",
                    ),
                    "Views": st.column_config.NumberColumn(f"Views (last {lookback}d)", format="%d"),
                    "Δ vs. prior": st.column_config.NumberColumn(
                        f"Δ vs. prior {lookback}d", format="%+d",
                        help="Absolute change in views compared to the equivalent period before this one.",
                    ),
                    "Days since publish": st.column_config.NumberColumn("Days live", format="%d"),
                    "Trend (14d)": st.column_config.LineChartColumn(
                        "Trend (14d)", y_min=0,
                        help="Daily views over the last 14 days.",
                    ),
                },
            )

        st.divider()

        # --- Chart: per-video timeline, default to top 5 by current-window views
        st.markdown("#### Daily timeline")
        st.caption("Top 5 videos by current-window views are plotted by default. Add or remove videos as needed.")

        plot_window = per_vid[per_vid["day"] >= cur_start].copy()
        plot_window["label"] = plot_window["title"].apply(
            lambda t: (t[:55] + "…") if len(t) > 55 else t
        )
        totals = plot_window.groupby("label")["views"].sum().sort_values(ascending=False)
        if totals.empty:
            st.info("Nothing to plot for this window.")
        else:
            default_selection = totals.head(5).index.tolist()
            all_labels = totals.index.tolist()

            selected = st.multiselect(
                f"Videos on chart ({len(all_labels)} earned views in window)",
                options=all_labels,
                default=default_selection,
                key="daily_video_pick",
            )

            if selected:
                fig = px.line(
                    plot_window[plot_window["label"].isin(selected)].sort_values("day"),
                    x="day", y="views", color="label",
                    title=f"Daily views — last {lookback} days",
                    labels={"views": "Views", "day": "", "label": "Video"},
                )
                fig.update_layout(
                    height=450,
                    margin=dict(l=0, r=0, t=40, b=0),
                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0),
                    template="plotly_dark",
                    paper_bgcolor="#0E1117",
                    plot_bgcolor="#0E1117",
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Pick at least one video to plot.")


# -----------------------------------------------------------------------------
# Tab: Videos
# -----------------------------------------------------------------------------
with tab_videos:
    with st.spinner("Loading video catalog + retention..."):
        videos = load_all_my_videos()
        retention = load_video_retention_28d()
        # Prefer REACH_HISTORY.csv (Studio CSV imports) over legacy REACH_DATA.md
        reach_latest = get_latest_reach_per_video()
        if not reach_latest.empty:
            reach = reach_latest.rename(columns={
                "impressions": "Impressions",
                "ctr_pct": "CTR",
                "views": "Views (Reach)",
            })
            reach["CTR"] = reach["CTR"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
            reach["Impressions"] = reach["Impressions"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        else:
            reach = parse_reach_data()

    if not retention.empty:
        # Normalize retention column names
        retention = retention.rename(columns={
            "video": "video_id",
            "views": "views_28d",
            "estimatedMinutesWatched": "watch_min_28d",
            "averageViewDuration": "avg_dur_28d",
        })
        # Merge retention into videos (videos has lifetime 'views', retention has '28d' views)
        df = videos.merge(retention, on="video_id", how="left")
    else:
        df = videos

    if not reach.empty:
        df = df.merge(reach, on="video_id", how="left")

    # Convert ISO duration to readable format
    if "duration" in df.columns:
        df["duration"] = df["duration"].apply(parse_iso_duration)

    # Format retention columns
    if "averageViewPercentage" in df.columns:
        df["Retention %"] = df["averageViewPercentage"].round(1)
    if "subscribersGained" in df.columns:
        df["Subs Gained (28d)"] = df["subscribersGained"].fillna(0).astype(int)

    # Watch-time-per-impression — the metric YouTube's algorithm actually rewards.
    # Computed from REACH_HISTORY.csv (latest snapshot per video has both watch_hours
    # and impressions). Result rendered in seconds for readability.
    reach_full = load_reach_history()
    if not reach_full.empty:
        latest = reach_full.sort_values("capture_date").drop_duplicates("video_id", keep="last")
        latest = latest[["video_id", "watch_hours", "impressions"]].rename(columns={
            "watch_hours": "_watch_hours_raw", "impressions": "_impressions_raw"
        })
        df = df.merge(latest, on="video_id", how="left")
        # WT/imp = (watch_hours * 3600) / impressions  → seconds per impression
        df["WT/imp (s)"] = df.apply(
            lambda r: round((float(r["_watch_hours_raw"]) * 3600.0) / float(r["_impressions_raw"]), 1)
            if pd.notna(r.get("_watch_hours_raw")) and pd.notna(r.get("_impressions_raw")) and float(r["_impressions_raw"]) > 0
            else None,
            axis=1,
        )

    display_cols = ["title", "published", "duration", "views"]
    rename_map = {"title": "Title", "published": "Published", "duration": "Duration", "views": "Lifetime Views"}
    for col, label in [
        ("Subs Gained (28d)", "Subs Gained (28d)"),
        ("Retention %", "Retention %"),
        ("Impressions", "Impressions"),
        ("CTR", "CTR"),
        ("WT/imp (s)", "WT/imp (s)"),
    ]:
        if col in df.columns:
            display_cols.append(col)

    df_display = df[display_cols].rename(columns=rename_map)

    st.subheader(f"All {len(df_display)} videos")
    st.caption(
        "Sort by any column. Data: lifetime views + tags from API, 28d retention/subs from Analytics, "
        "Impressions/CTR/WT-per-imp from REACH_HISTORY.csv. "
        "**WT/imp (s)** = watch-time per impression in seconds — the algorithm signal that drives escalation."
    )

    st.dataframe(
        df_display,
        width="stretch",
        height=600,
        hide_index=True,
    )

    # Quick filters
    st.divider()
    st.subheader("Quick insights")

    col1, col2 = st.columns(2)

    with col1:
        if "Retention %" in df_display.columns:
            top_retention = df_display.nlargest(5, "Retention %")[["Title", "Retention %", "Lifetime Views"]]
            st.markdown("**Highest retention (28d)**")
            st.dataframe(top_retention, width="stretch", hide_index=True)

    with col2:
        if "Subs Gained (28d)" in df_display.columns:
            top_subs = df_display.nlargest(5, "Subs Gained (28d)")[["Title", "Subs Gained (28d)", "Lifetime Views"]]
            st.markdown("**Most subs gained (28d)**")
            st.dataframe(top_subs, width="stretch", hide_index=True)

    if "WT/imp (s)" in df_display.columns:
        st.markdown("**Highest watch-time per impression** — the algorithm's escalation signal")
        wt_df = df_display.dropna(subset=["WT/imp (s)"]).nlargest(5, "WT/imp (s)")[
            ["Title", "WT/imp (s)", "CTR", "Retention %", "Lifetime Views"]
        ]
        st.dataframe(wt_df, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Tab: Video Detail
# -----------------------------------------------------------------------------
with tab_detail:
    st.subheader("🔍 Drill down into any video")
    st.caption("Pick a video to see full metadata, metrics, traffic sources, keyword analysis, and auto-recommendations.")

    with st.spinner("Loading videos..."):
        all_vids = load_all_my_videos()
        reach_df = parse_reach_data()
        kw_db = load_keyword_database()

    if all_vids.empty:
        st.info("No videos found.")
    else:
        # Build a clean selector: title (published)
        options = {f"{row['title'][:80]}  ·  {row['published']}": row["video_id"] for _, row in all_vids.iterrows()}
        selected_label = st.selectbox("Choose a video", list(options.keys()))
        selected_id = options[selected_label]

        with st.spinner(f"Loading detail for {selected_id}..."):
            detail = load_video_detail(selected_id)

        if detail is None:
            st.error("Could not load detail.")
        else:
            # Header
            st.markdown(f"### {detail['title']}")
            st.caption(f"Published: {detail['published']} · Duration: {parse_iso_duration(detail['duration'])} · Video ID: `{detail['video_id']}`")

            # Reach row for this video (if exists)
            reach_row = None
            if not reach_df.empty:
                reach_matches = reach_df[reach_df["video_id"] == selected_id]
                if not reach_matches.empty:
                    reach_row = reach_matches.iloc[0]

            # Metrics row
            st.divider()
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Lifetime Views", f"{detail['lifetime_views']:,}")
            m2.metric("Likes", f"{detail['lifetime_likes']:,}")

            analytics = detail["analytics_28d"]
            ret_pct = analytics.get("averageViewPercentage", 0) or 0
            m3.metric("Retention % (28d)", f"{ret_pct:.1f}%")
            subs_g = int(analytics.get("subscribersGained", 0) or 0)
            m4.metric("Subs Gained (28d)", subs_g)

            if reach_row is not None:
                m5.metric("CTR", str(reach_row.get("CTR", "—")))
            else:
                m5.metric("CTR", "—", help="No Reach data captured for this video yet")

            # More metrics
            st.divider()
            st.markdown("**28-day analytics**")

            # Surface analytics-fetch problems so zeros aren't ambiguous.
            analytics_error = detail.get("analytics_error")
            if analytics_error == "no_rows":
                st.warning(
                    "YouTube Analytics API returned no rows for this video in the last 28 days. "
                    "Common causes: video is too new (under ~48h), or the OAuth token's active "
                    "channel doesn't match this video's channel."
                )
            elif analytics_error and analytics_error.startswith("api_error"):
                st.error(f"Analytics fetch failed: `{analytics_error}`")

            acol1, acol2, acol3, acol4 = st.columns(4)
            acol1.metric("Views (28d)", int(analytics.get("views", 0) or 0))
            watch_min_detail = int(analytics.get("estimatedMinutesWatched", 0) or 0)
            acol2.metric("Watch time (28d)", format_minutes_to_hours(watch_min_detail))
            avg_dur_sec_detail = int(analytics.get('averageViewDuration', 0) or 0)
            acol3.metric("Avg view duration", f"{avg_dur_sec_detail / 60:.1f} min")
            if reach_row is not None:
                acol4.metric("Impressions", str(reach_row.get("Impressions", "—")))

            # CTR / Impressions trend (from REACH_HISTORY.csv)
            hist = load_reach_history()
            if not hist.empty:
                vid_hist = hist[hist["video_id"] == selected_id].sort_values("capture_date")
                if len(vid_hist) >= 1:
                    st.divider()
                    st.markdown("**📈 CTR & Impressions over time**")
                    st.caption("From weekly YouTube Studio CSV imports. Shows cumulative-to-date values at each capture.")

                    if len(vid_hist) == 1:
                        r = vid_hist.iloc[0]
                        # Guard against empty/NaN impressions or CTR (from live-API captures
                        # that don't have analytics filled in yet)
                        try:
                            imp_val = r["impressions"]
                            ctr_val = r["ctr_pct"]
                            imp_str = f"{int(float(imp_val)):,}" if pd.notna(imp_val) and str(imp_val).strip() not in ("", "nan") else "—"
                            ctr_str = f"{float(ctr_val):.2f}%" if pd.notna(ctr_val) and str(ctr_val).strip() not in ("", "nan") else "—"
                            st.info(
                                f"Only 1 data point so far ({r['capture_date'].date() if hasattr(r['capture_date'], 'date') else r['capture_date']}): "
                                f"**{imp_str} impressions · {ctr_str} CTR**. "
                                f"Import more weekly exports to see the trend."
                            )
                        except Exception:
                            st.info(f"1 data point captured ({r.get('capture_date', '?')}). Awaiting more captures for trend.")
                    else:
                        c1, c2 = st.columns(2)
                        with c1:
                            fig_ctr = px.line(
                                vid_hist, x="capture_date", y="ctr_pct", markers=True,
                                title="CTR % over time", labels={"ctr_pct": "CTR %", "capture_date": ""},
                            )
                            fig_ctr.add_hline(y=3, line_dash="dash", line_color="orange", annotation_text="3% floor")
                            fig_ctr.add_hline(y=6, line_dash="dash", line_color="green", annotation_text="6% excellent")
                            fig_ctr.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0),
                                                  template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
                            st.plotly_chart(fig_ctr, width="stretch")
                        with c2:
                            fig_impr = px.line(
                                vid_hist, x="capture_date", y="impressions", markers=True,
                                title="Impressions over time", labels={"impressions": "Impressions", "capture_date": ""},
                            )
                            fig_impr.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0),
                                                   template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
                            st.plotly_chart(fig_impr, width="stretch")

            # Traffic sources
            st.divider()
            st.markdown("**Traffic sources (28d)**")
            traffic = detail.get("traffic_sources", [])
            if traffic:
                traffic_df = pd.DataFrame(traffic)
                traffic_df["insightTrafficSourceType"] = traffic_df["insightTrafficSourceType"].map({
                    "YT_SEARCH": "🔍 YouTube Search",
                    "BROWSE": "🏠 Browse feed",
                    "RELATED_VIDEO": "▶️ Suggested (related video)",
                    "SUBSCRIBER": "🔔 Subscriber feed",
                    "NO_LINK_OTHER": "↪️ Direct / other",
                    "EXT_URL": "🌐 External URL",
                    "YT_CHANNEL": "📺 Channel page",
                    "YT_OTHER_PAGE": "📄 Other YouTube page",
                    "PLAYLIST": "📋 Playlist",
                    "END_SCREEN": "🎬 End screen",
                }).fillna(traffic_df["insightTrafficSourceType"])
                # Format watch time in hours, avg duration in minutes for readability
                traffic_df["Watch time"] = traffic_df["estimatedMinutesWatched"].apply(format_minutes_to_hours)
                traffic_df["Avg duration"] = traffic_df["averageViewDuration"].apply(
                    lambda s: f"{int(s) / 60:.1f} min" if s else "—"
                )
                st.dataframe(
                    traffic_df[["insightTrafficSourceType", "views", "Watch time", "Avg duration"]].rename(columns={
                        "insightTrafficSourceType": "Source",
                        "views": "Views",
                    }),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No traffic source data yet (video too new or no views in 28d).")

            # Keyword analysis
            st.divider()
            st.markdown("**🔑 Keyword analysis**")
            st.caption("Matches against your validated KEYWORD_DATA.md — HIGH score keywords are proven high-volume terms.")

            combined_text = f"{detail['title']} {detail['description']} {' '.join(detail.get('tags', []))}"
            kw_matches = analyze_keywords(combined_text, kw_db)

            if kw_matches:
                kw_df = pd.DataFrame(kw_matches)
                display_cols = ["keyword", "verdict", "score"]
                if "volume" in kw_df.columns:
                    display_cols.append("volume")
                if "notes" in kw_df.columns:
                    display_cols.append("notes")
                kw_display = kw_df[display_cols].rename(columns={
                    "keyword": "Keyword",
                    "verdict": "Verdict",
                    "score": "VidIQ Score",
                    "volume": "Volume",
                    "notes": "Notes",
                })
                # Keep numeric columns numeric (NaN-safe) so PyArrow can serialize.
                if "Volume" in kw_display.columns:
                    kw_display["Volume"] = pd.to_numeric(kw_display["Volume"], errors="coerce").astype("Int64")
                if "Notes" in kw_display.columns:
                    kw_display["Notes"] = kw_display["Notes"].fillna("")
                st.dataframe(
                    kw_display,
                    width="stretch",
                    hide_index=True,
                )

                # Suggest HIGH-score keywords NOT in this video
                st.markdown("**💡 HIGH-score keywords you could add:**")
                top_missing = []
                present = {m["keyword"] for m in kw_matches}
                for kw, data in sorted(kw_db.items(), key=lambda x: x[1].get("score", 0), reverse=True):
                    if kw not in present and data.get("label") == "HIGH":
                        top_missing.append((kw, data.get("score", 0)))
                    if len(top_missing) >= 5:
                        break
                if top_missing:
                    for kw, sc in top_missing:
                        st.markdown(f"- `{kw}` (score: {sc})")
                else:
                    st.caption("All HIGH-score keywords from your database are already in this video. ✅")
            else:
                st.warning("⚠️ No keywords from your validated database match this video's title/description/tags. Consider adding some.")

            # Recommendations
            st.divider()
            st.markdown("**💡 Recommendations**")
            recs = generate_recommendations(detail, reach_row, kw_matches)
            for r in recs:
                st.markdown(f"- {r}")

            # Full description + tags (collapsible)
            st.divider()
            with st.expander("📝 Full title, description, and tags"):
                st.markdown(f"**Title:** {detail['title']}")
                st.markdown(f"**Description ({len(detail['description'])} chars):**")
                st.text(detail["description"])
                st.markdown(f"**Tags ({len(detail['tags'])}):**")
                st.write(", ".join(detail["tags"]) if detail["tags"] else "(no tags)")

# -----------------------------------------------------------------------------
# Tab: Competitors
# -----------------------------------------------------------------------------
with tab_competitors:
    st.subheader("Side-by-side comparison")
    with st.spinner("Loading competitor data..."):
        my_info = load_my_channel_info()
        comp_df = load_competitor_stats()

    # Prepend our channel
    my_row = {
        "Channel": f"{my_info['title']} (us)",
        "Subscribers": my_info["subs"],
        "Total Views": my_info["total_views"],
        "Videos": my_info["video_count"],
        "Started": my_info["published"],
    }
    combined = pd.concat([pd.DataFrame([my_row]), comp_df], ignore_index=True)
    combined["Days Alive"] = combined["Started"].apply(
        lambda d: (date.today() - pd.to_datetime(d).date()).days
    )
    combined["Subs / day"] = (combined["Subscribers"] / combined["Days Alive"]).round(1)
    combined["Views / day"] = (combined["Total Views"] / combined["Days Alive"]).round(0).astype(int)

    st.dataframe(combined, width="stretch", hide_index=True)

    st.divider()
    st.subheader("What they've been shipping (latest 5 uploads)")

    for name, cid in COMPETITORS.items():
        st.markdown(f"### {name}")
        with st.spinner(f"Loading latest from {name}..."):
            latest = load_competitor_latest_videos(cid, limit=5)
        st.dataframe(latest, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Tab: Brief Queue (new — dynamic, reads from data/video_briefs/*.json)
# -----------------------------------------------------------------------------
from brief_queue import (
    load_all_briefs, set_brief_status, get_brief_by_id,
    count_by_status, STATUS_VALUES as BRIEF_STATUS_VALUES,
)

with tab_briefs:
    st.subheader("🧠 Brief Queue — auto-generated by pipeline")
    st.caption(
        "Dynamic queue. Every brief written by `pipeline/proposal_to_video.py` "
        "appears here automatically. The old Production Queue tab stays untouched "
        "as a parallel view until this one is fully validated."
    )

    if st.button("🔄 Refresh briefs", key="refresh_briefs"):
        st.cache_data.clear()
        st.rerun()

    briefs = load_all_briefs()
    if not briefs:
        st.info(
            "No briefs yet. Run the pipeline to generate one:\n\n"
            "```\npython3 pipeline/generate_ideas.py\npython3 pipeline/proposal_to_video.py --candidate 1\n```\n\n"
            "Briefs land in `raga-focus-dashboard/data/video_briefs/{slug}.json` and show here."
        )
    else:
        # Compact status strip (single line, only non-zero counts shown bold)
        counts = count_by_status()
        _bits = []
        for status in BRIEF_STATUS_VALUES:
            n = counts.get(status, 0)
            label = status.replace("_", " ").title()
            if n > 0:
                _bits.append(f"**{label}: {n}**")
            else:
                _bits.append(f"<span style='color:#888'>{label}: 0</span>")
        st.markdown("📊 " + "  ·  ".join(_bits), unsafe_allow_html=True)
        st.divider()

        # Split into active vs shipped
        shipped_statuses = {"PUBLISHED", "COMPLETE"}
        active_briefs  = [b for b in briefs if b.get("status", "DRAFT") not in shipped_statuses]
        shipped_briefs = [b for b in briefs if b.get("status", "DRAFT") in shipped_statuses]

        # Sort active by planned_date ascending (next-up at top), missing dates last.
        # Sort shipped by date_shipped descending (most recent first), then planned_date.
        def _sort_key_active(b):
            d = b.get("planned_date") or "9999-12-31"
            return d
        def _sort_key_shipped(b):
            d = b.get("date_shipped") or b.get("planned_date") or "0000-01-01"
            return d
        active_briefs.sort(key=_sort_key_active)
        shipped_briefs.sort(key=_sort_key_shipped, reverse=True)

        def _render_brief_row(b, show_shipped_date=False, is_next=False):
            with st.container():
                c1, c2, c3 = st.columns([4, 2, 2])
                with c1:
                    planned = b.get("planned_date", "")
                    # Slot badge: 🌅 AM (morning, 7am IST) / 🌙 PM (evening, 7pm IST)
                    slot_raw = b.get("planned_slot", "")
                    if slot_raw.startswith("AM"):
                        slot_badge = "<span style='background:#ffa500;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-right:6px;'>🌅 AM</span>"
                    elif slot_raw.startswith("PM"):
                        slot_badge = "<span style='background:#4a90e2;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-right:6px;'>🌙 PM</span>"
                    else:
                        slot_badge = ""
                    next_chip = "▶ NEXT  " if is_next else ""
                    label = f"📅 {planned}  " if planned else ""
                    title_text = b.get('title', '(untitled)')
                    if is_next:
                        st.markdown(
                            f"<div style='border-left:3px solid #ff6b35;padding-left:10px;'>"
                            f"<span style='background:#ff6b35;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600;'>NEXT</span> "
                            f"{slot_badge}"
                            f"<span style='color:#888;font-size:13px;'>{label}</span>"
                            f"<strong style='font-size:15px;'>{title_text}</strong>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"{slot_badge}<span style='color:#888;font-size:13px;'>{label}</span><strong>{title_text}</strong>", unsafe_allow_html=True)
                    if show_shipped_date and b.get("date_shipped"):
                        st.caption(f"Shipped: {b['date_shipped']}  ·  {b.get('id')}")
                    else:
                        st.caption(f"{b.get('id')}")
                with c2:
                    new_status = st.selectbox(
                        "Status",
                        options=BRIEF_STATUS_VALUES,
                        index=BRIEF_STATUS_VALUES.index(b.get("status", "DRAFT"))
                              if b.get("status") in BRIEF_STATUS_VALUES else 0,
                        key=f"brief_status_{b['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != b.get("status"):
                        set_brief_status(b["id"], new_status)
                        st.rerun()
                with c3:
                    if st.button("View brief", key=f"view_{b['id']}"):
                        st.session_state["selected_brief_id"] = b["id"]
                        st.rerun()
                st.divider()

        # Detail view for selected brief — rendered at TOP so "View brief"
        # click produces a visible response without scrolling.
        selected_id = st.session_state.get("selected_brief_id")
        if selected_id:
            brief = get_brief_by_id(selected_id)
            if brief is None:
                st.warning(f"Brief `{selected_id}` not found in store. It may have been deleted, or the gspread cache is stale.")
                if st.button("Clear selection", key="clear_missing_brief"):
                    del st.session_state["selected_brief_id"]
                    st.rerun()
            else:
                st.markdown(f"## 📋 {brief.get('title', '(untitled)')}")
                _meta = f"Slug: `{brief['id']}`  ·  Status: **{brief.get('status', 'DRAFT')}**"
                # Slot badge in detail view
                _slot_raw = brief.get("planned_slot", "")
                if _slot_raw.startswith("AM"):
                    _meta += "  ·  🌅 **AM (Morning · 7am IST)**"
                elif _slot_raw.startswith("PM"):
                    _meta += "  ·  🌙 **PM (Evening · 7pm IST)**"
                if brief.get("planned_date"):
                    _meta += f"  ·  Planned: {brief['planned_date']}"
                if brief.get("date_shipped"):
                    _meta += f"  ·  Shipped: {brief['date_shipped']}"
                st.caption(_meta)

                _bcol1, _bcol2, _bcol3, _bcol4 = st.columns([1, 1, 2, 4])
                with _bcol1:
                    if st.button("← Close", key="close_brief_top"):
                        del st.session_state["selected_brief_id"]
                        st.rerun()
                with _bcol2:
                    _confirm_key = f"confirm_delete_{brief['id']}"
                    if st.session_state.get(_confirm_key):
                        if st.button("🗑️ Confirm delete", key=f"do_delete_{brief['id']}", type="primary"):
                            import storage as _stor
                            _stor.delete_brief(brief["id"])
                            del st.session_state["selected_brief_id"]
                            st.session_state.pop(_confirm_key, None)
                            st.rerun()
                    else:
                        if st.button("🗑️ Delete brief", key=f"ask_delete_{brief['id']}"):
                            st.session_state[_confirm_key] = True
                            st.rerun()
                with _bcol3:
                    from datetime import date as _ddate, datetime as _ddt
                    _cur_planned = brief.get("planned_date") or ""
                    try:
                        _cur_dt = _ddt.strptime(_cur_planned, "%Y-%m-%d").date() if _cur_planned else _ddate.today()
                    except Exception:
                        _cur_dt = _ddate.today()
                    _new_dt = st.date_input(
                        "Planned date",
                        value=_cur_dt,
                        key=f"planned_date_edit_{brief['id']}",
                        label_visibility="collapsed",
                    )
                    _new_str = _new_dt.strftime("%Y-%m-%d")
                    if _new_str != _cur_planned:
                        import storage as _stor
                        brief["planned_date"] = _new_str
                        _stor.write_brief(brief)
                        st.toast(f"Planned date → {_new_str}")
                        st.rerun()

                st.success("📋 **READY-TO-PASTE BLOCKS** — copy each into YouTube Studio in order")

                st.markdown("##### 1️⃣ Title (paste into Title field)")
                title_str = brief.get("title", "")
                st.code(title_str, language="text")
                st.caption(f"{len(title_str)} chars")
                if brief.get("title_variants"):
                    with st.expander("Other A/B/C variants (for Test & Compare)", expanded=False):
                        for k, v in brief["title_variants"].items():
                            st.code(v, language="text")
                            st.caption(f"{k} · {len(v)} chars")

                st.markdown("##### 2️⃣ Description (paste into Description field)")
                desc = brief.get("description", "")
                st.code(desc, language="text")
                st.caption(f"{len(desc)} chars")

                st.markdown("##### 3️⃣ Tags (paste into Tags field, comma-separated)")
                tags_val = brief.get("tags", "")
                tags_str = tags_val if isinstance(tags_val, str) else ", ".join(tags_val)
                st.code(tags_str, language="text")
                st.caption(f"{len(tags_str)}/500 chars · {len(tags_str.split(',')) if tags_str else 0} tags")

                st.markdown("##### 4️⃣ Thumbnail overlay text")
                tvars = brief.get("thumbnail_text_variants") or []
                if tvars:
                    for v in tvars[:3]:
                        if isinstance(v, dict):
                            label    = v.get("label", "")
                            text     = v.get("text", "")
                            strategy = v.get("strategy", "")
                            if label:
                                st.markdown(f"<span style='color:#888;font-size:12px;'>VARIANT {label}</span>", unsafe_allow_html=True)
                            st.code(text, language="text")
                            if strategy:
                                st.caption(strategy)
                        else:
                            st.code(str(v), language="text")
                else:
                    st.code(brief.get("thumbnail_text_main", "—"), language="text")
                if brief.get("thumbnail_prompt"):
                    with st.expander("Image prompt (Ideogram / Midjourney)", expanded=False):
                        st.code(brief["thumbnail_prompt"], language="text")

                if brief.get("suno_prompt"):
                    st.markdown("##### 5️⃣ Suno prompt")
                    st.code(brief["suno_prompt"], language="text")

                # ── Playlist assignment ──────────────────────────────────────
                def _auto_suggest_playlists(_b):
                    _t = ((_b.get("title") or "") + " " + (_b.get("components", {}).get("problem") or "")).lower()
                    _res = []
                    if any(k in _t for k in ["sleep","insomnia","drift off","fall asleep","deep rest","unwind","restless","bedtime"]):
                        _res.append("Sleep Music")
                    if any(k in _t for k in ["meditation","mindfulness","dopamine","inner peace","mindful","stillness"]):
                        _res.append("Meditation")
                    if any(k in _t for k in ["morning","uplifting","joyful","positive vibes","good energy","productive","yoga","motivation"]):
                        _res.append("Morning Energy")
                    if any(k in _t for k in ["anxiety","overthinking","nervous system","cortisol","burnout","stress relief","healing","emotional","comfort","brain fog","mental clarity","worry","overwhelm"]):
                        _res.append("Healing & Anxiety Relief")
                    if any(k in _t for k in ["peaceful","relaxation","breathe","soothing","calm","gentle","quiet"]) and not _res:
                        _res.append("Peaceful Music")
                    return _res or ["Healing & Anxiety Relief"]

                _pl_list = brief.get("playlists") or []
                _pl_suggested = not brief.get("playlists")
                if _pl_suggested:
                    _pl_list = _auto_suggest_playlists(brief)

                st.markdown("##### 6️⃣ Add to Playlist(s) after publishing")
                _pl_colors = {
                    "Sleep Music":              "#1e3a5f",
                    "Meditation":               "#2d5a27",
                    "Morning Energy":           "#7d3c00",
                    "Healing & Anxiety Relief": "#4a235a",
                    "Peaceful Music":           "#1a4a4a",
                }
                _badges = " &nbsp; ".join(
                    f"<span style='background:{_pl_colors.get(_pl,'#444')};color:white;"
                    f"padding:5px 14px;border-radius:14px;font-size:13px;"
                    f"font-weight:600'>🎵 {_pl}</span>"
                    for _pl in _pl_list
                )
                st.markdown(_badges, unsafe_allow_html=True)
                if _pl_suggested:
                    st.caption("💡 Auto-suggested from title keywords — confirm when publishing")

                with st.expander("📊 Strategy details", expanded=False):
                    if brief.get("strategic_bet"):
                        st.markdown(f"**Strategic bet:** {brief['strategic_bet']}")
                    comps = brief.get("components", {})
                    if comps:
                        st.markdown("**Components:** " + " · ".join(
                            f"{k}: {v if not isinstance(v, dict) else v.get('name') or v.get('kw') or v.get('hz') or v.get('wave')}"
                            for k, v in comps.items()
                        ))
                    if brief.get("validated_keywords"):
                        st.markdown("**Validated keywords:** " + ", ".join(brief["validated_keywords"]))

                if brief.get("production_spec"):
                    with st.expander("🛠️ Production spec", expanded=False):
                        st.json(brief["production_spec"])

                st.markdown("---")

        # Active briefs
        st.markdown(f"### 🟢 Active Briefs ({len(active_briefs)})")
        if active_briefs:
            for i, b in enumerate(active_briefs):
                _render_brief_row(b, is_next=(i == 0))
        else:
            st.info("No active briefs — generate ideas to fill the queue.")

        # Shipped briefs (collapsed)
        if shipped_briefs:
            with st.expander(f"✅ Shipped ({len(shipped_briefs)})", expanded=False):
                for b in shipped_briefs:
                    _render_brief_row(b, show_shipped_date=True)

    st.divider()
    st.caption(
        "💡 Briefs are written by `pipeline/proposal_to_video.py`. To add one, run:\n\n"
        "`python3 pipeline/generate_ideas.py && python3 pipeline/proposal_to_video.py -c 1`"
    )


# -----------------------------------------------------------------------------
# Tab: A/B Insights
# -----------------------------------------------------------------------------

DASHBOARD_DIR = Path(__file__).parent
PIPELINE_DIR  = (DASHBOARD_DIR / "pipeline") if (DASHBOARD_DIR / "pipeline").exists() else (DASHBOARD_DIR.parent / "pipeline")
PROPOSALS_DIR = (DASHBOARD_DIR / "videos" / "proposals") if (DASHBOARD_DIR / "videos" / "proposals").exists() else (DASHBOARD_DIR.parent / "videos" / "proposals")
PROJECT_ROOT  = PIPELINE_DIR.parent
AB_RAW_CSV   = DASHBOARD_DIR / "data" / "ab_raw_data.csv"
AB_RULES_JSON = DASHBOARD_DIR / "data" / "playbook" / "ab_pattern_rules.json"

@st.cache_data(ttl=300)
def load_ab_raw():
    if not AB_RAW_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(AB_RAW_CSV)
    return df

@st.cache_data(ttl=300)
def load_ab_rules():
    import json as _j
    if not AB_RULES_JSON.exists():
        return {}
    return _j.loads(AB_RULES_JSON.read_text())

with tab_idea_gen:
    st.subheader("🧪 A/B Test Insights")
    st.caption("Live view of all title & thumbnail experiments. Updated whenever new screenshots are banked.")

    df_ab = load_ab_raw()
    rules = load_ab_rules()

    if df_ab.empty:
        st.warning("No A/B data found. Check that `data/ab_raw_data.csv` exists.")
        st.stop()

    # -------------------------------------------------------------------------
    # Summary metrics
    # -------------------------------------------------------------------------
    total = len(df_ab)
    concluded = df_ab[df_ab["status"] == "CONCLUDED"]
    running   = df_ab[df_ab["status"] == "RUNNING"]
    superseded = df_ab[df_ab["status"] == "SUPERSEDED"]

    n_concluded = len(concluded)
    n_running   = len(running)
    n_super     = len(superseded)

    # Wins/ties among concluded
    a_wins  = concluded["winner"].str.startswith("A").sum()
    b_wins  = concluded["winner"].str.startswith("B").sum()
    ties    = concluded["winner"].str.lower().str.contains("tie").sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total tests", total)
    c2.metric("Concluded", n_concluded)
    c3.metric("Running", n_running)
    c4.metric("A wins", int(a_wins))
    c5.metric("B wins", int(b_wins))
    c6.metric("Ties", int(ties))

    st.divider()

    # -------------------------------------------------------------------------
    # Inner sub-tabs
    # -------------------------------------------------------------------------
    sub_rules, sub_raw, sub_running, sub_next = st.tabs([
        "📋 Lane Rules", "📊 All Tests", "▶️ Running Now", "🔬 Next Tests"
    ])

    # =========================================================================
    # Sub-tab 1: Lane Rules
    # =========================================================================
    with sub_rules:
        st.markdown("### Thumbnail Text by Lane")
        st.caption("What wins on the thumbnail in each content lane — based on concluded tests.")

        lanes = rules.get("lanes", {})

        thumb_rows = []
        for lane_key, lane_data in lanes.items():
            conf = lane_data.get("confidence", "—")
            win_thumb = lane_data.get("winning_thumb_type", "—")
            win_ex    = " · ".join(lane_data.get("winning_thumb_examples", [])[:2])
            avoid_thumb = lane_data.get("avoid_thumb_type", "—")
            avoid_ex    = " · ".join(lane_data.get("avoid_thumb_examples", [])[:2])
            evid      = ", ".join(lane_data.get("evidence", [])[:3])
            conf_emoji = {"HIGH": "🟢", "VERY HIGH": "🟢🟢", "MEDIUM-HIGH": "🔵", "MEDIUM": "🔵", "LOW-MEDIUM": "🟡", "LOW": "🟡", "NONE": "⚪"}.get(conf, "⚪")
            thumb_rows.append({
                "Lane": lane_key.replace("_", " ").title(),
                "✅ Use": f"{win_thumb}" + (f" — {win_ex}" if win_ex else ""),
                "❌ Avoid": f"{avoid_thumb}" + (f" — {avoid_ex}" if avoid_ex else ""),
                "Confidence": f"{conf_emoji} {conf}",
                "Evidence": evid,
            })

        thumb_df = pd.DataFrame(thumb_rows)
        st.dataframe(thumb_df, use_container_width=True, hide_index=True,
                     column_config={
                         "Lane": st.column_config.TextColumn("Lane", width=130),
                         "✅ Use": st.column_config.TextColumn("✅ Format", width=200),
                         "❌ Avoid": st.column_config.TextColumn("❌ Avoid", width=200),
                         "Confidence": st.column_config.TextColumn("Conf", width=120),
                         "Evidence": st.column_config.TextColumn("Evidence", width=130),
                     })

        st.markdown("---")
        st.markdown("### Title Type by Lane")

        title_rows = []
        for lane_key, lane_data in lanes.items():
            conf = lane_data.get("confidence", "—")
            win_title  = lane_data.get("winning_title_type", "—")
            win_ex_t   = " · ".join(lane_data.get("winning_title_examples", [])[:1])
            avoid_title = lane_data.get("avoid_title_type") or "—"
            avoid_ex_t  = " · ".join(lane_data.get("avoid_title_examples", [])[:1])
            evid = ", ".join(lane_data.get("evidence", [])[:3])
            conf_emoji = {"HIGH": "🟢", "VERY HIGH": "🟢🟢", "MEDIUM-HIGH": "🔵", "MEDIUM": "🔵", "LOW-MEDIUM": "🟡", "LOW": "🟡", "NONE": "⚪"}.get(conf, "⚪")
            title_rows.append({
                "Lane": lane_key.replace("_", " ").title(),
                "✅ Use": f"{win_title}",
                "Example": win_ex_t[:70] + ("…" if len(win_ex_t) > 70 else ""),
                "❌ Avoid": f"{avoid_title}",
                "Confidence": f"{conf_emoji} {conf}",
            })

        title_df = pd.DataFrame(title_rows)
        st.dataframe(title_df, use_container_width=True, hide_index=True,
                     column_config={
                         "Lane": st.column_config.TextColumn("Lane", width=130),
                         "✅ Use": st.column_config.TextColumn("✅ Format", width=180),
                         "Example": st.column_config.TextColumn("Example title", width=340),
                         "❌ Avoid": st.column_config.TextColumn("❌ Avoid", width=180),
                         "Confidence": st.column_config.TextColumn("Conf", width=120),
                     })

        st.markdown("---")
        st.markdown("### Universal Rules")
        st.caption("Apply to every lane, every brief. These are the hardest rules — backed by multiple isolated tests.")

        universal = rules.get("universal_rules", [])
        if universal:
            ur_rows = []
            for ur in universal:
                conf = ur.get("confidence", "")
                conf_emoji = {"HIGH": "🟢", "MEDIUM": "🔵", "LOW": "🟡"}.get(conf, "⚪")
                ur_rows.append({
                    "Conf": f"{conf_emoji} {conf}",
                    "Rule": ur.get("rule", ""),
                    "Record": ur.get("record", ""),
                    "Action": ur.get("action", ""),
                    "Evidence": ", ".join(ur.get("evidence", [])[:3]),
                })
            ur_df = pd.DataFrame(ur_rows)
            st.dataframe(
                ur_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Conf":     st.column_config.TextColumn("Conf", width=100),
                    "Rule":     st.column_config.TextColumn("Rule", width=340),
                    "Record":   st.column_config.TextColumn("Record", width=110),
                    "Action":   st.column_config.TextColumn("→ Action", width=340),
                    "Evidence": st.column_config.TextColumn("Evidence", width=160),
                },
            )

        st.markdown("---")
        st.info(
            "**⚠️ Confidence tiers:** 🟢 HIGH = 2+ tests, decisive margins — follow without hesitation. "
            "🔵 MEDIUM = consistent direction but confounded or small margins — default to this. "
            "🟡 LOW = 1 test or marginal gap — treat as directional lean. "
            "⚪ NONE = tie or no tests — format-tolerant, content quality dominates."
        )

    # =========================================================================
    # Sub-tab 2: All Tests (raw data table)
    # =========================================================================
    with sub_raw:
        st.markdown(f"### All {total} Tests — Raw Data")
        st.caption("Every test with both variant titles and thumbnail texts side by side. Filter by lane or test type.")

        # Filters
        fcol1, fcol2, fcol3 = st.columns(3)
        lane_options = ["All"] + sorted(df_ab["lane"].dropna().unique().tolist())
        type_options = ["All"] + sorted(df_ab["test_type"].dropna().unique().tolist())
        status_options = ["All", "CONCLUDED", "RUNNING", "SUPERSEDED"]

        sel_lane   = fcol1.selectbox("Lane", lane_options, key="ab_lane_filter")
        sel_type   = fcol2.selectbox("Test type", type_options, key="ab_type_filter")
        sel_status = fcol3.selectbox("Status", status_options, key="ab_status_filter")

        df_show = df_ab.copy()
        if sel_lane != "All":
            df_show = df_show[df_show["lane"] == sel_lane]
        if sel_type != "All":
            df_show = df_show[df_show["test_type"] == sel_type]
        if sel_status != "All":
            df_show = df_show[df_show["status"] == sel_status]

        # Parse shares as floats for coloring
        def _pct(v):
            try:
                return float(str(v).replace("%","").strip())
            except Exception:
                return None

        df_show = df_show.copy()
        df_show["a_pct"] = df_show["a_share"].apply(_pct)
        df_show["b_pct"] = df_show["b_share"].apply(_pct)

        # Winner badge
        def _badge(row):
            w = str(row.get("winner","")).lower()
            if "tie" in w:
                return "🤝 Tie"
            elif w.startswith("a"):
                return "🏆 A"
            elif w.startswith("b"):
                return "🏆 B"
            elif "running" in str(row.get("status","")).lower():
                return "▶️ Running"
            elif "superseded" in str(row.get("status","")).lower():
                return "🔄 Superseded"
            return "—"

        df_show["Result"] = df_show.apply(_badge, axis=1)

        # Margin
        def _margin(row):
            a, b = row["a_pct"], row["b_pct"]
            if a is not None and b is not None:
                return round(abs(a - b), 1)
            return None

        df_show["Margin pp"] = df_show.apply(_margin, axis=1)

        # Add inferred_outcome column if present in CSV
        has_outcome = "inferred_outcome" in df_show.columns

        display_cols = [
            "test_num", "date", "lane", "test_type",
            "variant_a_title", "variant_a_thumb",
            "variant_b_title", "variant_b_thumb",
            "a_share", "b_share", "Margin pp", "Result",
        ]
        if has_outcome:
            display_cols.append("inferred_outcome")
        display_cols.append("status")

        rename_map = {
            "test_num": "#", "date": "Date", "lane": "Lane", "test_type": "Type",
            "variant_a_title": "A Title", "variant_a_thumb": "A Thumb",
            "variant_b_title": "B Title", "variant_b_thumb": "B Thumb",
            "a_share": "A %", "b_share": "B %", "status": "Status",
            "inferred_outcome": "Inferred Outcome",
        }
        df_display_ab = df_show[display_cols].rename(columns=rename_map)

        col_config = {
            "#": st.column_config.NumberColumn("#", width=40),
            "Date": st.column_config.TextColumn("Date", width=85),
            "Lane": st.column_config.TextColumn("Lane", width=130),
            "Type": st.column_config.TextColumn("Type", width=95),
            "A Title": st.column_config.TextColumn("A Title", width=240),
            "A Thumb": st.column_config.TextColumn("A Thumb", width=120),
            "B Title": st.column_config.TextColumn("B Title", width=240),
            "B Thumb": st.column_config.TextColumn("B Thumb", width=120),
            "A %": st.column_config.TextColumn("A %", width=55),
            "B %": st.column_config.TextColumn("B %", width=55),
            "Margin pp": st.column_config.NumberColumn("Gap pp", width=60, format="%.1f"),
            "Result": st.column_config.TextColumn("Result", width=85),
            "Status": st.column_config.TextColumn("Status", width=85),
        }
        if has_outcome:
            col_config["Inferred Outcome"] = st.column_config.TextColumn("Inferred Outcome", width=380)

        st.dataframe(
            df_display_ab,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config=col_config,
        )

        st.markdown(f"**{len(df_show)} tests shown** (of {total} total)")

        st.divider()
        # --- Win-rate breakdown by thumbnail format
        st.markdown("### Thumbnail Format Win Rates (concluded tests)")

        concluded_df = df_ab[df_ab["status"] == "CONCLUDED"].copy()
        if not concluded_df.empty:
            # Classify thumb format from winner side
            def _thumb_format(text):
                if not isinstance(text, str):
                    return "Unknown"
                t = text.strip().upper()
                if t.endswith("?"):
                    return "Q-hook"
                elif any(kw in t for kw in ["REST", "OKAY", "WORRY", "ALLOW", "GUILT"]):
                    return "Permission"
                elif any(kw in t for kw in ["MUSIC", "SLEEP", "RELAX MUSIC"]):
                    return "Intent-descriptor"
                else:
                    return "Outcome-imperative"

            def _get_winner_thumb(row):
                w = str(row.get("winner","")).lower()
                if w.startswith("a") and not "tie" in w:
                    return row.get("variant_a_thumb","")
                elif w.startswith("b") and not "tie" in w:
                    return row.get("variant_b_thumb","")
                return None

            concluded_df["winner_thumb"] = concluded_df.apply(_get_winner_thumb, axis=1)
            concluded_df["thumb_fmt"] = concluded_df["winner_thumb"].apply(_thumb_format)

            # Count wins by format
            fmt_counts = concluded_df[concluded_df["winner_thumb"].notna()]["thumb_fmt"].value_counts().reset_index()
            fmt_counts.columns = ["Thumbnail Format", "Wins"]

            fig_fmt = px.bar(
                fmt_counts,
                x="Wins", y="Thumbnail Format", orientation="h",
                color="Thumbnail Format",
                title="Wins by thumbnail format",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_fmt.update_layout(
                height=280, margin=dict(l=0, r=0, t=40, b=0),
                template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                showlegend=False,
            )
            st.plotly_chart(fig_fmt, width="stretch")

            # Margin distribution
            concluded_df["a_pct"] = concluded_df["a_share"].apply(_pct)
            concluded_df["b_pct"] = concluded_df["b_share"].apply(_pct)
            concluded_df["margin"] = concluded_df.apply(_margin, axis=1)
            decisive = concluded_df[concluded_df["margin"].notna()]

            if not decisive.empty:
                fig_margin = px.histogram(
                    decisive,
                    x="margin",
                    nbins=10,
                    title="Margin distribution (pp) — concluded tests",
                    labels={"margin": "Margin (percentage points)", "count": "Tests"},
                    color_discrete_sequence=["#636EFA"],
                )
                fig_margin.add_vline(x=5, line_dash="dash", line_color="orange",
                                     annotation_text="5pp decisive")
                fig_margin.update_layout(
                    height=260, margin=dict(l=0, r=0, t=40, b=0),
                    template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                )
                st.plotly_chart(fig_margin, width="stretch")

    # =========================================================================
    # Sub-tab 3: Running Now
    # =========================================================================
    with sub_running:
        st.markdown("### Currently Running Tests")
        st.caption("Scores are directional only — wait for 'Test finished' before banking any rule.")

        running_df = df_ab[df_ab["status"] == "RUNNING"].copy()

        if running_df.empty:
            st.success("No tests currently running.")
        else:
            running_df["a_pct"] = running_df["a_share"].apply(_pct)
            running_df["b_pct"] = running_df["b_share"].apply(_pct)

            for _, row in running_df.iterrows():
                a_pct = row["a_pct"]
                b_pct = row["b_pct"]
                margin = abs(a_pct - b_pct) if (a_pct is not None and b_pct is not None) else 0
                leader = "A" if (a_pct or 0) > (b_pct or 0) else "B"
                decisiveness = "🟢 Decisive (>10pp)" if margin > 10 else ("🟡 Leaning (5-10pp)" if margin > 5 else "⚪ Too close to call")

                with st.expander(f"#{int(row['test_num'])} · {row['lane']} · {row['test_type']} — Leading: **{leader}** ({decisiveness})"):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown(f"**Variant A** — `{row['a_share']}`")
                        st.markdown(f"**Title:** {row['variant_a_title']}")
                        st.markdown(f"**Thumb:** `{row['variant_a_thumb']}`")
                    with rc2:
                        st.markdown(f"**Variant B** — `{row['b_share']}`")
                        st.markdown(f"**Title:** {row['variant_b_title']}")
                        st.markdown(f"**Thumb:** `{row['variant_b_thumb']}`")

                    if a_pct is not None and b_pct is not None:
                        bar_df = pd.DataFrame({
                            "Variant": ["A", "B"],
                            "Share %": [a_pct, b_pct],
                            "Color": ["#636EFA" if leader == "A" else "#EF553B",
                                      "#EF553B" if leader == "A" else "#636EFA"],
                        })
                        fig_bar = px.bar(
                            bar_df, x="Variant", y="Share %",
                            color="Variant",
                            color_discrete_sequence=["#636EFA", "#EF553B"],
                            range_y=[0, 100],
                            height=200,
                        )
                        fig_bar.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3)
                        fig_bar.update_layout(
                            margin=dict(l=0, r=0, t=10, b=0),
                            template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                            showlegend=False,
                        )
                        st.plotly_chart(fig_bar, width="stretch")

        st.divider()
        st.info(
            "**Paste new screenshots** to the conversation whenever tests conclude. "
            "Claude will bank the result and this page updates automatically after you clear cache."
        )

    # =========================================================================
    # Sub-tab 4: Next Tests
    # =========================================================================
    with sub_next:
        st.markdown("### Hypotheses Queue — Next Tests to Run")
        st.caption("Gaps in the data worth structuring a deliberate test around. Set these up on the next relevant ship.")

        hypotheses = [
            {
                "priority": "🔴 1",
                "hypothesis": "Intent-descriptor thumb beats Q-hook in sleep lane cleanly",
                "lane": "Sleep",
                "design": "Thumb-only: **DEEP SLEEP NOW** vs **CAN'T FALL ASLEEP?**",
                "settles": "Whether sleep lane is intent-match or just anti-Q-hook",
                "status": "Needs a thumb-only sleep test",
            },
            {
                "priority": "🔴 2",
                "hypothesis": "Permission thumb beats both Q-hook and outcome-imperative — strongly supported by Test 29 (REST WITHOUT WORRY, 17.2pp win)",
                "lane": "Burnout/Rest",
                "design": "3-way thumb-only: **IT'S OKAY TO REST** vs **BURNED OUT AND TIRED?** vs **RELEASE THE TENSION**",
                "settles": "Isolates permission as a distinct category (Test 29 was confounded)",
                "status": "High priority — best current hypothesis",
            },
            {
                "priority": "🟡 3",
                "hypothesis": "Mental-state Q-hook beats physical-exhaustion Q-hook",
                "lane": "Any rest lane",
                "design": "Thumb-only: **MIND WON'T SLOW DOWN?** vs **BODY FEELS HEAVY?**",
                "settles": "Explains why some Q-hooks win and others lose",
                "status": "Explains pattern across 9 tests",
            },
            {
                "priority": "🟡 4",
                "hypothesis": "Plain-language state beats clinical jargon in burnout title",
                "lane": "Burnout",
                "design": "Title-only: **Exhausted Mind | Slow Veena | 1.5 Hours** vs **Nervous System Reset | Slow Veena | 1.5 Hours**",
                "settles": "Settles title lead style for burnout lane",
                "status": "Test 26 confounded — need isolation",
            },
            {
                "priority": "🟢 5",
                "hypothesis": "Strong title rescues generic outcome thumb",
                "lane": "Any lane",
                "design": "Thumb-only with proven strong title: **STRESSED?** vs **RELAX DEEPLY**",
                "settles": "Confirms whether generic thumb finding is real or title-confounded",
                "status": "Only Test 14 is a clean isolation so far",
            },
            {
                "priority": "🟢 6",
                "hypothesis": "Morning anti-Q-hook rule holds with thumb-only isolation",
                "lane": "Morning",
                "design": "Thumb-only morning test: **MORNING BOOST** vs **FEEL UNMOTIVATED?**",
                "settles": "Test 28 (tie, confounded) introduced doubt — need clean isolation",
                "status": "5 prior morning tests all showed outcome wins",
            },
        ]

        for h in hypotheses:
            with st.expander(f"{h['priority']} · **{h['lane']}** — {h['hypothesis'][:80]}{'…' if len(h['hypothesis'])>80 else ''}"):
                st.markdown(f"**Hypothesis:** {h['hypothesis']}")
                st.markdown(f"**Test design:** {h['design']}")
                st.markdown(f"**What it settles:** {h['settles']}")
                st.info(f"**Status:** {h['status']}")

        st.divider()
        st.markdown("### Quick Pre-Brief Checklist")
        st.markdown("""
**Title:**
- [ ] Lead slot is SEO-led or lifestyle/mood? (Not Q-hook, not duration, not practice/utility)
- [ ] 3 slots only? (Not 2, not 4+)
- [ ] Lead keyword is highest VidIQ score available for this lane?
- [ ] No Hz, wave type, or raga jargon stuffed in?

**Thumbnail:**
- [ ] Thumb type is right for the lane? (Check Lane Rules tab)
- [ ] If using Q-hook: is it a *mental/cognitive* state? (Not physical exhaustion or time-of-day)
- [ ] Avoiding generic soft outcomes? (RELAX DEEPLY, THINK LESS, LET YOURSELF REST — weak)
- [ ] Mobile readable? (2–3 words, 14–18 chars)
- [ ] Thumb energy matches music energy?
        """)


# -----------------------------------------------------------------------------
# Tab: Idea Queue — workshop space between Idea Gen and Brief Queue
# -----------------------------------------------------------------------------

# =============================================================================
# TAB: Title Builder (v4)
# =============================================================================
with tab_title_builder:
    import json as _tb_json
    import csv as _tb_csv
    import re as _tb_re
    from collections import defaultdict as _tb_dd
    from urllib.parse import quote_plus as _tb_qp
    from datetime import date as _tb_date

    # ─────────────────────────────────────────────────────────
    # CSS — minimal density tweaks only
    # ─────────────────────────────────────────────────────────
    st.markdown("""<style>
    .tb-scope .stButton > button {
        font-size: 13px !important;
        padding: 2px 8px !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
        font-weight: 400 !important;
    }
    .tb-scope div[data-testid="stHorizontalBlock"] {
        gap: 0.15rem !important;
        align-items: center !important;
        margin-bottom: 0 !important;
    }
    .tb-scope div[data-testid="stVerticalBlock"] > div {
        gap: 0.15rem !important;
    }
    .tb-scope div[data-testid="column"] { padding: 0 2px !important; }
    .tb-scope p { margin: 0 !important; line-height: 1.3 !important; }
    /* Compact number input */
    .tb-scope .stNumberInput { margin: 0 !important; }
    .tb-scope .stNumberInput > div { min-height: 28px !important; }
    .tb-scope .stNumberInput input {
        padding: 2px 4px !important;
        font-size: 12px !important;
        height: 28px !important;
        text-align: center !important;
    }
    /* Compact spinners but keep them visible for usability */
    .tb-scope .stNumberInput button {
        padding: 0 4px !important;
        min-width: 18px !important;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown('<div class="tb-scope">', unsafe_allow_html=True)
    st.markdown("## Title Builder")

    # ─────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────
    _tb_bank = {}
    _tb_bank_path = DASHBOARD_DIR / "data" / "keyword_bank.csv"
    if _tb_bank_path.exists():
        with open(_tb_bank_path) as _f:
            for _r in _tb_csv.DictReader(_f):
                _tb_bank[_r["phrase"].strip().lower()] = _r

    _tb_inv = set()
    _tb_inv_path = DASHBOARD_DIR / "data" / "invalidated_keywords.csv"
    if _tb_inv_path.exists():
        with open(_tb_inv_path) as _f:
            for _r in _tb_csv.DictReader(_f):
                _tb_inv.add(_r["phrase"].strip().lower())

    _tb_clusters = []
    _tb_clusters_path = DASHBOARD_DIR / "data" / "keyword_clusters.json"
    if _tb_clusters_path.exists():
        try:
            _tb_clusters = _tb_json.loads(_tb_clusters_path.read_text()).get("clusters", [])
        except Exception:
            _tb_clusters = []

    import sys as _tb_sys
    _tb_sys.path.insert(0, str(PIPELINE_DIR))

    @st.cache_data(ttl=300, show_spinner=False)
    def _tb_cached_catalog():
        try:
            from signals import load_own_catalog as _tb_load_catalog
            return _tb_load_catalog()
        except Exception:
            return []

    @st.cache_data(ttl=600, show_spinner=False)
    def _tb_cached_competitors(days=7):
        try:
            return fetch_competitor_pulse_live(days=days)
        except Exception:
            return {}

    _tb_catalog = _tb_cached_catalog()

    # Hidden bucket — persist to disk
    _tb_hidden_path = DASHBOARD_DIR / "data" / "title_builder_hidden.txt"
    if "tb_hidden" not in st.session_state:
        if _tb_hidden_path.exists():
            st.session_state["tb_hidden"] = set(_tb_hidden_path.read_text().splitlines())
        else:
            st.session_state["tb_hidden"] = set()

    def _save_hidden():
        try:
            _tb_hidden_path.write_text("\n".join(sorted(st.session_state["tb_hidden"])))
        except Exception:
            pass

    # Inline scores — persist to JSON to survive reruns/redeploys
    _tb_scores_path = DASHBOARD_DIR / "data" / "title_builder_scores.json"
    if "tb_inline_scores" not in st.session_state:
        if _tb_scores_path.exists():
            try:
                st.session_state["tb_inline_scores"] = _tb_json.loads(_tb_scores_path.read_text())
            except Exception:
                st.session_state["tb_inline_scores"] = {}
        else:
            st.session_state["tb_inline_scores"] = {}
    else:
        # On every render, merge any disk-persisted scores in case file was updated by another session
        if _tb_scores_path.exists():
            try:
                _disk = _tb_json.loads(_tb_scores_path.read_text())
                for _k, _v in _disk.items():
                    if _k not in st.session_state["tb_inline_scores"]:
                        st.session_state["tb_inline_scores"][_k] = _v
            except Exception:
                pass

    def _save_scores():
        try:
            _tb_scores_path.write_text(_tb_json.dumps(st.session_state["tb_inline_scores"], indent=2))
        except Exception:
            pass

    # Session state init
    for _k, _v in [
        ("tb_picked_a", []),
        ("tb_picked_b", []),
        ("tb_active_variant", "A"),
        ("tb_b_mode", "Question"),
        ("tb_active_cluster", "All"),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────
    # Pull pipeline's smart token logic — same stopwords, same theme detection
    try:
        from signals import _meaningful_tokens as _pipe_tokens
    except Exception:
        _pipe_tokens = None

    _COOLDOWN_DAYS = 5  # match pipeline default

    def _tb_cooldown(phrase):
        """Return (status, days_left, why_title).
        Status: 'invalidated' | 'cooldown' | 'unscored' | 'available'.
        why_title: the past video that triggered cooldown, or None.
        """
        p = phrase.strip().lower()
        if p in _tb_inv:
            return "invalidated", 0, None
        today = _tb_date.today()

        # Get meaningful tokens from candidate (filters stopwords, instruments, ragas, Hz)
        cand_tokens = set(_pipe_tokens(p)) if _pipe_tokens else set()

        for v in _tb_catalog:
            pub = v.get("publish_date")
            if not pub:
                continue
            days_ago = (today - pub).days
            if days_ago > _COOLDOWN_DAYS:
                continue
            title_l = v.get("title","").lower()
            video_title = v.get("title","")

            # Strategy 1: exact phrase match (only if meaningful — skip tiny/stopword phrases)
            # Avoids "music" / "1 hour" / "for" matching every title
            if len(p) >= 5 and " " in p and p in title_l:
                # Multi-word substring is strong signal
                return "cooldown", _COOLDOWN_DAYS - days_ago, video_title

            # Strategy 2: theme-token overlap (catches "settle your mind" when "calm your mind" was used)
            if cand_tokens and _pipe_tokens:
                title_tokens = set(_pipe_tokens(title_l))
                if cand_tokens & title_tokens:
                    return "cooldown", _COOLDOWN_DAYS - days_ago, video_title

            # Strategy 3: exact short-keyword match (instruments, ragas, Hz) — only when phrase is exact word in title
            # Use word boundary check: phrase appears as whole word
            if " " not in p and len(p) >= 4:
                import re as _re_cd
                if _re_cd.search(rf"\b{_re_cd.escape(p)}\b", title_l):
                    return "cooldown", _COOLDOWN_DAYS - days_ago, video_title

        row = _tb_bank.get(p)
        if not row or not row.get("vidiq_score","").strip().isdigit():
            return "unscored", 0, None
        return "available", 0, None

    def _tb_score(phrase):
        row = _tb_bank.get(phrase.strip().lower())
        if not row:
            return None
        s = row.get("vidiq_score","").strip()
        return int(s) if s.isdigit() else None

    def _tb_effective_score(phrase):
        """Score from bank or inline session score."""
        s = _tb_score(phrase)
        if s is None:
            s = st.session_state["tb_inline_scores"].get(phrase.strip().lower())
        return s

    def _tb_select_keyword(phrase):
        """Add to active variant's pool."""
        active = st.session_state["tb_active_variant"]
        target = "tb_picked_a" if active == "A" else "tb_picked_b"
        if phrase not in st.session_state[target]:
            st.session_state[target].append(phrase)

    def _tb_unselect_keyword(phrase, variant):
        target = "tb_picked_a" if variant == "A" else "tb_picked_b"
        if phrase in st.session_state[target]:
            st.session_state[target].remove(phrase)

    def _tb_in_a(phrase): return phrase in st.session_state["tb_picked_a"]
    def _tb_in_b(phrase): return phrase in st.session_state["tb_picked_b"]

    def _tb_chip_html(phrase):
        """Render a keyword chip status badge as HTML for inline display."""
        status, days_left, _ = _tb_cooldown(phrase)
        score = _tb_effective_score(phrase)
        if status == "invalidated":
            return '<span style="color:#f87171;font-size:0.7rem">❌</span>'
        if status == "cooldown":
            return f'<span style="color:#facc15;font-size:0.7rem">🕐{days_left}d</span>'
        if score is None:
            return '<span style="color:#8a8a92;font-size:0.7rem">⚠️</span>'
        color = "#4ade80" if score >= 70 else "#facc15" if score >= 60 else "#f87171"
        return f'<span style="color:{color};font-size:0.78rem;font-weight:600">{score}</span>'

    # Competitor word extraction
    _STOP = {"music","1","hour","min","mins","minutes","hr","hrs","for","and","the","a","an","with",
             "of","to","in","on","at","is","are","be","you","your","my","this","that","new",
             "raga","ragas","video","track","mix","ft","feat","official","hd","4k","2025","2026"}

    def _tb_extract_words(uploads, top_n=22):
        """Return list of (phrase, total_views, count) sorted by views."""
        agg = _tb_dd(lambda: {"views": 0, "count": 0})
        for u in uploads:
            title = u.get("title", "")
            views = u.get("views", 0) or 0
            parts = _tb_re.split(r'[\|\-—–•·:()]', title)
            for part in parts:
                words = [w.lower().strip('.,!?:()[]"\'') for w in part.split()]
                words = [w for w in words if w and w not in _STOP and len(w) > 2 and not w.isdigit()]
                # Single words
                for w in words:
                    agg[w]["views"] += views
                    agg[w]["count"] += 1
                # 2-word phrases
                for i in range(len(words)-1):
                    p = f"{words[i]} {words[i+1]}"
                    agg[p]["views"] += views
                    agg[p]["count"] += 1
        # Filter: keep things that appear in 2+ titles OR have high single-title views
        out = [(k, v["views"], v["count"]) for k, v in agg.items()]
        out.sort(key=lambda x: -x[1])
        return out[:top_n]

    # ═════════════════════════════════════════════════════════
    # SECTION 1 — Live A/B preview at top
    # ═════════════════════════════════════════════════════════
    def _smart_title(s):
        """Title-case but DON'T capitalize after apostrophes ('can't' not 'Can'T')."""
        if not s:
            return s
        words = s.split(" ")
        out = []
        for w in words:
            if not w:
                out.append(w); continue
            # Capitalize first char only, preserve rest as-is (handles can't, won't, you'll, etc.)
            out.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
        return " ".join(out)

    def _resolve_instrument():
        """Return chosen instrument: custom text overrides dropdown."""
        custom = (st.session_state.get("tb_instrument_custom","") or "").strip()
        if custom:
            return custom
        sel = st.session_state.get("tb_instrument", "(none)")
        return sel if sel != "(none)" else ""

    def _dedupe_overlapping(kws):
        """Drop keywords that share theme tokens with a higher-scored keyword.
        Keeps the first (highest-scored) occurrence per theme cluster.
        """
        if not _pipe_tokens:
            return kws
        kept = []
        seen_tokens = set()
        for kw in kws:
            tokens = set(_pipe_tokens(kw.lower()))
            if not tokens:
                # Keyword has no meaningful tokens (all stopwords) — keep it
                kept.append(kw)
                continue
            if tokens & seen_tokens:
                # Overlap with already-kept keyword — drop this one
                continue
            kept.append(kw)
            seen_tokens |= tokens
        return kept

    def _build_variant_a():
        picked = st.session_state["tb_picked_a"]
        if not picked: return ""
        sorted_kws = sorted(picked, key=lambda p: -(_tb_effective_score(p) or 0))
        # Dedupe overlapping themes (e.g., "stress relief music" + "release stress" → keep one)
        sorted_kws = _dedupe_overlapping(sorted_kws)
        inst = _resolve_instrument()
        dur = st.session_state.get("tb_duration", "(none)")
        dur = dur if dur != "(none)" else ""
        # Drop redundant instrument if it's already in the lead keyword (e.g., "veena music" + "Veena")
        if inst and sorted_kws and inst.lower() in sorted_kws[0].lower():
            inst = ""
        parts = [_smart_title(k) for k in sorted_kws]
        if inst: parts.append(inst.title())
        if dur:  parts.append(dur)
        out = " | ".join(parts)
        # Char cap: 70 chars. If over, drop lowest-priority keyword (last picked)
        while len(out) > 70 and len(parts) > 2:
            # Drop the last keyword (least important since they're score-sorted)
            kw_count = len(sorted_kws)
            if kw_count > 1:
                sorted_kws = sorted_kws[:-1]
                parts = [_smart_title(k) for k in sorted_kws]
                if inst: parts.append(inst.title())
                if dur:  parts.append(dur)
                out = " | ".join(parts)
            else:
                break
        return out

    def _build_variant_b():
        picked = st.session_state["tb_picked_b"]
        if not picked: return ""
        sorted_kws = sorted(picked, key=lambda p: -(_tb_effective_score(p) or 0))
        # Apply same dedupe as Variant A
        sorted_kws = _dedupe_overlapping(sorted_kws)
        lead = sorted_kws[0]
        rest = sorted_kws[1:]
        inst = _resolve_instrument()
        raga = st.session_state.get("tb_raga", "(none)")
        raga = raga if raga != "(none)" else ""
        dur = st.session_state.get("tb_duration", "(none)")
        dur = dur if dur != "(none)" else ""
        mode = st.session_state.get("tb_b_mode", "Question")

        ll = lead.lower().strip()

        # ── Grammatical classification of the lead keyword ──
        ACTION_VERBS = ("calm", "release", "drift", "fall", "ease", "settle",
                        "soothe", "find", "stop", "let go", "wind down",
                        "still", "quiet", "boost", "lift", "feel", "get")
        PROBLEM_NOUNS = ("stress", "anxiety", "insomnia", "burnout", "overthinking",
                         "exhaustion", "tension", "fatigue", "depression", "loneliness",
                         "homesick", "nostalgia", "grief", "panic", "overwhelm",
                         "sleep", "bed", "night", "fog", "rest")
        POSITIVE_THEMES = ("feel good", "positive", "uplifting", "happy", "joyful",
                           "bright", "cheerful", "energy", "mood")

        # ── Cluster-based theme detection (more reliable than substring) ──
        _b_cluster_id = None
        try:
            _b_cluster_id = _find_keyword_cluster(lead, _tb_clusters)
        except Exception:
            pass
        # Cluster-based theme overrides for templates
        # Each cluster maps to a "canonical theme word" used in templates
        _CLUSTER_THEME = {
            "calm": "calm", "stress": "stress", "sleep": "sleep",
            "anxiety": "anxiety", "healing": "healing", "nostalgia": "nostalgia",
            "focus": "focus", "grounding": "grounding", "uplifting": "energy",
        }
        _theme = _CLUSTER_THEME.get(_b_cluster_id) if _b_cluster_id else None

        # Strip common suffixes for cleaner template insertion
        clean = lead.replace(" music","").replace(" relief","").replace(" instrumental","").replace(" therapy","").strip()

        is_question_phrase = ll.startswith("can't") or ll.startswith("cant") or ll.startswith("how to") or ll.endswith("?")
        is_action = any(ll.startswith(v + " ") or ll == v for v in ACTION_VERBS)
        contains_problem = next((p for p in PROBLEM_NOUNS if p in ll), None)
        contains_positive = next((p for p in POSITIVE_THEMES if p in ll), None)

        # ── Question mode ──
        # Theme-based question hooks (fired first when keyword's cluster is known)
        _theme_question = {
            "sleep":     "Can't Sleep?",
            "stress":    "Stressed Out?",
            "anxiety":   "Anxious?",
            "calm":      "Need to Calm Down?",
            "focus":     "Can't Focus?",
            "healing":   "Hurting?",
            "nostalgia": "Missing Someone?",
            "grounding": "Ungrounded?",
            "energy":    "Drained?",
        }
        if "Question" in mode:
            if is_question_phrase:
                head = _smart_title(lead).rstrip("?") + "?"
            elif _theme and _theme in _theme_question:
                head = _theme_question[_theme]
            elif is_action:
                head = f"Can't {_smart_title(lead)}?"
            elif contains_problem:
                # Map problem noun → natural question
                _problem_q = {
                    "sleep": "Can't Sleep?", "bed": "Can't Sleep?", "night": "Up at Night?",
                    "stress": "Stressed Out?", "anxiety": "Anxious?",
                    "insomnia": "Insomnia?", "burnout": "Burned Out?",
                    "overthinking": "Overthinking?", "exhaustion": "Drained?",
                    "fog": "Brain Fog?", "rest": "Can't Rest?",
                    "tension": "Tense?", "fatigue": "Drained?",
                    "homesick": "Missing Home?", "nostalgia": "Missing Someone?",
                    "grief": "Heavy Heart?", "panic": "Panic Rising?",
                    "overwhelm": "Overwhelmed?",
                }
                head = _problem_q.get(contains_problem, f"Struggling with {contains_problem.title()}?")
            elif contains_positive:
                if "energy" in ll or "boost" in ll: head = "Drained?"
                elif "mood" in ll: head = "Mood Down?"
                elif "happy" in ll or "joyful" in ll: head = "Need Joy?"
                elif "morning" in ll: head = "Tired Morning?"
                else: head = "Need a Lift?"
            else:
                if "music" in ll or "relief" in ll or "instrumental" in ll:
                    head = f"Looking for {_smart_title(clean)}?"
                else:
                    head = f"{_smart_title(lead)}?"

        # ── Outcome mode ── (map theme → action verb + theme noun)
        elif "Outcome" in mode:
            # Cluster-theme outcomes (fired first when keyword's cluster known)
            _theme_outcome = {
                "sleep":     "Drift Into Sleep",
                "stress":    "Release Stress",
                "anxiety":   "Soothe Anxiety",
                "calm":      "Find Calm",
                "focus":     "Sharpen Focus",
                "healing":   "Begin Healing",
                "nostalgia": "Embrace Nostalgia",
                "grounding": "Ground Yourself",
                "energy":    "Get Your Energy Back",
            }
            outcome_map = {
                "stress": "Release Stress", "anxiety": "Soothe Anxiety",
                "insomnia": "Beat Insomnia", "burnout": "Heal Burnout",
                "overthinking": "Quiet Overthinking", "tension": "Release Tension",
                "exhaustion": "Restore Energy", "nostalgia": "Embrace Nostalgia",
                "homesick": "Find Comfort", "panic": "Calm Panic",
                "overwhelm": "Settle Overwhelm", "grief": "Heal Grief",
                "loneliness": "Hold Yourself", "fatigue": "Restore Energy",
                "feel good": "Feel Good Now", "positive": "Lift Your Mood",
                "uplifting": "Lift Your Mood", "happy": "Find Joy",
                "joyful": "Find Joy", "energy": "Get Your Energy Back",
                "mood": "Boost Your Mood", "bright": "Brighten Your Day",
                "cheerful": "Find Joy",
                "sleep": "Drift Into Sleep", "bed": "Drift Off", "bedtime": "Drift Off",
                "night": "Settle Into Night", "rest": "Find Rest",
                "calm": "Find Calm", "focus": "Sharpen Focus",
                "concentration": "Lock In", "brain fog": "Clear the Fog",
                "healing": "Begin Healing", "comfort": "Find Comfort",
                "morning": "Start Bright", "wake": "Wake Up Bright",
            }
            if _theme and _theme in _theme_outcome:
                head = _theme_outcome[_theme]
            else:
                outcome_phrase = next((v for k, v in outcome_map.items() if k in ll), None)
                if outcome_phrase:
                    head = outcome_phrase
                elif is_action:
                    head = _smart_title(lead)
                else:
                    # Generic "Find X" / "Discover X" fallback so it at least differs from Theme mode
                    head = f"Find {_smart_title(clean)}" if clean else _smart_title(lead)

        # ── Theme mode ── just the keyword cleanly (no decoration)
        elif "theme" in mode.lower():
            head = _smart_title(lead)

        # ── Competitor mode ── borrow winning patterns
        elif "Competitor" in mode:
            # Pick "Ancient" vs "Bright" vs neutral prefix based on theme
            # "Ancient" fits problem/calm themes — stress, anxiety, focus, sleep, healing, etc.
            _is_calm_theme = _theme in ("calm","sleep","healing","nostalgia","grounding","stress","anxiety","focus") or contains_problem
            _is_bright_theme = _theme == "energy" or contains_positive
            _prefix = "Ancient" if _is_calm_theme else ("Bright" if _is_bright_theme else "Timeless")
            _theme_word = (contains_problem or _theme or clean.lower())

            if inst and (contains_problem or _theme):
                head = f"{_prefix} {inst.title()} for {_theme_word.title()}"
            elif inst:
                head = f"{_prefix} {inst.title()} · {_smart_title(lead)}"
            elif contains_problem or _theme:
                head = f"{_prefix} Music for {_theme_word.title()}"
            else:
                # Truly unknown — at least add prefix so it differs from Theme mode
                head = f"{_prefix} {_smart_title(lead)}"

        # ── Phrase mode ── natural prose ("X with Veena", "X through Sarangi")
        elif "phrase" in mode.lower():
            if inst:
                if _is_bright_theme := (_theme == "energy" or contains_positive):
                    connector = "with"
                elif _theme in ("healing","nostalgia","grounding") or any(k in ll for k in ("healing","grief","nostalgia","comfort")):
                    connector = "through"
                else:
                    connector = "with"
                head = f"{_smart_title(lead)} {connector} {inst.title()}"
            else:
                # No instrument — make it differ from Theme mode by adding a connector phrase
                if _theme in ("healing","nostalgia"):
                    head = f"{_smart_title(lead)} for the Heart"
                elif _theme in ("sleep","calm","grounding"):
                    head = f"{_smart_title(lead)} for Quiet Mind"
                elif _theme == "energy":
                    head = f"{_smart_title(lead)} for a Bright Day"
                else:
                    head = f"{_smart_title(lead)} for Deep Listening"
        else:
            head = _smart_title(lead)

        # Track whether the head already contains the instrument (Competitor/Phrase modes weave it in)
        head_has_inst = bool(inst) and inst.lower() in head.lower()

        def _assemble(_head, _rest_kws):
            _parts = [_head]
            for _r in _rest_kws:
                _parts.append(_smart_title(_r))
            # Append instrument unless already in head OR in lead keyword
            if inst and not head_has_inst and inst.lower() not in lead.lower():
                _parts.append(inst.title())
            if raga: _parts.append(raga.title())
            if dur:  _parts.append(dur)
            return " | ".join(_parts)

        out = _assemble(head, rest)
        # Char cap: 70 chars (your A/B test rule). Drop secondary keywords if over.
        while len(out) > 70 and len(rest) > 0:
            rest = rest[:-1]
            out = _assemble(head, rest)
        return out

    _va_default = _build_variant_a()
    _vb_default = _build_variant_b()

    with st.container(border=True):
        _pa, _pb = st.columns(2, gap="medium")
        with _pa:
            st.markdown('**Variant A** · safe')
            _ea_key = "tb_va_input"
            if _ea_key not in st.session_state or st.session_state.get("_tb_last_a") != _va_default:
                st.session_state[_ea_key] = _va_default
                st.session_state["_tb_last_a"] = _va_default
            _ea = st.text_input("A", key=_ea_key, label_visibility="collapsed",
                                placeholder="Pick keywords for A →")
            _la = len(_ea)
            _color = "#4ade80" if _la <= 70 else "#facc15"
            st.markdown(
                f'<div style="font-size:11px;color:#9ca3af;margin-top:2px">'
                f'<span style="color:{_color}">{_la} chars</span> · auto-built from selected keywords</div>',
                unsafe_allow_html=True
            )

        with _pb:
            st.markdown('**Variant B** · experiment')
            _eb_key = "tb_vb_input"
            if _eb_key not in st.session_state or st.session_state.get("_tb_last_b") != _vb_default:
                st.session_state[_eb_key] = _vb_default
                st.session_state["_tb_last_b"] = _vb_default
            _eb = st.text_input("B", key=_eb_key, label_visibility="collapsed",
                                placeholder="Pick keywords for B →")
            _lb = len(_eb)
            _color = "#4ade80" if _lb <= 70 else "#facc15"
            _mode_label = st.session_state["tb_b_mode"].split()[-1] if " " in st.session_state["tb_b_mode"] else st.session_state["tb_b_mode"]
            st.markdown(
                f'<div style="font-size:11px;color:#9ca3af;margin-top:2px">'
                f'<span style="color:{_color}">{_lb} chars</span> · {_mode_label} mode</div>',
                unsafe_allow_html=True
            )

            # B mode pills — plain labels, no emoji
            _modes = ["Question", "Outcome", "Theme", "Competitor", "Phrase"]
            _row1 = st.columns(3)
            _row2 = st.columns(3)
            for _mc, _mode in zip(_row1 + _row2[:2], _modes):
                with _mc:
                    _is_active = _mode == st.session_state["tb_b_mode"]
                    if st.button(_mode, key=f"tb_bm_{_mode}",
                                 type="primary" if _is_active else "secondary",
                                 use_container_width=True):
                        st.session_state["tb_b_mode"] = _mode
                        st.rerun()

    # ═════════════════════════════════════════════════════════
    # Thumbnail text suggestions — directly below A/B preview
    # Theme-aware: looks up keyword's cluster first, then substring fallback
    # ═════════════════════════════════════════════════════════
    # Map cluster id → PROBLEM_THUMBNAIL_TEXT bucket key
    _CLUSTER_TO_BUCKET = {
        "calm": "calm",
        "stress": "stress",
        "sleep": "sleep",
        "anxiety": "anxiety",
        "healing": "healing",
        "nostalgia": "nostalgia",
        "focus": "focus",
        "grounding": "grounding",
        "uplifting": "feel good",  # uplifting cluster maps to feel-good bucket
    }

    def _find_keyword_cluster(keyword, clusters):
        """Return cluster_id if keyword exists in a cluster, else None."""
        kw_l = keyword.strip().lower()
        for cl in clusters:
            for k in cl.get("keywords", []):
                if k.strip().lower() == kw_l:
                    return cl.get("id")
        return None

    st.markdown("### 🎨 Thumbnail text suggestions")

    try:
        from thumbnail_text import build_thumbnail_text_variants as _bt_variants_top, _bucket_for as _bt_bucket_for
        from config import PROBLEM_THUMBNAIL_TEXT as _PTT
    except Exception as _imp_err:
        st.error(f"❌ Thumbnail module import failed: {_imp_err}")
        import traceback as _tb_err
        st.code(_tb_err.format_exc())
        _bt_variants_top = None
        _bt_bucket_for = None
        _PTT = {}

    if _bt_variants_top is not None:
        def _build_variants_theme_aware(lead):
            """Try cluster-based bucket first, fall back to substring match."""
            cluster_id = _find_keyword_cluster(lead, _tb_clusters)
            if cluster_id and _CLUSTER_TO_BUCKET.get(cluster_id) in _PTT:
                bucket_key = _CLUSTER_TO_BUCKET[cluster_id]
                bank = _PTT[bucket_key]
                return [
                    {"label": "A_question", "strategy": "Question form — cold-feed CTR",
                     "text": bank["question"][0], "alts": bank["question"][1:]},
                    {"label": "B_outcome",  "strategy": "Outcome / imperative — warm cohort",
                     "text": bank["outcome"][0],  "alts": bank["outcome"][1:]},
                    {"label": "C_identity", "strategy": "Identity / state label — low-friction scan",
                     "text": bank["identity"][0], "alts": bank["identity"][1:]},
                ], f"cluster: {cluster_id}"
            # Fallback: existing substring match
            return _bt_variants_top(lead), f"substring: {_bt_bucket_for(lead)}"

        def _render_thumb_below(variant_label, picked_list, color):
            if not picked_list:
                st.caption(f"_Pick keywords for {variant_label} →_")
                return
            sorted_kws = sorted(picked_list, key=lambda p: -(_tb_effective_score(p) or 0))
            lead = sorted_kws[0]
            try:
                variants_top, source = _build_variants_theme_aware(lead)
            except Exception as _be_top:
                st.caption(f"_Could not build thumbnail suggestions: {_be_top}_")
                return
            st.markdown(
                f'<div style="font-size:11px;color:{color};margin:2px 0 4px;font-weight:600">'
                f'{variant_label} · theme: <code style="background:#1a1d24;padding:1px 5px;border-radius:3px">{lead}</code> '
                f'<span style="color:#6b7280;font-weight:400">({source})</span></div>',
                unsafe_allow_html=True
            )
            for v in variants_top:
                _strategy = v.get("strategy", v.get("label", "")).split("—")[0].strip()
                _text = v.get("text", "")
                _alts = v.get("alts", [])
                _alts_str = " · ".join(_alts) if _alts else ""
                st.markdown(
                    f'<div style="background:#1a1d24;border:1px solid #2a2e36;border-radius:3px;'
                    f'padding:5px 9px;margin-bottom:3px">'
                    f'<div style="font-size:9px;color:#9ca3af">{_strategy}</div>'
                    f'<div style="font-size:15px;color:#e5e7eb;font-weight:600">{_text}</div>'
                    + (f'<div style="font-size:9px;color:#6b7280">alt: {_alts_str}</div>' if _alts_str else '')
                    + '</div>',
                    unsafe_allow_html=True
                )

        try:
            with st.container(border=True):
                _t1, _t2 = st.columns(2, gap="medium")
                with _t1:
                    _render_thumb_below("Variant A · safe", st.session_state.get("tb_picked_a", []), "#93c5fd")
                with _t2:
                    _render_thumb_below("Variant B · experiment", st.session_state.get("tb_picked_b", []), "#d4a574")
        except Exception as _render_err:
            st.error(f"❌ Thumbnail render failed: {_render_err}")
            import traceback as _tb_render
            st.code(_tb_render.format_exc())

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════
    # SECTION 2 — Three columns: competitors / keywords / build
    # ═════════════════════════════════════════════════════════
    _col_left, _col_mid, _col_right = st.columns([1.3, 2.6, 1.6], gap="medium")

    # ──────────────────────────────────────────────
    # LEFT: Competitor word cloud
    # ──────────────────────────────────────────────
    with _col_left:
        st.markdown("**Competitors** · last 7d")
        st.caption("Trending phrases ranked by total views.")

        try:
            _comp_data = _tb_cached_competitors(days=7)
            _all_uploads = []
            for _cn, _ups in _comp_data.items():
                for _u in _ups:
                    if "error" not in _u:
                        _all_uploads.append({**_u, "channel": _cn})
            _trends = _tb_extract_words(_all_uploads, top_n=22)

            if _trends:
                # Render as inline chip cloud, sized by views
                _max_v = _trends[0][1] if _trends else 1
                _min_v = _trends[-1][1] if _trends else 1
                _bank_set = set(_tb_bank.keys())

                _cloud_html = '<div style="line-height:1.9">'
                for _phrase, _views, _count in _trends:
                    _ratio = (_views - _min_v) / max(_max_v - _min_v, 1)
                    _size = 11 + _ratio * 4  # 11px to 15px
                    _is_banked = _phrase in _bank_set
                    _color = "#4ade80" if _is_banked else "#e5e7eb"
                    _border = "rgba(74,222,128,0.25)" if _is_banked else "#2a2e36"
                    _cloud_html += (
                        f'<span style="display:inline-block;background:#1a1d24;border:1px solid {_border};'
                        f'border-radius:3px;padding:2px 7px;margin:2px;font-size:{_size}px;color:{_color}">'
                        f'{_phrase}<span style="font-size:9px;color:#6b7280;margin-left:4px">'
                        f'{_count}·{_views//1000}K</span></span>'
                    )
                _cloud_html += '</div>'
                st.markdown(_cloud_html, unsafe_allow_html=True)

                # Add a trending word to active variant
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                _trend_names = [t[0] for t in _trends]
                _picked_trend = st.selectbox(
                    "Add a trending word",
                    options=["(pick to add to selected variant)"] + _trend_names,
                    key="tb_trend_pick",
                    label_visibility="collapsed",
                )
                if _picked_trend and _picked_trend != "(pick to add to selected variant)":
                    if st.button(f"Add '{_picked_trend}' to {st.session_state['tb_active_variant']}",
                                 key="tb_add_trend", use_container_width=True):
                        _tb_select_keyword(_picked_trend)
                        st.session_state["tb_trend_pick"] = "(pick to add to selected variant)"
                        st.rerun()

                # Recent titles — always visible, compact cards
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                st.markdown("**Recent titles**")
                _sorted_uploads = sorted(_all_uploads, key=lambda x: -x.get("views",0))
                for _u in _sorted_uploads[:5]:
                    st.markdown(
                        f'<div style="background:#1a1d24;border:1px solid #2a2e36;border-radius:4px;'
                        f'padding:6px 8px;margin-bottom:4px">'
                        f'<div style="font-size:10px;color:#9ca3af;margin-bottom:2px">'
                        f'{_u["channel"]} · {_u.get("views",0):,} · {_u.get("days_ago","?")}d</div>'
                        f'<div style="font-size:12px;color:#e5e7eb;line-height:1.35">{_u.get("title","")}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                if len(_sorted_uploads) > 5:
                    st.caption(f"+ {len(_sorted_uploads) - 5} more")
            else:
                st.info("No competitor data available.")
        except Exception as _ce:
            st.warning(f"Competitor fetch failed: {_ce}")

    # ──────────────────────────────────────────────
    # MIDDLE: Keywords — dense single-line rows
    # ──────────────────────────────────────────────
    with _col_mid:
        st.markdown("**Keywords**")

        # Free-text add
        _ft1, _ft2, _ft3 = st.columns([4, 1, 1])
        with _ft1:
            _free_kw = st.text_input("k", placeholder="Add any keyword + score…",
                                      key="tb_free_kw", label_visibility="collapsed")
        with _ft2:
            _free_sc = st.number_input("s", 0, 100, 0, key="tb_free_sc", label_visibility="collapsed")
        with _ft3:
            if st.button("➕ Add", key="tb_free_add", use_container_width=True):
                _kc = _free_kw.strip().lower()
                if _kc:
                    if _free_sc > 0:
                        st.session_state["tb_inline_scores"][_kc] = _free_sc
                        _save_scores()
                        try:
                            from keyword_bank import append_keyword as _bk
                            _bk(_kc, slot="problem", vidiq_score=_free_sc, source="title-builder-freetext")
                        except Exception:
                            pass
                    _tb_select_keyword(_kc)
                    st.rerun()

        # Cluster filter — use cluster IDs as ground truth, labels for display
        _cluster_options = [("__all__", "All")]
        for _cl in _tb_clusters:
            _short = _cl["name"].split("/")[0].strip()
            _cluster_options.append((_cl["id"], f"{_cl.get('emoji','')} {_short}".strip()))
        _cluster_options.append(("__hidden__", "🗑 Hidden"))

        _labels = [lbl for _, lbl in _cluster_options]
        _id_by_label = {lbl: cid for cid, lbl in _cluster_options}

        _chosen_label = st.radio(
            "cluster",
            options=_labels,
            key="tb_active_cluster_lbl",
            horizontal=True,
            label_visibility="collapsed",
        )
        _cluster_id = _id_by_label.get(_chosen_label, "__all__")
        _cluster_choice = _cluster_id  # used downstream for unique keys

        # Build keyword list — dedupe; filter by cluster id
        _seen = set()
        _kw_raw = []
        if _cluster_id == "__all__":
            for _cl in _tb_clusters:
                for _kw in _cl["keywords"]:
                    _kl = _kw.strip().lower()
                    if _kl in _seen or _kl in st.session_state["tb_hidden"]:
                        continue
                    _seen.add(_kl)
                    _kw_raw.append((_kw, _cl["name"]))
        elif _cluster_id == "__hidden__":
            for _kw in sorted(st.session_state["tb_hidden"]):
                _kw_raw.append((_kw, "Hidden"))
        else:
            _match_cluster = next((c for c in _tb_clusters if c["id"] == _cluster_id), None)
            if _match_cluster:
                for _kw in _match_cluster["keywords"]:
                    _kl = _kw.strip().lower()
                    if _kl in _seen or _kl in st.session_state["tb_hidden"]:
                        continue
                    _seen.add(_kl)
                    _kw_raw.append((_kw, _match_cluster["name"]))

        # Sort: ready (scored, available) first → unscored → cooldown → invalidated
        # Within ready, highest score first
        def _sort_priority(item):
            kw, _ = item
            kl = kw.strip().lower()
            stat, _dl, _ = _tb_cooldown(kl)
            sc = _tb_effective_score(kl)
            if stat == "available" and sc is not None:
                return (0, -sc)
            if stat == "unscored":
                return (1, kw)
            if stat == "cooldown":
                return (2, kw)
            return (3, kw)
        _kw_list = sorted(_kw_raw, key=_sort_priority)

        _unscored = [(kw, cn) for kw, cn in _kw_list if _tb_effective_score(kw.strip().lower()) is None
                     and _tb_cooldown(kw.strip().lower())[0] != "invalidated"]
        _scored_avail = [(kw, cn) for kw, cn in _kw_list
                         if _tb_effective_score(kw.strip().lower()) is not None
                         and _tb_cooldown(kw.strip().lower())[0] == "available"]

        # Selection hint
        _active = st.session_state["tb_active_variant"]
        _active_label = "Variant A" if _active == "A" else "Variant B"
        st.caption(f"Click any keyword to add it to **{_active_label}**. Switch variants in the right panel.")

        st.caption(
            f"{len(_kw_list)} total · :green[{len(_scored_avail)} ready] · :orange[{len(_unscored)} unscored]"
        )

        # ─── KEYWORD ROWS — inline score for unscored, single line for scored ───
        for _idx, (_kw, _cn) in enumerate(_kw_list):
            _kl = _kw.strip().lower()
            _stat, _dl, _why = _tb_cooldown(_kl)
            _sc = _tb_effective_score(_kl)
            _in_a = _tb_in_a(_kl)
            _in_b = _tb_in_b(_kl)
            _disabled = _stat in ("invalidated", "cooldown")
            _key_safe = f"{_idx}_{_kl.replace(' ','_').replace(chr(39),'').replace('/','')}"
            _is_unscored = (_sc is None and _stat == "unscored")

            if _stat == "invalidated":   _badge = "❌"
            elif _stat == "cooldown":    _badge = f"🕐{_dl}d"
            elif _sc is None:            _badge = "⚠️"
            elif _sc >= 70:              _badge = f"🟢{_sc}"
            elif _sc >= 60:              _badge = f"🟡{_sc}"
            else:                        _badge = f"🔴{_sc}"

            _ab = ""
            if _in_a and _in_b: _ab = " · AB"
            elif _in_a: _ab = " · A"
            elif _in_b: _ab = " · B"

            _label = f"{_kw}  {_badge}{_ab}"
            _btn_type = "primary" if (_in_a or _in_b) else "secondary"
            # Tooltip: show why on cooldown (which past video triggered it)
            _help_text = (
                f"⏸ On cooldown because of: {_why}" if _stat == "cooldown" and _why else
                "❌ Invalidated keyword (audience-fit failure or low score)" if _stat == "invalidated" else
                None
            )

            if _is_unscored:
                # Balanced: keyword btn wide, score input readable, controls compact
                _c1, _c2, _c3, _c4, _c5 = st.columns([6, 1.3, 0.7, 0.6, 0.5])
                with _c1:
                    if st.button(_label, key=f"tb_kw_{_cluster_choice}_{_key_safe}",
                                 type=_btn_type, use_container_width=True, help=_help_text):
                        active = st.session_state["tb_active_variant"]
                        if active == "A":
                            if _in_a: _tb_unselect_keyword(_kl, "A")
                            else:     _tb_select_keyword(_kl)
                        else:
                            if _in_b: _tb_unselect_keyword(_kl, "B")
                            else:     _tb_select_keyword(_kl)
                        st.rerun()
                with _c2:
                    _new_sc = st.number_input(
                        "s", 0, 100, 0,
                        key=f"tb_inscore_{_cluster_choice}_{_key_safe}",
                        label_visibility="collapsed",
                    )
                with _c3:
                    st.markdown(
                        f'<a href="https://www.youtube.com/results?search_query={_tb_qp(_kl)}" '
                        f'target="_blank" style="font-size:11px;color:#93c5fd;text-decoration:none;'
                        f'display:inline-block;padding:6px 0;line-height:1">▶ YT</a>',
                        unsafe_allow_html=True
                    )
                with _c4:
                    if _new_sc > 0:
                        if st.button("💾", key=f"tb_save_{_cluster_choice}_{_key_safe}",
                                     help="Save score", use_container_width=True):
                            try:
                                from keyword_bank import append_keyword as _bks
                                _slot = "problem"
                                for _c in _tb_clusters:
                                    if _c["name"] == _cn:
                                        _slot = _c.get("slot","problem"); break
                                _bks(_kl, slot=_slot, vidiq_score=_new_sc, source="title-builder")
                                st.session_state["tb_inline_scores"][_kl] = _new_sc
                                _save_scores()
                                st.success(f"✓ Saved {_kl} = {_new_sc}")
                                st.rerun()
                            except Exception as _e:
                                st.error(f"Save: {_e}")
                with _c5:
                    if st.button("✕", key=f"tb_hd_{_key_safe}", help="Hide",
                                 use_container_width=True):
                        st.session_state["tb_hidden"].add(_kl)
                        _save_hidden()
                        _tb_unselect_keyword(_kl, "A")
                        _tb_unselect_keyword(_kl, "B")
                        st.rerun()
            else:
                # Scored / cooldown / invalidated — simple row [name 7] [✕ 1]
                _r1, _r2 = st.columns([7, 1])
                with _r1:
                    if st.button(_label, key=f"tb_kw_{_cluster_choice}_{_key_safe}",
                                 type=_btn_type, use_container_width=True, disabled=_disabled, help=_help_text):
                        active = st.session_state["tb_active_variant"]
                        if active == "A":
                            if _in_a: _tb_unselect_keyword(_kl, "A")
                            else:     _tb_select_keyword(_kl)
                        else:
                            if _in_b: _tb_unselect_keyword(_kl, "B")
                            else:     _tb_select_keyword(_kl)
                        st.rerun()
                with _r2:
                    if _cluster_choice == "🗑 Hidden":
                        if st.button("↺", key=f"tb_unh_{_key_safe}", help="Restore",
                                     use_container_width=True):
                            st.session_state["tb_hidden"].discard(_kl)
                            _save_hidden()
                            st.rerun()
                    else:
                        if st.button("✕", key=f"tb_hd_{_key_safe}", help="Hide",
                                     use_container_width=True):
                            st.session_state["tb_hidden"].add(_kl)
                            _save_hidden()
                            _tb_unselect_keyword(_kl, "A")
                            _tb_unselect_keyword(_kl, "B")
                            st.rerun()

        # ─────────────────────────────────────────────────────────
        # ✨ SPARK PHRASES — curated Q-hooks / state words / outcomes
        # Visual click-to-add chips for creative title brainstorming.
        # Not VidIQ-scored — these are plain-English viewer vocabulary.
        # Filtered by the active cluster (or All shows everything).
        # ─────────────────────────────────────────────────────────
        _spark_path = DASHBOARD_DIR / "data" / "spark_phrases.json"
        _spark_data = {}
        if _spark_path.exists():
            try:
                _spark_data = _tb_json.loads(_spark_path.read_text()).get("clusters", {})
            except Exception:
                _spark_data = {}

        if _spark_data:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            st.markdown(
                "<div style='font-size:13px;font-weight:600;color:#e5e7eb'>"
                "✨ Spark phrases <span style='font-size:10px;color:#9ca3af;font-weight:400'>"
                "· click to add to active variant (no score needed)</span></div>",
                unsafe_allow_html=True
            )

            # Pick which clusters to show
            if _cluster_id == "__all__":
                _spark_clusters = list(_spark_data.keys())
            elif _cluster_id == "__hidden__":
                _spark_clusters = []
            else:
                _spark_clusters = [_cluster_id] if _cluster_id in _spark_data else []

            _SPARK_COLORS = {
                "question": ("#facc15", "rgba(250,204,21,0.12)", "Q"),
                "state":    ("#93c5fd", "rgba(147,197,253,0.10)", "state"),
                "outcome":  ("#4ade80", "rgba(74,222,128,0.10)", "out"),
            }

            for _scid in _spark_clusters:
                _sc_block = _spark_data.get(_scid, {})
                if not _sc_block:
                    continue
                # Cluster header (only show if multiple clusters visible)
                if len(_spark_clusters) > 1:
                    _cl_meta = next((c for c in _tb_clusters if c["id"] == _scid), None)
                    _cl_emoji = _cl_meta.get("emoji","") if _cl_meta else ""
                    _cl_name = _cl_meta.get("name", _scid).split("/")[0].strip() if _cl_meta else _scid
                    st.markdown(
                        f"<div style='font-size:10px;color:#9ca3af;margin:6px 0 3px;"
                        f"text-transform:uppercase;letter-spacing:0.5px'>"
                        f"{_cl_emoji} {_cl_name}</div>",
                        unsafe_allow_html=True
                    )

                # Render rows per kind (question / state / outcome)
                for _kind in ("question", "state", "outcome"):
                    _phrases = _sc_block.get(_kind, [])
                    if not _phrases:
                        continue
                    _txt, _bg, _lbl = _SPARK_COLORS[_kind]
                    # Render as clickable chips using a wide row of small buttons
                    # Use 3 columns per row to keep them compact
                    _cols_per_row = 3
                    for _i in range(0, len(_phrases), _cols_per_row):
                        _row_phrases = _phrases[_i:_i+_cols_per_row]
                        _cols = st.columns(_cols_per_row)
                        for _ci, _phr in enumerate(_row_phrases):
                            with _cols[_ci]:
                                _pl = _phr.strip().lower()
                                _in_a_sp = _tb_in_a(_pl)
                                _in_b_sp = _tb_in_b(_pl)
                                _suffix = ""
                                if _in_a_sp and _in_b_sp: _suffix = " ·AB"
                                elif _in_a_sp: _suffix = " ·A"
                                elif _in_b_sp: _suffix = " ·B"
                                _label_sp = f"{_phr}{_suffix}"
                                _btn_type_sp = "primary" if (_in_a_sp or _in_b_sp) else "secondary"
                                _key_sp = f"tb_sp_{_scid}_{_kind}_{_i}_{_ci}"
                                if st.button(
                                    _label_sp,
                                    key=_key_sp,
                                    type=_btn_type_sp,
                                    use_container_width=True,
                                    help=f"{_lbl} · click to add to Variant {st.session_state['tb_active_variant']}"
                                ):
                                    active_sp = st.session_state["tb_active_variant"]
                                    if active_sp == "A":
                                        if _in_a_sp: _tb_unselect_keyword(_pl, "A")
                                        else:        _tb_select_keyword(_pl)
                                    else:
                                        if _in_b_sp: _tb_unselect_keyword(_pl, "B")
                                        else:        _tb_select_keyword(_pl)
                                    # Stash a placeholder score so cooldown/score lookups don't choke
                                    # (spark phrases aren't VidIQ-validated; we treat them as "creative" picks)
                                    if _pl not in st.session_state["tb_inline_scores"]:
                                        st.session_state["tb_inline_scores"][_pl] = 50  # neutral default
                                        _save_scores()
                                    st.rerun()
                    # Legend strip
                    st.markdown(
                        f"<div style='font-size:9px;color:{_txt};margin:-2px 0 4px;"
                        f"text-transform:uppercase;letter-spacing:0.5px'>↑ {_kind}</div>",
                        unsafe_allow_html=True
                    )

    # ──────────────────────────────────────────────
    # RIGHT: Build panel — A/B toggle, config, selected
    # ──────────────────────────────────────────────
    with _col_right:
        # A/B toggle — controls which variant new clicks go to
        _ta, _tb = st.columns(2, gap="small")
        _active = st.session_state["tb_active_variant"]
        _a_count = len(st.session_state["tb_picked_a"])
        _b_count = len(st.session_state["tb_picked_b"])
        with _ta:
            if st.button(f"A · safe ({_a_count})",
                         key="tb_pick_a",
                         type="primary" if _active == "A" else "secondary",
                         use_container_width=True):
                st.session_state["tb_active_variant"] = "A"
                st.rerun()
        with _tb:
            if st.button(f"B · experiment ({_b_count})",
                         key="tb_pick_b",
                         type="primary" if _active == "B" else "secondary",
                         use_container_width=True):
                st.session_state["tb_active_variant"] = "B"
                st.rerun()

        st.caption(f"Keyword clicks add to Variant {_active}")
        st.markdown("**Configuration**")
        _instruments = sorted(
            [p for p,r in _tb_bank.items()
             if r.get("slot") == "instrument" and r.get("vidiq_score","").strip().isdigit()],
            key=lambda p: -int(_tb_bank[p]["vidiq_score"])
        )
        _ragas = sorted(
            [p for p,r in _tb_bank.items()
             if r.get("slot") == "raga" and r.get("vidiq_score","").strip().isdigit()],
            key=lambda p: -int(_tb_bank[p]["vidiq_score"])
        )
        st.selectbox("Instrument", ["(none)"] + _instruments, key="tb_instrument")
        st.text_input("Or custom instrument",
                      key="tb_instrument_custom",
                      placeholder="overrides dropdown if filled")
        st.selectbox("Raga", ["(none)"] + _ragas, key="tb_raga")
        st.selectbox("Duration",
                     ["(none)", "1 Hour", "1:15", "1:30", "45 Min", "30 Min"],
                     key="tb_duration")

        def _tb_picked_chip(_p, _sc, _bg_rgb, _text_color):
            """Render picked-variant chip — same look as picker, badge changes with status."""
            _stat, _dl, _why = _tb_cooldown(_p)
            if _stat == "cooldown":
                _tip = (_why or "").replace('"', "'")
                _badge = f' · 🕐{_dl}d'
                _title_attr = f' title="On cooldown — recently used in: {_tip}"'
            elif _stat == "invalidated":
                _badge = ' · ❌'
                _title_attr = ' title="Invalidated keyword"'
            elif _sc:
                _badge = f' · {_sc}'
                _title_attr = ''
            else:
                _badge = ''
                _title_attr = ''
            return (
                f'<div{_title_attr} style="background:rgba({_bg_rgb},0.1);color:{_text_color};padding:3px 8px;'
                f'border-radius:3px;font-size:12px;display:inline-block;'
                f'border:1px solid rgba({_bg_rgb},0.3)">'
                f'{_p}{_badge}</div>'
            )

        # Selected lists
        st.markdown(f"**Variant A** · {_a_count} keywords")
        if st.session_state["tb_picked_a"]:
            _a_warn = [_p for _p in st.session_state["tb_picked_a"]
                       if _tb_cooldown(_p)[0] in ("cooldown", "invalidated")]
            if _a_warn:
                st.warning(f"⚠️ {len(_a_warn)} keyword(s) in Variant A on cooldown/invalidated — see chips")
            for _p in st.session_state["tb_picked_a"]:
                _sc = _tb_effective_score(_p)
                _cs1, _cs2 = st.columns([5, 1])
                with _cs1:
                    st.markdown(_tb_picked_chip(_p, _sc, "147,197,253", "#93c5fd"),
                                unsafe_allow_html=True)
                with _cs2:
                    if st.button("×", key=f"tb_rmA_{_p.replace(' ','_')}", help="Remove from A"):
                        st.session_state["tb_picked_a"].remove(_p)
                        st.rerun()
        else:
            st.caption("Pick keywords for A →")

        st.markdown(f"**Variant B** · {_b_count} keywords")
        if st.session_state["tb_picked_b"]:
            _b_warn = [_p for _p in st.session_state["tb_picked_b"]
                       if _tb_cooldown(_p)[0] in ("cooldown", "invalidated")]
            if _b_warn:
                st.warning(f"⚠️ {len(_b_warn)} keyword(s) in Variant B on cooldown/invalidated — see chips")
            for _p in st.session_state["tb_picked_b"]:
                _sc = _tb_effective_score(_p)
                _cs1, _cs2 = st.columns([5, 1])
                with _cs1:
                    st.markdown(_tb_picked_chip(_p, _sc, "212,165,116", "#d4a574"),
                                unsafe_allow_html=True)
                with _cs2:
                    if st.button("×", key=f"tb_rmB_{_p.replace(' ','_')}", help="Remove from B"):
                        st.session_state["tb_picked_b"].remove(_p)
                        st.rerun()
        else:
            st.caption("Pick keywords for B →")

        # Clear all
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Clear all selections", key="tb_clear_all", use_container_width=True):
            st.session_state["tb_picked_a"] = []
            st.session_state["tb_picked_b"] = []
            for k in ["tb_va_input","tb_vb_input","_tb_last_a","_tb_last_b"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

        # ── Export scores so they can be merged back to the canonical bank ──
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Track previously-exported phrases so they don't keep showing up
        _tb_exported_path = DASHBOARD_DIR / "data" / "title_builder_exported.txt"
        _exported_set = set()
        if _tb_exported_path.exists():
            try:
                _exported_set = set(_tb_exported_path.read_text().splitlines())
            except Exception:
                _exported_set = set()

        _all_scores = dict(st.session_state.get("tb_inline_scores", {}))
        # Also include scores already in keyword_bank.csv that came from title-builder source
        for _kw, _row in _tb_bank.items():
            if "title-builder" in _row.get("source","") and _row.get("vidiq_score","").strip().isdigit():
                _all_scores.setdefault(_kw, int(_row["vidiq_score"]))

        # Filter out already-exported
        _all_scores = {k: v for k, v in _all_scores.items() if k not in _exported_set}

        # Always show the expander (even when empty) so user can find it
        _exp_label = (f"📤 Export {len(_all_scores)} scored keywords"
                      if _all_scores else
                      "📤 Export scored keywords (none right now)")
        with st.expander(_exp_label, expanded=bool(_all_scores)):
            if not _all_scores:
                st.caption(
                    f"No new scores to export. Score any unscored keyword via the inline 💾 button "
                    f"and it'll show here. ({len(_exported_set)} already marked exported in "
                    f"data/title_builder_exported.txt)"
                )
            else:
                st.caption("Copy this and paste in chat — I'll merge into keyword_bank.csv and commit to git. Then click 'Clear' to remove from this list.")
                _export_text = "\n".join(f"{k}: {v}" for k, v in sorted(_all_scores.items(), key=lambda x: -x[1]))
                st.code(_export_text, language="text")
                _csv_text = "phrase,vidiq_score,source\n" + "\n".join(
                    f'"{k}",{v},title-builder' for k, v in sorted(_all_scores.items())
                )
                _ex1, _ex2 = st.columns(2)
                with _ex1:
                    st.download_button(
                        "📥 Download as CSV",
                        data=_csv_text,
                        file_name=f"title_builder_scores_{_tb_date.today().isoformat()}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with _ex2:
                    if st.button(f"✓ Clear {len(_all_scores)} (mark as exported)",
                                 key="tb_clear_exported", use_container_width=True,
                                 help="Removes these from the export list. Bank entries are preserved."):
                        # Append all currently-shown phrases to exclusion file
                        new_exclusions = sorted(_exported_set | set(_all_scores.keys()))
                        try:
                            _tb_exported_path.write_text("\n".join(new_exclusions))
                            # Also clear matching entries from session inline_scores + scores JSON
                            for _k in list(_all_scores.keys()):
                                if _k in st.session_state["tb_inline_scores"]:
                                    del st.session_state["tb_inline_scores"][_k]
                            _save_scores()
                            st.success(f"✓ Cleared {len(_all_scores)} from export list")
                            st.rerun()
                        except Exception as _ce:
                            st.error(f"Clear failed: {_ce}")

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# Tab: Playlists — strategic playlist build plan + per-playlist video ordering
# =============================================================================
with tab_playlists:
    st.markdown("## 🎵 Playlist Strategy")
    st.caption(
        "Playlists drive **36-min AVD on Raga Focus vs 19-min channel avg** "
        "(1.9× retention multiplier) but currently only 2.5% of traffic. "
        "Building 6 themed playlists with proper ordering + SEO descriptions is "
        "the highest-leverage 1-hour task on the channel."
    )

    import json as _json
    _pl_path = Path(__file__).parent / "data" / "playlists_plan.json"
    if not _pl_path.exists():
        st.error("Playlists plan not found at data/playlists_plan.json")
    else:
        try:
            _plan = _json.loads(_pl_path.read_text())
        except Exception as _e:
            st.error(f"Failed to load playlists_plan.json: {_e}")
            _plan = None

        if _plan:
            # ---- Header metrics ----
            _cs = _plan.get("current_state", {})
            _existing = _cs.get("existing_playlists", [])
            _existing_total_views = _cs.get("total_playlist_views", 0)
            _missing = _cs.get("missing_playlists", [])
            _to_build = _plan.get("playlists_to_build", [])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Existing playlists", len(_existing), help="On-channel today")
            c2.metric("Missing themes", len(_missing), help="Need to be created")
            c3.metric("Total existing views", f"{_existing_total_views:,}", help="Across all current playlists")
            c4.metric("Planned playlists", len(_to_build), help="Full restructured plan")

            st.markdown("---")

            # ---- Existing playlists summary ----
            with st.expander("📌 Current playlist state", expanded=False):
                if _existing:
                    _df_existing = pd.DataFrame(_existing)
                    st.dataframe(_df_existing, use_container_width=True, hide_index=True)
                if _missing:
                    st.markdown(f"**Missing themed playlists:** {', '.join(_missing)}")
                _adv = _cs.get("playlist_avd_advantage", "")
                if _adv:
                    st.caption(f"AVD advantage: {_adv}")

            # ---- Ordering principle ----
            _principle = _plan.get("ordering_principle", "")
            if _principle:
                st.info(f"💡 **Ordering principle:** {_principle}")

            # ---- Execution order ----
            with st.expander("🎯 Execution order (step-by-step, ~75 min total)", expanded=True):
                _steps = _plan.get("execution_order_for_user", [])
                for _step in _steps:
                    st.markdown(f"- {_step}")
                _est = _plan.get("total_time_estimate", "")
                _impact = _plan.get("expected_impact", "")
                if _est:
                    st.caption(f"⏱ {_est}")
                if _impact:
                    st.success(f"📈 **Expected impact:** {_impact}")

            st.markdown("---")
            st.markdown("### Playlists to build / restructure")

            # ---- Per-playlist cards ----
            _priority_colors = {
                "HIGHEST": "🔥",
                "HIGH": "🔥",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }

            for _pl in _to_build:
                _num = _pl.get("playlist_number", "?")
                _name = _pl.get("name", "Untitled")
                _status = _pl.get("status", "")
                _priority = _pl.get("priority", "")
                _seo = _pl.get("seo_description", "")
                _videos = _pl.get("videos_in_order", [])
                _future = _pl.get("future_additions", [])

                # Priority emoji
                _pri_emoji = "🟡"
                for _key, _emo in _priority_colors.items():
                    if _key in _priority.upper():
                        _pri_emoji = _emo
                        break

                with st.expander(
                    f"{_pri_emoji} **Playlist #{_num} — {_name}** · _{_status}_",
                    expanded=False,
                ):
                    if _priority:
                        st.caption(f"**Priority:** {_priority}")

                    st.markdown("**SEO Description (copy-paste into YT Studio):**")
                    st.code(_seo, language="text")

                    st.markdown(f"**Videos in order ({len(_videos)}):**")
                    if _videos:
                        _vid_rows = []
                        for _v in _videos:
                            _vid_rows.append({
                                "Rank": _v.get("rank", ""),
                                "Title": _v.get("title", ""),
                                "Video ID": _v.get("id", ""),
                                "Views": f"{_v.get('views'):,}" if isinstance(_v.get("views"), (int, float)) else "—",
                                "CTR%": f"{_v.get('ctr'):.2f}" if isinstance(_v.get("ctr"), (int, float)) else "—",
                                "Note": _v.get("note", ""),
                            })
                        _df_vids = pd.DataFrame(_vid_rows)
                        st.dataframe(_df_vids, use_container_width=True, hide_index=True)

                    if _future:
                        st.markdown("**Future additions:**")
                        for _fa in _future:
                            st.markdown(f"- {_fa}")

            # ---- Playlists to retire ----
            _retire = _plan.get("playlists_to_retire_or_dismantle", [])
            if _retire:
                st.markdown("---")
                with st.expander("🗑 Playlists to retire / repurpose", expanded=False):
                    for _r in _retire:
                        st.markdown(f"**{_r.get('name', '?')}** — _{_r.get('action', '')}_")
                        st.caption(_r.get("rationale", ""))

            st.markdown("---")
            st.caption(
                f"📄 Source: `data/playlists_plan.json` · "
                f"Created: {_plan.get('created_at', '?')} · "
                "Edit JSON directly to update this view."
            )

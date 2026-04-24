"""Raga Focus — Channel Intelligence Dashboard (v0 prototype)."""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from auth import yt_data as _yt_data, yt_analytics as _yt_analytics, iso_date as _iso
from production_queue import (
    get_all_videos as get_production_queue,
    set_video_status,
    STATUS_VALUES,
)

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
            sn = item["snippet"]
            st_ = item["statistics"]
            rows.append({
                "video_id": item["id"],
                "title": sn["title"],
                "published": sn["publishedAt"][:10],
                "duration": item["contentDetails"]["duration"],
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
        sn = item["snippet"]
        st_ = item["statistics"]
        rows.append({
            "Published": sn["publishedAt"][:10],
            "Title": sn["title"][:75],
            "Views": int(st_.get("viewCount", 0)),
            "Likes": int(st_.get("likeCount", 0)),
            "Duration": parse_iso_duration(item["contentDetails"]["duration"]),
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
    sn = item["snippet"]
    st_ = item["statistics"]
    cd = item["contentDetails"]

    detail = {
        "video_id": video_id,
        "title": sn["title"],
        "description": sn.get("description", ""),
        "tags": sn.get("tags", []),
        "published": sn["publishedAt"][:10],
        "duration": cd["duration"],
        "lifetime_views": int(st_.get("viewCount", 0)),
        "lifetime_likes": int(st_.get("likeCount", 0)),
        "lifetime_comments": int(st_.get("commentCount", 0)),
    }

    # 28d analytics
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=28)
    try:
        r = ya.reports().query(
            ids="channel==MINE",
            startDate=_iso(start), endDate=_iso(end),
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,shares,comments",
            filters=f"video=={video_id}",
        ).execute()
        cols = [h["name"] for h in r.get("columnHeaders", [])]
        rows = r.get("rows") or [[0] * len(cols)]
        detail["analytics_28d"] = dict(zip(cols, rows[0]))
    except Exception:
        detail["analytics_28d"] = {}

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
tab_overview, tab_daily, tab_videos, tab_detail, tab_competitors, tab_reach, tab_queue = st.tabs(
    ["📊 Overview", "📈 Daily Views", "📺 Videos", "🔍 Video Detail", "⚔️ Competitors", "🎯 Reach Data", "🚀 Production Queue"]
)

# -----------------------------------------------------------------------------
# Tab: Overview
# -----------------------------------------------------------------------------
with tab_overview:
    with st.spinner("Loading channel info..."):
        info = load_my_channel_info()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Subscribers", f"{info['subs']:,}")
    col2.metric("Total Views", f"{info['total_views']:,}")
    col3.metric("Videos Published", info["video_count"])
    col4.metric("Channel Age", f"{(date.today() - pd.to_datetime(info['published']).date()).days} days")

    st.divider()

    with st.spinner(f"Loading last {period} days..."):
        df = load_channel_overview(period)

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

        fig = px.line(
            df, x="day", y="views",
            title=f"Daily views — last {period} days",
            markers=True,
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0), template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
        st.plotly_chart(fig, use_container_width=True)

        # Convert watch minutes to hours for the chart
        df_chart = df.copy()
        df_chart["watch_hours"] = (df_chart["estimatedMinutesWatched"] / 60).round(2)
        fig2 = px.bar(
            df_chart, x="day", y="watch_hours",
            title=f"Daily watch time (hours) — last {period} days",
            labels={"watch_hours": "Hours watched", "day": ""},
        )
        fig2.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

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
            st.dataframe(top5, use_container_width=True, hide_index=True)

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
            st.dataframe(bot5, use_container_width=True, hide_index=True)

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
        st.plotly_chart(fig_ctr, use_container_width=True)

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
                st.dataframe(noisy_show, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab: Daily Views (historical per-video + channel totals)
# -----------------------------------------------------------------------------
with tab_daily:
    st.subheader("📈 Daily views — historical")
    st.caption("Day-by-day view counts. Per-video chart shows every video on the channel; channel chart shows total daily views. Analytics API has a 24-48h reporting lag, so the last 2 days may read low.")

    lookback = st.selectbox(
        "Lookback window",
        [30, 90, 180, 365],
        index=2,
        format_func=lambda x: f"Last {x} days",
        key="daily_lookback",
    )

    with st.spinner(f"Loading {lookback} days of daily data..."):
        per_vid = load_daily_views_all_videos(lookback)
        channel_df = load_channel_overview(lookback)
        all_vids = load_all_my_videos()

    # --- Chart 1: per-video daily views
    st.markdown("#### Per-video daily views")
    if per_vid.empty:
        st.info("No per-video daily data available for this window.")
    else:
        titles = all_vids[["video_id", "title"]].rename(columns={"video_id": "video"})
        per_vid = per_vid.merge(titles, on="video", how="left")
        per_vid["title"] = per_vid["title"].fillna(per_vid["video"])
        per_vid["label"] = per_vid["title"].apply(lambda t: (t[:55] + "…") if len(t) > 55 else t)

        # Filter by cumulative views so the chart doesn't drown in zero-line videos
        totals = per_vid.groupby("label")["views"].sum().sort_values(ascending=False)
        default_selection = totals.head(10).index.tolist()
        all_labels = totals.index.tolist()

        selected = st.multiselect(
            f"Videos on chart (default: top 10 by total views in window, {len(all_labels)} total)",
            options=all_labels,
            default=default_selection,
            key="daily_video_pick",
        )

        if selected:
            plot_df = per_vid[per_vid["label"].isin(selected)]
            fig = px.line(
                plot_df.sort_values("day"),
                x="day",
                y="views",
                color="label",
                title=f"Daily views per video — last {lookback} days",
                labels={"views": "Views", "day": "", "label": "Video"},
            )
            fig.update_layout(
                height=550,
                margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0),
                template="plotly_dark",
                paper_bgcolor="#0E1117",
                plot_bgcolor="#0E1117",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pick at least one video to plot.")

    st.divider()

    # --- Chart 2: channel-total daily views
    st.markdown("#### Channel total daily views")
    if channel_df.empty:
        st.info("No channel data available for this window.")
    else:
        fig2 = px.line(
            channel_df.sort_values("day"),
            x="day",
            y="views",
            markers=True,
            title=f"Channel total daily views — last {lookback} days",
            labels={"views": "Views", "day": ""},
        )
        fig2.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Quick totals
        total_views = int(channel_df["views"].sum())
        peak_row = channel_df.loc[channel_df["views"].idxmax()]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Total views ({lookback}d)", f"{total_views:,}")
        c2.metric("Peak day", peak_row["day"].strftime("%Y-%m-%d"))
        c3.metric("Peak-day views", f"{int(peak_row['views']):,}")


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

    display_cols = ["title", "published", "duration", "views"]
    rename_map = {"title": "Title", "published": "Published", "duration": "Duration", "views": "Lifetime Views"}
    for col, label in [
        ("Subs Gained (28d)", "Subs Gained (28d)"),
        ("Retention %", "Retention %"),
        ("Impressions", "Impressions"),
        ("CTR", "CTR"),
    ]:
        if col in df.columns:
            display_cols.append(col)

    df_display = df[display_cols].rename(columns=rename_map)

    st.subheader(f"All {len(df_display)} videos")
    st.caption("Sort by any column. Data: lifetime views + tags from API, 28d retention/subs from Analytics, Impressions/CTR from REACH_DATA.md")

    st.dataframe(
        df_display,
        use_container_width=True,
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
            st.dataframe(top_retention, use_container_width=True, hide_index=True)

    with col2:
        if "Subs Gained (28d)" in df_display.columns:
            top_subs = df_display.nlargest(5, "Subs Gained (28d)")[["Title", "Subs Gained (28d)", "Lifetime Views"]]
            st.markdown("**Most subs gained (28d)**")
            st.dataframe(top_subs, use_container_width=True, hide_index=True)

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
                        st.info(
                            f"Only 1 data point so far ({r['capture_date'].date()}): "
                            f"**{int(r['impressions']):,} impressions · {r['ctr_pct']:.2f}% CTR**. "
                            f"Import more weekly exports to see the trend."
                        )
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
                            st.plotly_chart(fig_ctr, use_container_width=True)
                        with c2:
                            fig_impr = px.line(
                                vid_hist, x="capture_date", y="impressions", markers=True,
                                title="Impressions over time", labels={"impressions": "Impressions", "capture_date": ""},
                            )
                            fig_impr.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0),
                                                   template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
                            st.plotly_chart(fig_impr, use_container_width=True)

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
                    use_container_width=True,
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
                st.dataframe(
                    kw_df[display_cols].rename(columns={
                        "keyword": "Keyword",
                        "verdict": "Verdict",
                        "score": "VidIQ Score",
                        "volume": "Volume",
                        "notes": "Notes",
                    }).fillna(""),
                    use_container_width=True,
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

    st.dataframe(combined, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("What they've been shipping (latest 5 uploads)")

    for name, cid in COMPETITORS.items():
        st.markdown(f"### {name}")
        with st.spinner(f"Loading latest from {name}..."):
            latest = load_competitor_latest_videos(cid, limit=5)
        st.dataframe(latest, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Tab: Reach Data
# -----------------------------------------------------------------------------
with tab_reach:
    st.subheader("Reach metrics (impressions + CTR)")
    st.caption("Manually captured from YouTube Studio → Analytics → Reach tab. Updates when you edit REACH_DATA.md and refresh.")
    reach = parse_reach_data()
    if reach.empty:
        st.warning("No reach data parsed from REACH_DATA.md. Check file format.")
    else:
        # Join with titles for readability
        videos = load_all_my_videos()
        titles = videos[["video_id", "title"]].rename(columns={"title": "Title"})
        reach_display = reach.merge(titles, on="video_id", how="left")
        reach_display = reach_display[["Title", "Impressions", "CTR", "Views (Reach)", "Unique Viewers"]]
        st.dataframe(reach_display, use_container_width=True, hide_index=True)

        st.divider()

        # CTR parse for chart
        def _ctr_to_float(v):
            try:
                return float(str(v).replace("%", "").replace("—", "nan").strip())
            except Exception:
                return float("nan")

        reach_display["CTR_num"] = reach_display["CTR"].apply(_ctr_to_float)
        chart_df = reach_display.dropna(subset=["CTR_num"]).sort_values("CTR_num", ascending=True)
        if not chart_df.empty:
            fig = px.bar(
                chart_df,
                x="CTR_num",
                y="Title",
                orientation="h",
                title="CTR per video (%)  —  niche benchmark: 3–6%",
                labels={"CTR_num": "CTR %", "Title": ""},
            )
            fig.add_vline(x=3, line_dash="dash", line_color="orange", annotation_text="3% floor")
            fig.add_vline(x=6, line_dash="dash", line_color="green", annotation_text="6% excellent")
            fig.update_layout(height=600, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# Tab: Production Queue
# -----------------------------------------------------------------------------
with tab_queue:
    st.subheader("🚀 Next 7 Videos — Production Briefs")
    st.caption("Full production briefs for each upcoming video — title, description, tags, Suno music prompt, thumbnail image prompt, and success criteria. Pick one to view everything.")

    queue = get_production_queue()

    # Summary table at top — Status column is an inline dropdown.
    st.markdown("### Overview")
    st.caption("Edit the **Status** dropdown directly to mark videos as in progress or published. Changes save instantly to `data/queue_status.json`.")

    summary_rows = []
    for v in queue:
        summary_rows.append({
            "ID": v["id"],
            "Status": v["status"],
            "Publish Date": v["publish_date"],
            "Title": v["title"][:60] + ("…" if len(v["title"]) > 60 else ""),
            "Length": v["length"],
            "Instrument": v["instrument"].split(" + ")[0],
        })
    summary_df = pd.DataFrame(summary_rows)

    edited_df = st.data_editor(
        summary_df,
        use_container_width=True,
        hide_index=True,
        disabled=["ID", "Publish Date", "Title", "Length", "Instrument"],
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=STATUS_VALUES,
                required=True,
            ),
        },
        key="queue_status_editor",
    )

    # Persist any status changes the user made in the editor.
    changes = edited_df.merge(summary_df, on="ID", suffixes=("_new", "_old"))
    changed = changes[changes["Status_new"] != changes["Status_old"]]
    if not changed.empty:
        for _, row in changed.iterrows():
            set_video_status(row["ID"], row["Status_new"])
        st.success(f"Updated status for {len(changed)} video(s).")
        st.rerun()

    st.divider()

    # Picker
    st.markdown("### Drill into a video")
    options = {f"{v['id']} · {v['title'][:80]}": v["id"] for v in queue}
    selected_label = st.selectbox("Choose a video from the queue", list(options.keys()))
    selected_id = options[selected_label]
    video = next(v for v in queue if v["id"] == selected_id)

    # Header metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Length", video["length"])
    c2.metric("Instrument", video["instrument"].split(" + ")[0])
    c3.metric("Publish Date", video["publish_date"])
    status_emoji = {"not_started": "⚪ Not started", "in_progress": "🟡 In progress", "published": "🟢 Published"}.get(video["status"], video["status"])
    c4.metric("Status", status_emoji)

    # Strategic bet
    st.markdown("#### 🎯 Strategic bet")
    st.info(video["strategic_bet"])

    # Validated keywords
    st.markdown("#### 🔑 Validated keywords in this video")
    for kw in video["validated_keywords"]:
        st.markdown(f"- {kw}")

    # Title (copy block)
    st.markdown("#### 📝 Title")
    st.code(video["title"], language=None)

    # Description
    st.markdown("#### 📄 Description")
    with st.expander("View full description", expanded=False):
        st.code(video["description"], language=None)

    # Tags
    st.markdown("#### 🏷️ Tags")
    if video["tags"]:
        tag_count = len(video["tags"].split(","))
        char_count = len(video["tags"])
        st.caption(f"{tag_count} tags · {char_count} chars (limit: 500)")
        st.code(video["tags"], language=None)
    else:
        st.info("🚫 Tags intentionally empty (mirrors Raga Heal's zero-tag approach on their 997K-view flagship)")

    # Suno prompt
    st.markdown("#### 🎵 Suno AI prompt")
    st.caption("Paste into Suno Pro 'Custom Mode' → Style field. Toggle 'Instrumental' ON in the UI.")
    st.code(video["suno_prompt"], language=None)

    # Hz/binaural note
    if video.get("hz") and video["hz"] != "None (keep acoustic/pure)":
        st.caption(f"**Post-production binaural overlay:** {video['hz']} — layer underneath Suno track at -15dB via Audacity. Use [MyNoise.net](https://mynoise.net) or similar to generate the tone.")

    # Thumbnail
    st.markdown("#### 🎨 Thumbnail image prompt")
    st.caption("Paste into Midjourney, DALL-E, or Flux. Generate 4-6 variations, pick best.")
    st.code(video["thumbnail_prompt"], language=None)

    st.markdown("#### 🖼️ Thumbnail text overlay")
    st.caption("Add these after image generation in Canva/Photoshop. Typography: bold serif or sans-serif in warm cream `#FAF3E0`, drop shadow for readability.")
    tt1, tt2 = st.columns([1, 1])
    with tt1:
        st.markdown("**Main text (large, bottom-left)**")
        st.code(video["thumbnail_text_main"], language=None)
    with tt2:
        st.markdown("**Secondary text (small, below main)**")
        st.code(video["thumbnail_text_secondary"], language=None)

    # Success criteria
    st.markdown("#### 📊 Success criteria (14 days post-publish)")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**🟢 Good**")
        st.caption(video["success_good"])
    with sc2:
        st.markdown("**🔥 Breakthrough**")
        st.caption(video["success_breakthrough"])

    st.divider()
    st.caption("💡 Tip: Update status from the **Overview** dropdown above. To add a new video to the pipeline, append a dict to `VIDEOS` in `production_queue.py`.")

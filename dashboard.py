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
tab_overview, tab_daily, tab_videos, tab_detail, tab_competitors, tab_queue, tab_briefs, tab_idea_gen = st.tabs(
    ["📊 Overview", "📈 Daily Views", "📺 Videos", "🔍 Video Detail", "⚔️ Competitors", "🚀 Production Queue", "🧠 Brief Queue (new)", "💡 Idea Generation"]
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
            # Build a 14-day sparkline (zero-fill missing days so the line doesn't lie)
            spark = (
                grp[grp["day"] >= spark_start]
                .set_index("day")["views"]
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
# Tab: Production Queue
# -----------------------------------------------------------------------------
with tab_queue:
    st.subheader("🚀 Next 7 Videos — Production Briefs")
    st.caption("Full production briefs for each upcoming video — title, description, tags, Suno music prompt, thumbnail image prompt, and success criteria. Pick one to view everything.")

    queue = get_production_queue()

    # Map between canonical status values and emoji-prefixed display labels
    # used by the dropdown in the data_editor.
    _STATUS_LABEL = {
        "not_started": "⚪ Not started",
        "in_progress": "🟡 In progress",
        "published": "🟢 Published",
    }
    _LABEL_STATUS = {v: k for k, v in _STATUS_LABEL.items()}

    # Summary table at top — Status column is an inline dropdown.
    st.markdown("### Overview")
    st.caption("Edit the **Status** dropdown directly to mark videos as in progress or published. Changes save instantly to `data/queue_status.json`.")

    summary_rows = []
    for v in queue:
        summary_rows.append({
            "ID": v["id"],
            "Status": _STATUS_LABEL.get(v["status"], v["status"]),
            "Publish Date": v["publish_date"],
            "Title": v["title"][:60] + ("…" if len(v["title"]) > 60 else ""),
            "Length": v["length"],
            "Instrument": v["instrument"].split(" + ")[0],
        })
    summary_df = pd.DataFrame(summary_rows)

    edited_df = st.data_editor(
        summary_df,
        width="stretch",
        hide_index=True,
        disabled=["ID", "Publish Date", "Title", "Length", "Instrument"],
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=list(_STATUS_LABEL.values()),
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
            new_status = _LABEL_STATUS.get(row["Status_new"], row["Status_new"])
            set_video_status(row["ID"], new_status)
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

    briefs = load_all_briefs()
    if not briefs:
        st.info(
            "No briefs yet. Run the pipeline to generate one:\n\n"
            "```\npython3 pipeline/generate_ideas.py\npython3 pipeline/proposal_to_video.py --candidate 1\n```\n\n"
            "Briefs land in `raga-focus-dashboard/data/video_briefs/{slug}.json` and show here."
        )
    else:
        # Status counter strip
        counts = count_by_status()
        cols = st.columns(len(BRIEF_STATUS_VALUES))
        for col, status in zip(cols, BRIEF_STATUS_VALUES):
            with col:
                st.metric(status.replace("_", " ").title(), counts.get(status, 0))

        st.divider()

        # Briefs table with status editor
        st.markdown("### All Briefs (newest first)")
        for b in briefs:
            with st.container():
                c1, c2, c3 = st.columns([4, 2, 2])
                with c1:
                    st.markdown(f"**{b.get('title', '(untitled)')}**")
                    st.caption(f"`{b.get('id')}`  ·  Score {b.get('candidate_score', '—')}  ·  "
                               f"created {b.get('created_at', '')[:10]}")
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
                st.divider()

        # Detail view for selected brief
        selected_id = st.session_state.get("selected_brief_id")
        if selected_id:
            brief = get_brief_by_id(selected_id)
            if brief:
                st.markdown("---")
                st.markdown(f"## 📋 {brief.get('title', '(untitled)')}")
                st.caption(f"Slug: `{brief['id']}`  ·  Status: **{brief.get('status', 'DRAFT')}**")

                # Title variants if available
                if brief.get("title_variants"):
                    with st.expander("📝 A/B/C title variants", expanded=False):
                        for k, v in brief["title_variants"].items():
                            st.markdown(f"- **{k}** ({len(v)} chars): `{v}`")

                # Structural bet + score reasoning
                if brief.get("strategic_bet"):
                    st.markdown(f"**Strategic bet:** {brief['strategic_bet']}")

                # Components
                comps = brief.get("components", {})
                if comps:
                    cols = st.columns(5)
                    for col, (k, v) in zip(cols, comps.items()):
                        col.metric(k.title(), str(v))

                # Suno prompt
                st.markdown("### 🎵 Suno prompt")
                st.code(brief.get("suno_prompt", ""), language="text")

                # Thumbnail
                st.markdown("### 🎨 Thumbnail")
                tcol1, tcol2 = st.columns([1, 2])
                with tcol1:
                    st.markdown(f"**Main text:** `{brief.get('thumbnail_text_main', '—')}`")
                    st.markdown(f"**Subtitle:** `{brief.get('thumbnail_text_secondary', '—')}`")
                    if brief.get("thumbnail_text_variants"):
                        st.caption("Other variants: " + ", ".join(brief["thumbnail_text_variants"]))
                with tcol2:
                    st.markdown("**Image prompt** (paste into Ideogram/Midjourney):")
                    st.code(brief.get("thumbnail_prompt", ""), language="text")

                # Description + Tags
                st.markdown("### 📄 Description")
                st.text_area("Description body",
                             value=brief.get("description", ""),
                             height=300, label_visibility="collapsed",
                             key=f"desc_{brief['id']}")

                st.markdown("### 🏷️ Tags")
                tags = brief.get("tags", "")
                st.code(tags if isinstance(tags, str) else ", ".join(tags), language="text")
                if isinstance(tags, str):
                    st.caption(f"{len(tags)}/500 chars")

                # Production spec
                if brief.get("production_spec"):
                    with st.expander("🛠️ Production spec (binaural, mix, master, ffmpeg)", expanded=False):
                        st.json(brief["production_spec"])

                # Validated keywords
                if brief.get("validated_keywords"):
                    st.markdown("### ✅ Validated keywords")
                    for kw in brief["validated_keywords"]:
                        st.markdown(f"- {kw}")

                # Success criteria
                if brief.get("success_good") or brief.get("success_breakthrough"):
                    st.markdown("### 🎯 Success criteria")
                    cs1, cs2 = st.columns(2)
                    cs1.markdown(f"**Good:** {brief.get('success_good', '—')}")
                    cs2.markdown(f"**Breakthrough:** {brief.get('success_breakthrough', '—')}")

                if st.button("Close brief detail"):
                    del st.session_state["selected_brief_id"]
                    st.rerun()

    st.divider()
    st.caption(
        "💡 Briefs are written by `pipeline/proposal_to_video.py`. To add one, run:\n\n"
        "`python3 pipeline/generate_ideas.py && python3 pipeline/proposal_to_video.py -c 1`"
    )


# -----------------------------------------------------------------------------
# Tab: Idea Generation
# -----------------------------------------------------------------------------
import subprocess
from datetime import date as _idea_date

DASHBOARD_DIR = Path(__file__).parent
# Repo-local first (deployed mode); fall back to project parent (local dev mode)
PIPELINE_DIR  = (DASHBOARD_DIR / "pipeline") if (DASHBOARD_DIR / "pipeline").exists() else (DASHBOARD_DIR.parent / "pipeline")
PROPOSALS_DIR = (DASHBOARD_DIR / "videos" / "proposals") if (DASHBOARD_DIR / "videos" / "proposals").exists() else (DASHBOARD_DIR.parent / "videos" / "proposals")
PROJECT_ROOT  = PIPELINE_DIR.parent


def _run_pipeline_subprocess():
    """Invoke pipeline/generate_ideas.py as a subprocess, return (returncode, stdout, stderr)."""
    if not PIPELINE_DIR.exists():
        return 127, "", f"Pipeline directory not found at {PIPELINE_DIR}"
    try:
        proc = subprocess.run(
            ["python3", "generate_ideas.py"],
            cwd=str(PIPELINE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Pipeline timed out after 120s"
    except Exception as e:
        return 1, "", f"Subprocess error: {e}"


def _latest_proposal_md():
    """Return (path, today_str, exists) for today's proposal markdown."""
    today_str = _idea_date.today().isoformat()
    p = PROPOSALS_DIR / f"{today_str}.md"
    return p, today_str, p.exists()


def _refresh_reach_history():
    """Pull fresh per-video stats via the YouTube Analytics MCP function and
    append a new capture row to REACH_HISTORY.csv. Returns (n_rows, error_or_none).
    """
    import csv
    from datetime import date as _today_d
    try:
        info = load_my_channel_info()
        catalog = load_all_my_videos()
    except Exception as e:
        return 0, f"YouTube API call failed: {e}"
    if catalog.empty:
        return 0, "Catalog empty (API returned no videos)"

    capture = _today_d.today().isoformat()
    hist_path = DASHBOARD_DIR / "data" / "REACH_HISTORY.csv"
    HEADER = ["capture_date", "video_id", "title", "publish_date", "views",
              "watch_hours", "subscribers_gained", "impressions",
              "ctr_pct", "avg_view_duration_sec", "avg_view_pct"]

    # Existing keys to dedupe
    existing_keys = set()
    if hist_path.exists():
        with open(hist_path) as f:
            for r in csv.DictReader(f):
                existing_keys.add((r["video_id"], r["capture_date"]))

    # Per-video impressions/CTR aren't in the Data API — only Views/duration.
    # We write what we have; reach details come from the periodic xlsx export.
    new_rows = []
    for _, v in catalog.iterrows():
        if (v["video_id"], capture) in existing_keys:
            continue
        new_rows.append({
            "capture_date":           capture,
            "video_id":               v["video_id"],
            "title":                  v["title"],
            "publish_date":           v["published"],
            "views":                  int(v["views"]),
            "watch_hours":            "",
            "subscribers_gained":    "",
            "impressions":            "",
            "ctr_pct":                "",
            "avg_view_duration_sec":  "",
            "avg_view_pct":           "",
        })

    if not new_rows:
        return 0, None

    with open(hist_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        for r in new_rows:
            w.writerow(r)
    return len(new_rows), None


with tab_idea_gen:
    st.subheader("💡 Idea Generation — daily video proposal")
    st.caption(
        "Click **Generate Idea** to run the full pipeline: pulls fresh signals "
        "(own catalog via RSS + competitor RSS), scores all combinations, "
        "and writes today's proposal. Result renders below."
    )

    col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 3])

    with col_a:
        gen_clicked = st.button("🚀 Generate Idea", type="primary", use_container_width=True)

    with col_b:
        refresh_clicked = st.button("🔄 Refresh Catalog", use_container_width=True,
                                    help="Clears the dashboard's YouTube API cache so the next run sees your latest uploads.")

    with col_c:
        reach_clicked = st.button("📊 Refresh REACH", use_container_width=True,
                                  help="Pulls fresh per-video stats via the YouTube API and appends a new capture row to REACH_HISTORY.csv.")

    with col_d:
        proposal_path, today_str, has_today = _latest_proposal_md()
        if has_today:
            mtime = datetime.fromtimestamp(proposal_path.stat().st_mtime).strftime("%H:%M")
            st.metric("Today's proposal", f"✓ {today_str}", delta=f"updated {mtime}")
        else:
            st.metric("Today's proposal", "—", delta="not yet generated")

    st.divider()

    # ── Refresh catalog handler ──
    if refresh_clicked:
        st.cache_data.clear()
        st.success("✓ Cache cleared. Next API call will fetch fresh data including latest uploads.")

    # ── Refresh REACH handler ──
    if reach_clicked:
        with st.spinner("Pulling fresh stats from YouTube API…"):
            n, err = _refresh_reach_history()
        if err:
            st.error(f"❌ {err}")
        elif n == 0:
            st.info("No new rows to write — REACH_HISTORY.csv already has today's capture.")
        else:
            st.success(f"✓ Appended {n} new rows to REACH_HISTORY.csv (capture_date={_idea_date.today().isoformat()}).")
            st.caption("Per-video impressions / CTR / AVD% come from the periodic xlsx export; this captures live views + watch.")

    # ── Generate handler ──
    if gen_clicked:
        with st.status("Running pipeline…", expanded=True) as status:
            st.write("📡 Pulling competitor RSS + own-channel uploads…")
            st.write("🎯 Scoring combinations and applying gates…")
            rc, stdout, stderr = _run_pipeline_subprocess()
            if rc == 0:
                status.update(label="✓ Pipeline complete", state="complete")
                if stdout.strip():
                    with st.expander("Pipeline log", expanded=False):
                        st.code(stdout, language="text")
            else:
                status.update(label=f"❌ Pipeline failed (exit {rc})", state="error")
                st.error(stderr or stdout or "Unknown error")
                st.stop()
        # Force re-read of the proposal file
        proposal_path, today_str, has_today = _latest_proposal_md()

    # ── Render today's morning brief ──
    if has_today:
        # Load JSON sidecar (richer than the MD)
        proposal_json_path = proposal_path.with_suffix(".json")
        proposal_data = {}
        if proposal_json_path.exists():
            import json as _json
            try:
                proposal_data = _json.loads(proposal_json_path.read_text())
            except Exception:
                proposal_data = {}

        # Load bank + invalidated set ONCE for the whole tab (used by KO panel,
        # scratchpad, and Score Check panel below — must be defined before any of them).
        import csv as _csv
        bank_path = DASHBOARD_DIR / "data" / "keyword_bank.csv"
        bank_index = {}
        if bank_path.exists():
            with open(bank_path) as f:
                for row in _csv.DictReader(f):
                    bank_index[row["phrase"].strip().lower()] = row

        invalidated_path = DASHBOARD_DIR / "data" / "invalidated_keywords.csv"
        invalidated_set = set()
        if invalidated_path.exists():
            with open(invalidated_path) as f:
                for row in _csv.DictReader(f):
                    invalidated_set.add(row["phrase"].strip().lower())

        # ─────────────────────────────────────────
        # Section 1 — Competitor Pulse (last 7d)
        # ─────────────────────────────────────────
        comp_pulse = proposal_data.get("competitor_pulse", {})
        if comp_pulse:
            st.markdown("### 📡 Competitor Pulse — last 7 days")
            # Header strip — count per competitor
            metric_cols = st.columns(len(comp_pulse) or 1)
            for col, (comp_name, uploads) in zip(metric_cols, comp_pulse.items()):
                with col:
                    label = "uploads (silent this week)" if not uploads else "uploads"
                    col.metric(comp_name, f"{len(uploads)}", delta=label, delta_color="off")

            # Combined sortable table — Channel · Days ago · Views · Likes · Title
            pulse_rows = []
            for comp_name, uploads in comp_pulse.items():
                for u in uploads:
                    pulse_rows.append({
                        "Channel":  comp_name,
                        "Days ago": u.get("days_ago", 0),
                        "Views":    u.get("views"),
                        "Likes":    u.get("likes"),
                        "Title":    u.get("title", ""),
                    })
            if pulse_rows:
                pulse_df = pd.DataFrame(pulse_rows).sort_values("Days ago")
                st.dataframe(
                    pulse_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Channel":  st.column_config.TextColumn(width="small"),
                        "Days ago": st.column_config.NumberColumn(width="small", format="%dd ago"),
                        "Views":    st.column_config.NumberColumn(width="small", format="%d"),
                        "Likes":    st.column_config.NumberColumn(width="small", format="%d"),
                        "Title":    st.column_config.TextColumn(width="large"),
                    },
                )
            st.divider()

        # ─────────────────────────────────────────
        # Section 2 — Keyword Opportunities (mined from competitors)
        # ─────────────────────────────────────────
        ko = proposal_data.get("keyword_opportunities", [])
        if ko:
            from urllib.parse import quote_plus
            st.markdown("### 🔍 Keyword Opportunities — mined from competitor titles")
            st.caption(
                "Phrases competitors are using that aren't in our `keyword_bank.csv` yet. "
                "Run each on VidIQ → paste the score below → bulk-save."
            )

            if "ko_score_inputs" not in st.session_state:
                st.session_state["ko_score_inputs"] = {}

            for c in ko:
                phrase = c.get("phrase", "")
                uses = c.get("uses", 0)
                sources = ", ".join(c.get("sources", []))
                latest = c.get("latest_days", "?")
                vidiq_url = f"https://app.vidiq.com/keywords/{quote_plus(phrase)}"
                yt_url    = f"https://www.youtube.com/results?search_query={quote_plus(phrase)}"
                row = st.columns([4, 2, 1, 1, 2])
                with row[0]:
                    st.markdown(f"**`{phrase}`**")
                    st.caption(f"used {uses}× by {sources} · latest {latest}d ago")
                with row[1]:
                    st.markdown(f"[🔗 VidIQ]({vidiq_url}) · [▶ YouTube]({yt_url})")
                with row[2]:
                    score = st.number_input(
                        "score",
                        min_value=0, max_value=100, value=0, step=1,
                        key=f"ko_score_{phrase}",
                        label_visibility="collapsed",
                    )
                with row[3]:
                    if score >= 60:
                        st.markdown("✅")
                    elif score > 0:
                        st.markdown("❌")
                    else:
                        st.markdown("—")
                with row[4]:
                    st.caption("type score →")
                if score > 0:
                    st.session_state["ko_score_inputs"][phrase] = score

            ko_save_clicked = st.button("💾 Bulk-save mined-keyword scores", key="ko_bulk_save",
                                        use_container_width=False)
            if ko_save_clicked:
                import sys as _sys
                _sys.path.insert(0, str(PIPELINE_DIR))
                try:
                    from persistence import auto_promote_vidiq_scores
                    scores = {p: s for p, s in st.session_state["ko_score_inputs"].items() if s > 0}
                    if scores:
                        result = auto_promote_vidiq_scores(scores, source=f"dashboard-ko-{_idea_date.today().isoformat()}")
                        promoted = result.get("promoted", [])
                        invalidated = result.get("invalidated", [])
                        msg = []
                        if promoted: msg.append(f"✓ {len(promoted)} promoted")
                        if invalidated: msg.append(f"✗ {len(invalidated)} invalidated")
                        st.success(" · ".join(msg))
                    else:
                        st.warning("No scores entered yet — type a value > 0 in any row, then save.")
                except Exception as e:
                    st.error(f"Save failed: {e}")
            st.divider()

        # ─────────────────────────────────────────
        # Section 2.5 — Test Random Titles (scratchpad)
        # ─────────────────────────────────────────
        with st.expander("🧪 Test custom titles / phrases (scratchpad)", expanded=True):
            st.caption(
                "Brainstorm space — paste any phrases or full titles, one per line, "
                "to scan their bank scores, length checks, kill-phrase checks, "
                "and quick VidIQ / YouTube lookup links. Use this for random ideas "
                "outside today's pipeline output."
            )
            test_input = st.text_area(
                "Paste phrases or titles (one per line)",
                placeholder="example:\nsomatic healing music\npolyvagal reset music\nMorning Anxiety? | 528Hz Sitar | Alpha Wave",
                height=120,
                key="test_phrases_input",
            )
            test_clicked = st.button("🔎 Scan all", key="test_scan_btn")
            if test_clicked and test_input.strip():
                from urllib.parse import quote_plus as _qp2
                # Load kill phrases + own catalog (for recency-overlap check)
                try:
                    import sys as _sys2
                    _sys2.path.insert(0, str(PIPELINE_DIR))
                    from config import KILL_PHRASES as _KILL
                    from signals import load_own_catalog, theme_overlap_with_recent, find_in_titles
                    own_catalog = load_own_catalog()
                except Exception as _ex:
                    _KILL = []
                    own_catalog = []
                    theme_overlap_with_recent = None
                    find_in_titles = None

                rows = []
                for raw in test_input.splitlines():
                    p = raw.strip()
                    if not p:
                        continue
                    p_lower = p.lower()
                    bank_row = bank_index.get(p_lower)
                    bank_score = ""
                    if bank_row:
                        s = bank_row.get("vidiq_score", "").strip()
                        if s.isdigit():
                            bank_score = int(s)
                    is_inv = p_lower in invalidated_set
                    kill_hit = next((k for k in _KILL if k in p_lower), None)
                    is_title_like = "|" in p
                    length_ok = (60 <= len(p) <= 88) if is_title_like else None

                    # Own-catalog cannibalization check (same gate the pipeline uses).
                    # 1. Exact-substring match with any title shipped in last 5 days
                    # 2. Theme-token overlap with any title shipped in last 5 days
                    own_recency_warnings = []
                    if own_catalog and find_in_titles is not None:
                        # Exact-substring check on the FULL phrase first
                        full_hits = find_in_titles(own_catalog, p_lower, within_days=5)
                        for d, t in full_hits[:1]:
                            short = t[:55] + ("…" if len(t) > 55 else "")
                            own_recency_warnings.append(f"❌ exact match in own video {d}d ago: '{short}'")
                        # Theme-token overlap (catches Sleep Music vs Can't Fall Asleep)
                        if not full_hits and theme_overlap_with_recent is not None:
                            theme_hits = theme_overlap_with_recent(own_catalog, p_lower, within_days=5)
                            if theme_hits:
                                tokens = sorted(set(h[0] for h in theme_hits))
                                first = theme_hits[0]
                                short = first[2][:55] + ("…" if len(first[2]) > 55 else "")
                                own_recency_warnings.append(
                                    f"❌ theme-overlap {tokens} with own video {first[1]}d ago: '{short}'"
                                )

                    verdict_parts = []
                    # Order: recency block (highest priority) → kill → invalidated → length → bank → fallback
                    verdict_parts.extend(own_recency_warnings)
                    if kill_hit:
                        verdict_parts.append(f"❌ kill: '{kill_hit}'")
                    if is_inv:
                        verdict_parts.append("❌ invalidated")
                    if is_title_like and length_ok is False:
                        verdict_parts.append(f"⚠️ len {len(p)}")
                    if isinstance(bank_score, int):
                        if bank_score >= 60:
                            verdict_parts.append(f"✅ bank {bank_score}")
                        else:
                            verdict_parts.append(f"⚠️ bank {bank_score}")
                    if not verdict_parts:
                        verdict_parts.append("⚠️ untested")

                    rows.append({
                        "Phrase":  p,
                        "Length":  len(p),
                        "Status":  " · ".join(verdict_parts),
                        "VidIQ":   f"https://app.vidiq.com/keywords/{_qp2(p)}",
                        "YouTube": f"https://www.youtube.com/results?search_query={_qp2(p)}",
                    })

                if rows:
                    test_df = pd.DataFrame(rows)
                    st.dataframe(
                        test_df,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "Phrase":  st.column_config.TextColumn(width="large"),
                            "Length":  st.column_config.NumberColumn(width="small"),
                            "Status":  st.column_config.TextColumn(width="medium"),
                            "VidIQ":   st.column_config.LinkColumn("VidIQ", display_text="🔗 open"),
                            "YouTube": st.column_config.LinkColumn("YouTube", display_text="▶ search"),
                        },
                    )

                # ── Decomposed component check + score input + bulk save ──
                # For each pipe-separated title, break out the components and let user paste
                # VidIQ scores inline. This is the validate-before-ship affordance for any
                # custom title (not just pipeline-proposed ones).
                title_lines = [r["Phrase"] for r in rows if "|" in r["Phrase"]]
                phrase_only_lines = [r["Phrase"] for r in rows if "|" not in r["Phrase"]]
                all_components = []  # list of (parent_idx, component_phrase)

                if title_lines:
                    st.markdown("---")
                    st.markdown("**🔬 Validate before ship — paste VidIQ scores per component:**")
                    st.caption(
                        "For each title, the components below are what YouTube and VidIQ "
                        "actually score against. Paste each score → click Save → bank auto-updates."
                    )
                    if "scratch_score_inputs" not in st.session_state:
                        st.session_state["scratch_score_inputs"] = {}

                    for ti, title in enumerate(title_lines, 1):
                        parts = [p.strip() for p in title.split("|") if p.strip()]
                        # Filter: skip pure-duration parts ("1 Hour", "30 Min")
                        components = [
                            p for p in parts
                            if not (p.lower().endswith("hour") or "min" in p.lower().split()[-1] if p.split() else False)
                        ]
                        st.markdown(f"**`{title}`**")
                        for ci, comp in enumerate(components):
                            comp_lower = comp.lower()
                            existing = bank_index.get(comp_lower)
                            cur = ""
                            badge = "⚠️ UNTESTED"
                            if comp_lower in invalidated_set:
                                badge = "❌ INVALIDATED previously"
                            elif existing:
                                s = existing.get("vidiq_score", "").strip()
                                if s.isdigit():
                                    cur = int(s)
                                    badge = f"✅ bank: {s}" if int(s) >= 60 else f"⚠️ bank: {s}"

                            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                            with c1:
                                st.markdown(f"`{comp}`")
                                st.caption(badge)
                            with c2:
                                st.markdown(
                                    f"[🔗 VidIQ](https://app.vidiq.com/keywords/{_qp2(comp)})  ·  "
                                    f"[▶ YT](https://www.youtube.com/results?search_query={_qp2(comp)})"
                                )
                            with c3:
                                key = f"scratch_score_t{ti}_c{ci}"
                                new_val = st.number_input(
                                    "score", min_value=0, max_value=100,
                                    value=int(cur) if isinstance(cur, int) else 0,
                                    step=1, key=key, label_visibility="collapsed",
                                )
                                if new_val and new_val != (cur if isinstance(cur, int) else 0):
                                    st.session_state["scratch_score_inputs"][comp_lower] = new_val
                            with c4:
                                if new_val >= 60:
                                    st.markdown("✅ pass")
                                elif new_val > 0:
                                    st.markdown("❌ fail (auto-invalidate)")
                                else:
                                    st.caption("type score →")

                    save_clicked = st.button("💾 Save scratchpad scores", key="scratch_save_btn")
                    if save_clicked:
                        import sys as _sys3
                        _sys3.path.insert(0, str(PIPELINE_DIR))
                        try:
                            from persistence import auto_promote_vidiq_scores
                            scores = dict(st.session_state.get("scratch_score_inputs", {}))
                            scores = {k: v for k, v in scores.items() if v > 0}
                            if scores:
                                result = auto_promote_vidiq_scores(
                                    scores,
                                    source=f"dashboard-scratchpad-{_idea_date.today().isoformat()}",
                                )
                                promoted = result.get("promoted", [])
                                invalidated = result.get("invalidated", [])
                                msg = []
                                if promoted: msg.append(f"✓ {len(promoted)} promoted to bank")
                                if invalidated: msg.append(f"✗ {len(invalidated)} added to invalidated")
                                st.success(" · ".join(msg))
                            else:
                                st.warning("No scores entered — type a value > 0 in any field, then save.")
                        except Exception as _e:
                            st.error(f"Save failed: {_e}")

        # ─────────────────────────────────────────
        # Section 3 — Today's candidates (existing markdown render)
        # ─────────────────────────────────────────
        st.markdown(f"### 🏆 Today's candidates — {today_str}")
        st.caption(f"Source: `{proposal_path.relative_to(PROJECT_ROOT)}`")
        proposal_md = proposal_path.read_text()
        with st.container(border=True):
            st.markdown(proposal_md)

        # ────────────────────────────────────────────────────
        # Score Check panel — validate + auto-bank + re-rank
        # ────────────────────────────────────────────────────
        st.divider()
        st.markdown("### 🔍 Score Check — validate keywords, auto-bank, re-rank")
        st.caption(
            "Read each candidate's keywords below. Paste fresh VidIQ scores → "
            "**Save** writes to `keyword_bank.csv` (≥60) or `invalidated_keywords.csv` (<60). "
            "Then **Re-rank** re-runs the pipeline with the new data."
        )
        st.info(
            "**Score legend:** ✅ PASS (≥60) · ❌ FAIL (<60, auto-invalidates) · "
            "⚠️ UNTESTED (no score yet) · 🟡 STALE (last checked >30d ago, re-validate)",
            icon="ℹ️",
        )

        # Load proposal JSON sidecar (richer than the MD)
        proposal_json_path = proposal_path.with_suffix(".json")
        if proposal_json_path.exists():
            import json as _json
            try:
                proposal_data = _json.loads(proposal_json_path.read_text())
            except Exception:
                proposal_data = {}
        else:
            proposal_data = {}

        # bank_index and invalidated_set already loaded at the top of the tab.
        candidates = proposal_data.get("candidates", [])[:3]  # top 3 only — keep UI focused
        if not candidates:
            st.info("No candidate JSON found — re-run Generate Idea to get the structured payload.")
        else:
            from datetime import date as _d
            today = _d.today()

            def score_badge(phrase: str):
                """Return (badge_label, current_score, last_check, is_invalidated)."""
                p = phrase.strip().lower()
                if p in invalidated_set:
                    return "❌ FAILED previously", None, None, True
                row = bank_index.get(p)
                if not row:
                    return "⚠️ UNTESTED", None, None, False
                score = row.get("vidiq_score", "").strip()
                if not score.isdigit():
                    return "⚠️ UNTESTED", None, row.get("last_score_check", ""), False
                score = int(score)
                last_check = row.get("last_score_check", "")
                stale = False
                if last_check:
                    try:
                        days = (today - _d.fromisoformat(last_check)).days
                        if days > 30:
                            stale = True
                    except Exception:
                        pass
                if stale:
                    return f"🟡 STALE ({score}, checked {last_check})", score, last_check, False
                if score >= 60:
                    return f"✅ PASS ({score})", score, last_check, False
                return f"❌ FAIL ({score})", score, last_check, False

            # Initialise score-input state
            if "vidiq_score_inputs" not in st.session_state:
                st.session_state["vidiq_score_inputs"] = {}

            for idx, cand in enumerate(candidates, start=1):
                comp = cand.get("components", {})
                title = cand.get("title") or cand.get("variants", {}).get("A_seo", "(untitled)")
                with st.expander(f"#{idx} — {title}", expanded=(idx == 1)):
                    # Keywords to validate for this candidate
                    keywords_to_check = []
                    keywords_to_check.append(("full_title", title, "Full title string"))
                    if comp.get("problem"):
                        keywords_to_check.append(("problem", comp["problem"]["kw"], "Problem keyword"))
                    if comp.get("instrument"):
                        keywords_to_check.append(("instrument", comp["instrument"]["name"].lower(), "Instrument"))
                    if comp.get("hz"):
                        keywords_to_check.append(("hz", comp["hz"]["hz"].lower(), "Hz"))
                    if comp.get("raga"):
                        keywords_to_check.append(("raga", comp["raga"]["name"].lower(), "Raga"))

                    # Promote to Brief button — top-right of expander
                    promote_col1, promote_col2 = st.columns([4, 1])
                    with promote_col2:
                        promote_clicked = st.button(
                            "🚀 Promote to Brief",
                            key=f"promote_btn_{idx}",
                            use_container_width=True,
                            help="Runs proposal_to_video.py --candidate N → creates a brief in Brief Queue tab",
                        )
                    if promote_clicked:
                        try:
                            proc = subprocess.run(
                                ["python3", "proposal_to_video.py", "--candidate", str(idx)],
                                cwd=str(PIPELINE_DIR),
                                capture_output=True, text=True, timeout=60,
                            )
                            if proc.returncode == 0:
                                st.success(f"✓ Brief created for candidate #{idx}. Check the **🧠 Brief Queue** tab.")
                                with st.expander("Promote log"):
                                    st.code(proc.stdout, language="text")
                            else:
                                st.error(f"❌ Promote failed (exit {proc.returncode})")
                                st.code(proc.stderr or proc.stdout)
                        except Exception as e:
                            st.error(f"Subprocess error: {e}")

                    st.markdown("**Keywords for this candidate:**")
                    from urllib.parse import quote_plus as _qp
                    for slot, kw, label in keywords_to_check:
                        badge, cur_score, last_check, is_inv = score_badge(kw)
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        with c1:
                            st.markdown(f"`{kw}`")
                            st.caption(f"{label} · {badge}")
                        with c2:
                            vidiq_url = f"https://app.vidiq.com/keywords/{_qp(kw)}"
                            yt_url    = f"https://www.youtube.com/results?search_query={_qp(kw)}"
                            st.markdown(f"[🔗 VidIQ]({vidiq_url})  ·  [▶ YT]({yt_url})")
                        with c3:
                            input_key = f"score_{idx}_{slot}_{kw}"
                            new_score = st.number_input(
                                "VidIQ score",
                                min_value=0, max_value=100,
                                value=int(cur_score) if cur_score is not None else 0,
                                step=1, key=input_key,
                                label_visibility="collapsed",
                                help="Paste the VidIQ score (0-100). 0 = skip / not yet checked.",
                            )
                        with c4:
                            if new_score and new_score != (cur_score or 0):
                                st.caption("✏️ changed")
                            else:
                                st.caption("— no change —")
                            # Track for batch save
                            st.session_state["vidiq_score_inputs"][(idx, slot, kw)] = (new_score, slot if slot != "full_title" else "tag")

            # Save & re-rank buttons
            col_save, col_rerank, _ = st.columns([2, 2, 4])
            with col_save:
                save_clicked = st.button("💾 Save scores", use_container_width=True, key="save_scores_btn")
            with col_rerank:
                rerank_clicked = st.button("🔁 Re-rank with new scores", type="primary", use_container_width=True, key="rerank_btn")

            if save_clicked:
                # Auto-promote scores via persistence.py
                import sys as _sys
                _sys.path.insert(0, str(PIPELINE_DIR))
                try:
                    from persistence import auto_promote_vidiq_scores
                    scores_to_save = {}
                    slot_hints = {}
                    for (cand_idx, slot, kw), (score, write_slot) in st.session_state["vidiq_score_inputs"].items():
                        if score and score > 0:
                            scores_to_save[kw] = score
                            slot_hints[kw] = write_slot
                    if scores_to_save:
                        result = auto_promote_vidiq_scores(scores_to_save, slot_hint=slot_hints, source=f"dashboard-{_idea_date.today().isoformat()}")
                        promoted = result.get("promoted", [])
                        invalidated = result.get("invalidated", [])
                        msg = []
                        if promoted:
                            msg.append(f"✓ {len(promoted)} promoted to keyword_bank.csv")
                        if invalidated:
                            msg.append(f"✗ {len(invalidated)} added to invalidated_keywords.csv")
                        if msg:
                            st.success(" · ".join(msg))
                        else:
                            st.info("No scores to save (all were 0 or unchanged).")
                    else:
                        st.warning("No scores entered — type a value > 0 in any field, then Save.")
                except Exception as e:
                    st.error(f"Save failed: {e}")

            if rerank_clicked:
                with st.status("Re-running pipeline…", expanded=True) as status:
                    st.write("🔁 Reading updated keyword_bank.csv + invalidated_keywords.csv…")
                    st.write("🎯 Re-scoring candidates with fresh data…")
                    rc, stdout, stderr = _run_pipeline_subprocess()
                    if rc == 0:
                        status.update(label="✓ Re-rank complete", state="complete")
                    else:
                        status.update(label=f"❌ Re-rank failed (exit {rc})", state="error")
                        st.error(stderr or stdout or "Unknown error")
                        st.stop()
                st.rerun()
    else:
        st.info(
            "No proposal for today yet. Click **🚀 Generate Idea** above to run the pipeline."
        )

    st.divider()
    with st.expander("⚙️ How this works"):
        st.markdown(
            """
            **Inputs (read live each run):**
            - Own-channel RSS (catches new uploads immediately, no manual export needed)
            - `REACH_HISTORY.csv` (analytics if available, optional)
            - Raga Heal + Shanti Instrumentals RSS (competitor pulse, last 14d)
            - `keyword_bank.csv` (validated VidIQ scores)
            - `config.py` rules (musicology, kill list, scoring weights)

            **Process:**
            1. Brute-force every {problem × instrument × Hz × raga × wave} combo
            2. Apply ~13 automatic gates (length, kill phrases, recency, tonal fit, cannibalization, competitor saturation)
            3. Score each candidate; rank top 5
            4. Generate A/B/C title variants + 4-tier tag stack + Suno prompt + production spec
            5. Write `videos/proposals/YYYY-MM-DD.md` and `.json`

            **Manual gates after** (you do these):
            - VidIQ score on the full title (must be ≥50)
            - YouTube top-5 search dominance check
            """
        )

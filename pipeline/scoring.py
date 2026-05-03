"""
Raga Focus — Scoring + Title/Tag Generation

Pure functions. Inputs = static config + fresh signals. Outputs = scores + content.
"""

import csv as _csv
import json as _json
import sys as _sys
from datetime import date as _date, timedelta as _td
from pathlib import Path

from config import (
    PROBLEM_HOOKS, INSTRUMENTS, FREQUENCIES, RAGAS, WAVE_FRAMES,
    TONAL_FIT, KILL_PHRASES, RULES, WEIGHTS,
)
from signals import (
    instrument_last_used, hz_last_used, raga_last_used, wave_last_used,
    competitor_instrument_uses, competitor_problem_uses, find_in_titles,
    theme_overlap_with_recent,
)


# ═══════════════════════════════════════════════════════════
# TITLE BUILDING — lean 3-slot format (derived from A/B test winners)
#
# Winner pattern: "{SEO keyword} | {secondary keyword} with {Instrument} | 1 Hour"
# Proven: Calm Your Mind | Veena Healing Music | 1 hour  (41 chars, 2.1× margin)
#         Deep Rest Music | Find Stillness with Surbahar | 1 Hour  (#1 by views)
#
# Both slot 1 AND slot 2 are VidIQ-ranked keywords from the bank.
# Slot 2 = best compatible keyword (problem or tag, ≥60) that doesn't
#          overlap with slot 1 tokens. Falls back to action_phrase from config.
# Hz and Wave are metadata for tags/scoring — NOT title slots.
# Raga appears only in Variant B to test raga-name CTR lift.
# ═══════════════════════════════════════════════════════════

_SEC_STOPS = {"music", "for", "the", "with", "to", "of", "and", "your",
              "you", "this", "that", "in", "on", "at", "an", "a", "my"}

# Focus/productivity keywords — wrong lane for healing/sleep/anxiety content
_FOCUS_LANE = {"focus", "study", "work", "concentration", "coding", "productivity",
               "pomodoro", "lofi", "deep work", "coffee"}

# Healing-lane signal tokens — if problem contains any of these, skip focus-lane secondaries
_HEALING_LANE = {"heal", "calm", "relax", "sleep", "rest", "anxiety", "stress",
                 "meditation", "peace", "sooth", "nostalgia", "comfort", "gentle",
                 "serene", "ambient", "nervous", "nerve", "vagus", "unwind", "overthink",
                 "emotional", "burnout", "insomnia", "drift", "stillness", "grounding",
                 "grief", "loss", "lonely", "loneliness", "heartbreak", "sad", "sadness",
                 "depress", "trauma", "nervous", "panic", "fear", "worry", "tired"}


def _meaningful_tokens_title(text):
    return {w.lower().strip("?!.,") for w in text.split() if len(w) >= 3 and w.lower() not in _SEC_STOPS}


def _pick_secondary_keyword(problem_kw, recent_tokens=None):
    """Return the best VidIQ-ranked keyword to use as title slot 2.

    Pulls from problem + tag slots (both are searchable).
    Filters:
      - score ≥ 60
      - no token overlap with slot 1
      - no token overlap with recent_tokens (3-day title block)
      - no focus-lane keywords when problem is in the healing lane
    Prefers keywords ending in 'music' for natural slot-2 phrasing.
    Falls back to None → caller uses action_phrase from config.
    """
    try:
        from keyword_bank import load_by_slot
        rows = load_by_slot("problem") + load_by_slot("tag")
    except Exception:
        return None

    slot1_tokens  = _meaningful_tokens_title(problem_kw)
    recent_tokens = recent_tokens or set()

    # Determine if this problem is in the healing lane → exclude focus-lane secondaries
    prob_lower   = problem_kw.lower()
    is_healing   = any(sig in prob_lower for sig in _HEALING_LANE)

    candidates = []
    for r in rows:
        phrase = r.get("phrase", "").strip()
        score  = r.get("vidiq_score")
        if not phrase or score is None:
            continue
        try:
            score = int(score)
        except (ValueError, TypeError):
            continue
        if score < 60:
            continue
        if phrase.lower() == problem_kw.lower():
            continue

        phrase_tokens = _meaningful_tokens_title(phrase)

        # Skip if overlaps with slot 1
        if phrase_tokens & slot1_tokens:
            continue
        # Skip if any token would conflict with recent titles
        if phrase_tokens & {t.lower() for t in recent_tokens}:
            continue
        # Skip focus-lane keywords for healing-lane problems
        if is_healing and phrase_tokens & _FOCUS_LANE:
            continue

        candidates.append((score, phrase))

    if not candidates:
        return None

    # Sort: highest score first; prefer "music" keywords at same tier
    candidates.sort(key=lambda x: (-x[0], 0 if "music" in x[1].lower() else 1))
    return candidates[0][1].title()


def _render_A(problem, instrument, secondary_kw=None):
    """Variant A — SEO safe: '{keyword} | {secondary keyword} with {Instrument} | 1 Hour'"""
    seo   = problem.get("seo_phrase") or problem["kw"].title()
    slot2 = secondary_kw or problem.get("action_phrase") or seo
    return f"{seo} | {slot2} with {instrument['name']} | 1 Hour"


def _render_B(problem, raga, secondary_kw=None):
    """Variant B — experiment: '{Question} | {secondary keyword} with Raga {Raga} | 1 Hour'"""
    question = problem.get("question") or (problem["kw"].title() + "?")
    slot2    = secondary_kw or problem.get("outcome_short") or problem.get("action_phrase") or problem["kw"].title()
    return f"{question} | {slot2} with Raga {raga['name']} | 1 Hour"


def build_title(problem, hz, instrument, raga, wave, recent_tokens=None):
    """Default title = Variant A (safe SEO). Hz/wave not in title — used for tags."""
    secondary = _pick_secondary_keyword(problem["kw"], recent_tokens)
    return _render_A(problem, instrument, secondary)


def build_variants(problem, hz, instrument, raga, wave, recent_tokens=None):
    """Two A/B title variants, both using VidIQ-ranked keywords for all slots.

    A — SEO safe:   {keyword} | {best bank keyword} with {Instrument} | 1 Hour
    B — Experiment: {Question} | {best bank keyword} with Raga {Name} | 1 Hour

    recent_tokens: set of tokens from own catalog last 3 days — excluded from slot 2.
    Falls back to config action_phrase if no compatible secondary keyword found.
    """
    secondary = _pick_secondary_keyword(problem["kw"], recent_tokens)
    return {
        "A_seo":      _render_A(problem, instrument, secondary),
        "B_question": _render_B(problem, raga, secondary),
    }


def title_passes_basic_filters(title):
    """Length + kill-phrase check. Returns (passes, reason_if_not)."""
    if len(title) < RULES["title_min_chars"]:
        return False, f"too short ({len(title)} chars)"
    if len(title) > RULES["title_max_chars"]:
        return False, f"too long ({len(title)} chars)"
    title_l = title.lower()
    for kill in KILL_PHRASES:
        if kill in title_l:
            return False, f"contains kill phrase '{kill}'"
    return True, None


# ═══════════════════════════════════════════════════════════
# TONAL FIT — match instrument to problem mood
# ═══════════════════════════════════════════════════════════
def tonal_match_keyword(problem_kw):
    """Find the TONAL_FIT bucket whose key appears in the problem keyword."""
    pkw = problem_kw.lower()
    for key in TONAL_FIT:
        if key in pkw:
            return key
    return None


def tonal_score(problem_kw, instrument_name):
    """Returns (score, label) for tonal fit."""
    key = tonal_match_keyword(problem_kw)
    if not key:
        return 0, "no tonal mapping"
    fit = TONAL_FIT[key]
    if instrument_name in fit.get("primary", []):
        return WEIGHTS["tonal_primary"], f"primary fit for {key}"
    if instrument_name in fit.get("secondary", []):
        return WEIGHTS["tonal_secondary"], f"secondary fit for {key}"
    if instrument_name in fit.get("avoid", []):
        return WEIGHTS["tonal_avoid"], f"AVOID for {key}"
    return 0, f"neutral for {key}"


# ═══════════════════════════════════════════════════════════
# CANDIDATE SCORING
# ═══════════════════════════════════════════════════════════
def score_candidate(problem, instrument, hz, raga, wave, catalog, competitor_data, _pw=None):
    """Score a single candidate. Returns (total_score, reasons_list).

    _pw: pre-loaded performance_weights dict (pass from generate_candidates to avoid
         re-reading the file on every call). Falls back to disk load if None.
    """
    score = 100
    reasons = []

    # ── PROBLEM ───────────────────────────────────────
    own_uses = find_in_titles(catalog, problem["kw"])
    # HARD GATE: same exact keyword used in last 5 days → disqualify
    # (We CAN do another sleep-themed video; we CAN'T re-use "sleep music" within 5d.)
    recent_uses = [(d, t) for d, t in own_uses if d <= 5]
    if recent_uses:
        d, t = recent_uses[0]
        short = t[:55] + ("…" if len(t) > 55 else "")
        return -1000, [f"❌ HARD SKIP: '{problem['kw']}' used in own title {d}d ago: '{short}'"]
    if own_uses:
        score += WEIGHTS["problem_claimed_by_us"]
        reasons.append(f"❌ '{problem['kw']}' already in our catalog: {len(own_uses)} videos (latest {own_uses[0][0]}d ago)")
    if problem.get("vidiq_score") is None:
        score += WEIGHTS["problem_needs_vidiq"]
        reasons.append(f"⚠️ '{problem['kw']}' VidIQ score unknown — must validate before ship")
    elif problem["vidiq_score"] >= 60:
        boost = (problem["vidiq_score"] - 60) * WEIGHTS["problem_vidiq_boost_per_pt"]
        score += boost
        reasons.append(f"✅ '{problem['kw']}' VidIQ {problem['vidiq_score']} HIGH (+{boost})")
    if problem.get("competitor_proven"):
        score += WEIGHTS["problem_competitor_proven"]
        reasons.append(f"✅ Competitor-proven: {problem['competitor_proven']}")

    # Competitor recently posted same problem?
    comp_problem_recent = competitor_problem_uses(competitor_data, problem["kw"], within_days=7)
    if comp_problem_recent:
        score += WEIGHTS["competitor_used_last_5d"]
        latest = comp_problem_recent[0]
        reasons.append(f"⚠️ Competitor topic-overlap: {latest['competitor']} — '{latest['title']}' ({latest['days_ago']}d ago)")

    # HARD GATE — theme-token overlap with our OWN recent videos (last 5 days).
    # YouTube treats semantic clusters as one (e.g. "Sleep Music" and "Can't Fall
    # Asleep" target the same audience), so any meaningful token overlap within
    # 5 days = self-cannibalization → disqualify.
    own_theme_overlaps = theme_overlap_with_recent(catalog, problem["kw"], within_days=7)  # theme window, not exact
    if own_theme_overlaps:
        unique_tokens = sorted(set(t[0] for t in own_theme_overlaps))
        most_recent = min(t[1] for t in own_theme_overlaps)
        first = own_theme_overlaps[0]
        short = first[2][:55] + ("…" if len(first[2]) > 55 else "")
        return -1000, [
            f"❌ HARD SKIP: theme-overlap on {unique_tokens} with our own video {most_recent}d ago: '{short}'"
        ]

    # AUDIENCE-CLUSTER awareness — INFORMATIONAL ONLY, no score penalty
    # Different SEO keywords are independently rankable even if audience overlaps.
    # Cluster is recorded so generate_ideas.py can surface DOUBLE-DOWN vs DIVERSIFY tracks.
    from config import PROBLEM_TO_RAGA_MOOD
    new_cluster = None
    for key, cluster in PROBLEM_TO_RAGA_MOOD.items():
        if key in problem["kw"].lower():
            new_cluster = cluster
            break
    if new_cluster:
        # Count how many of last 5 videos target same cluster (label, no penalty)
        from datetime import date as _date
        same_cluster_count = 0
        for v in catalog[:8]:
            days_ago = (_date.today() - v["publish_date"]).days
            if days_ago > 5:
                continue
            t_lower = v["title"].lower()
            for key, cluster in PROBLEM_TO_RAGA_MOOD.items():
                if cluster == new_cluster and key in t_lower:
                    same_cluster_count += 1
                    break
        if same_cluster_count >= 2:
            reasons.append(
                f"ℹ️ Audience cluster '{new_cluster}' covered {same_cluster_count}× in last 5d "
                f"(label only — different SEO keyword still rankable)"
            )
        # NOTE: hardcoded PROBLEM_TO_RAGA_MOOD is a brittle seed — should be replaced
        # with semantic LLM classifier (cache-first). Documented in next session's todos.

    # ── TONAL FIT ─────────────────────────────────────
    t_score, t_label = tonal_score(problem["kw"], instrument["name"])
    score += t_score
    if t_score < 0:
        reasons.append(f"❌ Tonal: {instrument['name']} = {t_label}")
        return score, reasons  # hard disqualify
    elif t_score > 0:
        reasons.append(f"✅ Tonal: {instrument['name']} = {t_label} (+{t_score})")

    # ── INSTRUMENT ────────────────────────────────────
    inst_last = instrument_last_used(catalog, instrument["name"])
    if inst_last is not None and inst_last < RULES["own_recency_block_days"]:
        score += WEIGHTS["instrument_used_last_5d"]  # -1000 → effectively disqualified
        reasons.append(f"❌ HARD SKIP: {instrument['name']} used {inst_last}d ago (rule: <{RULES['own_recency_block_days']}d)")
        return score, reasons
    elif inst_last is not None:
        reasons.append(f"ℹ️ {instrument['name']} last used {inst_last}d ago — clear")

    # VidIQ comp boost
    if instrument.get("vidiq_comp") == "Very Low":
        score += WEIGHTS["instrument_vidiq_very_low"]
    elif instrument.get("vidiq_comp") == "Low":
        score += WEIGHTS["instrument_vidiq_low"]
    elif instrument.get("vidiq_comp") == "Med" or instrument.get("vidiq_comp") == "Medium":
        score += WEIGHTS["instrument_vidiq_med"]
    elif instrument.get("vidiq_comp") == "High":
        score += WEIGHTS["instrument_vidiq_high"]

    # Competitor saturation on this instrument
    comp_count, comp_recent = competitor_instrument_uses(competitor_data, instrument["name"], within_days=RULES["trending_window_days"])
    if comp_count == 0:
        score += WEIGHTS["instrument_competitor_unique"]
        reasons.append(f"⭐ {instrument['name']}: 0 competitor uses in {RULES['trending_window_days']}d — unique to us")
    elif comp_count >= 3:
        score += WEIGHTS["instrument_competitor_heavy"]
        reasons.append(f"⚠️ {instrument['name']}: {comp_count} competitor uses in {RULES['trending_window_days']}d — saturated")
    if comp_recent is not None and comp_recent < RULES["competitor_recency_days"]:
        score += WEIGHTS["competitor_used_last_5d"]
        reasons.append(f"⚠️ {instrument['name']} used by competitor {comp_recent}d ago")

    # Trending check
    if comp_count == 0 and instrument.get("vidiq_score") is None:
        # No competitor signal AND no VidIQ data = dead instrument
        score -= 30
        reasons.append(f"❌ {instrument['name']}: no competitor signal in {RULES['trending_window_days']}d AND no VidIQ score — non-trending")

    # ── HZ ────────────────────────────────────────────
    hz_last = hz_last_used(catalog, hz["hz"])
    if hz_last is not None and hz_last <= 7:
        score += WEIGHTS["hz_used_last_7d"]
        reasons.append(f"⚠️ {hz['hz']} used {hz_last}d ago")

    # ── RAGA ──────────────────────────────────────────
    raga_last = raga_last_used(catalog, raga["name"])
    if raga_last is not None and raga_last <= 7:
        score += WEIGHTS["raga_used_last_7d"]
        reasons.append(f"⚠️ Raga {raga['name']} used {raga_last}d ago")

    # ── WAVE ──────────────────────────────────────────
    wave_last = wave_last_used(catalog, wave["wave"])
    if wave_last is not None and wave_last <= 7:
        score += WEIGHTS["wave_used_last_7d"]
        reasons.append(f"⚠️ {wave['wave']} wave used {wave_last}d ago")

    # Wave–problem match
    if any(m in problem["kw"].lower() for m in wave.get("matches", [])):
        score += WEIGHTS["wave_problem_match"]
        reasons.append(f"✅ {wave['wave']} matches '{problem['kw']}'")

    # ── PERFORMANCE LEARNING (from performance_weights.json) ──────────────
    # Boost candidates whose instrument or problem keyword is proven on our channel.
    # performance_score > 1.0 = above channel average; < 1.0 = below average.
    # Bonus = (performance_score - 1.0) * 15, capped at ±25 points.
    try:
        if _pw is None:
            import json as _json
            from pathlib import Path as _Path
            _pw_path = _Path(__file__).parent.parent / "data" / "performance_weights.json"
            _pw = _json.loads(_pw_path.read_text()) if _pw_path.exists() else {}
        if _pw:
            _inst_name = instrument.get("name", "") if isinstance(instrument, dict) else str(instrument)
            _inst_data = _pw.get("instruments", {}).get(_inst_name)
            if _inst_data and _inst_data.get("video_count", 0) >= 1:
                _boost = max(-25, min(25, (_inst_data["performance_score"] - 1.0) * 15))
                if _boost > 2:
                    reasons.append(f"🚀 {_inst_name} proven: {_inst_data['avg_views']:.0f} avg views, {_inst_data['avg_view_pct']:.1f}% AVD (score {_inst_data['performance_score']:.2f}×)")
                elif _boost < -2:
                    reasons.append(f"⚠️ {_inst_name} underperforming: {_inst_data['avg_views']:.0f} avg views (score {_inst_data['performance_score']:.2f}×)")
                score += round(_boost)
            _pkw = problem.get("kw", "").lower() if isinstance(problem, dict) else str(problem).lower()
            _kw_data = _pw.get("problem_keywords", {}).get(_pkw)
            if _kw_data and _kw_data.get("video_count", 0) >= 1:
                _boost = max(-25, min(25, (_kw_data["performance_score"] - 1.0) * 15))
                if _boost > 2:
                    reasons.append(f"🚀 '{_pkw}' proven: {_kw_data['avg_views']:.0f} avg views, {_kw_data['avg_ctr_pct']:.2f}% CTR (score {_kw_data['performance_score']:.2f}×)")
                elif _boost < -2:
                    reasons.append(f"⚠️ '{_pkw}' underperforming: {_kw_data['avg_views']:.0f} avg views (score {_kw_data['performance_score']:.2f}×)")
                score += round(_boost)
    except Exception:
        pass

    return score, reasons


# ═══════════════════════════════════════════════════════════
# 3-day title-token recency: every candidate's title must NOT share any
# meaningful token with our last-3-days own catalog titles.
# ═══════════════════════════════════════════════════════════
def _recent_title_tokens(catalog, within_days=3):
    """Return set of meaningful tokens used in own catalog titles in last N days."""
    from datetime import date
    from signals import _meaningful_tokens
    today = date.today()
    tokens = set()
    for v in catalog:
        days_ago = (today - v["publish_date"]).days
        if days_ago <= within_days:
            for tok in _meaningful_tokens(v["title"]):
                tokens.add(tok)
    return tokens


def _title_tokens(title):
    from signals import _meaningful_tokens
    return set(_meaningful_tokens(title))


# ═══════════════════════════════════════════════════════════
# Strategy tagging: each candidate gets one of three strategy labels
# based on portfolio-thinking:
#   🎯 competitor — counter what Raga Heal / Shanti just shipped
#   💎 niche — double down on the audience cluster that's working for us
#   🌙 moonshot — fresh / creative bet outside the proven lane
# ═══════════════════════════════════════════════════════════
def _own_top_clusters(catalog, top_k=4):
    """Identify audience clusters of top-K best-performing own videos."""
    from config import PROBLEM_TO_RAGA_MOOD
    # Use views as proxy if available; else publish recency
    sorted_vids = sorted(catalog, key=lambda v: -(v.get("views", 0) or 0))[:top_k]
    clusters = []
    for v in sorted_vids:
        title_l = v["title"].lower()
        for key, cluster in PROBLEM_TO_RAGA_MOOD.items():
            if key in title_l:
                clusters.append(cluster)
                break
    return set(clusters)


def _tag_strategy(candidate, competitor_data, own_top_clusters):
    """Tag candidate with one of: 'competitor', 'niche', 'moonshot'."""
    from config import PROBLEM_TO_RAGA_MOOD
    from signals import competitor_problem_uses
    comp = candidate["components"]
    prob_kw = comp["problem"]["kw"].lower()

    # 1. Competitor-driven — competitor used this problem in last 7d
    comp_recent = competitor_problem_uses(competitor_data, prob_kw, within_days=7)
    if comp_recent:
        candidate["strategy"] = "competitor"
        candidate["strategy_note"] = f"Counter-strategy: {comp_recent[0]['competitor']} used this problem {comp_recent[0]['days_ago']}d ago"
        return candidate

    # 2. Niche doubling-down — problem's cluster matches our top performers
    cand_cluster = None
    for key, cluster in PROBLEM_TO_RAGA_MOOD.items():
        if key in prob_kw:
            cand_cluster = cluster
            break
    if cand_cluster and cand_cluster in own_top_clusters:
        candidate["strategy"] = "niche"
        candidate["strategy_note"] = f"Doubling down on '{cand_cluster}' cluster — your proven audience"
        return candidate

    # 3. Moonshot — anything else
    candidate["strategy"] = "moonshot"
    candidate["strategy_note"] = "Fresh angle outside your proven lane — high-variance bet"
    return candidate


# ═══════════════════════════════════════════════════════════
# CANDIDATE GENERATION
# ═══════════════════════════════════════════════════════════

# Rough problem-keyword → raga mood mapping for greedy raga picker.
# Keeps raga selection musically coherent without a full instrument_fit matrix.
# Will be superseded by RAGA_META instrument_fit in the next optimisation pass.
_RAGA_MOOD_MAP = {
    "sleep":        {"peace", "grandeur", "depth", "lunar"},
    "rest":         {"peace", "grandeur", "depth", "serenity"},
    "unwind":       {"peace", "serenity", "romance", "longing"},
    "anxiety":      {"peace", "devotional", "yearning", "serenity"},
    "overthinking": {"peace", "serenity", "devotional"},
    "stress":       {"peace", "serenity", "longing"},
    "meditation":   {"peace", "serenity", "devotional", "cheerful"},
    "emotional":    {"pathos", "longing", "romance", "depth"},
    "focus":        {"cheerful", "majestic", "yearning"},
    "morning":      {"cheerful", "devotional", "majestic"},
    "healing":      {"peace", "serenity", "devotional"},
    "grounding":    {"peace", "grandeur", "serenity"},
    "nostalgia":    {"romance", "longing", "pathos"},
    "comfort":      {"peace", "serenity", "devotional"},
}


def _best_hz(catalog):
    avail = [h for h in FREQUENCIES if (hz_last_used(catalog, h["hz"]) or 999) > 7]
    pool = avail or list(FREQUENCIES)
    return sorted(pool, key=lambda h: -(h.get("vidiq_score") or 0))[0]


def _best_wave(catalog, problem_kw):
    pkw = problem_kw.lower()
    matched = [w for w in WAVE_FRAMES if any(m in pkw for m in w.get("matches", []))]
    pool = matched or list(WAVE_FRAMES)
    return sorted(pool, key=lambda w: (wave_last_used(catalog, w["wave"]) or 999), reverse=True)[0]


def _best_raga(catalog, problem_kw):
    avail = [r for r in RAGAS if (raga_last_used(catalog, r["name"]) or 999) > 7]
    pool = avail or list(RAGAS)
    pkw = problem_kw.lower()
    target_moods = set()
    for kw, moods in _RAGA_MOOD_MAP.items():
        if kw in pkw:
            target_moods |= moods
    if target_moods:
        mood_matched = [r for r in pool if r.get("mood", "").lower() in target_moods]
        if mood_matched:
            pool = mood_matched
    return sorted(pool, key=lambda r: (raga_last_used(catalog, r["name"]) or 999), reverse=True)[0]


def generate_candidates(catalog, competitor_data, top_n=3):
    """Generate, score, tag with strategy, return 1 per strategy bucket.

    Optimised: pre-filters problems / instruments / tonal pairs before scoring,
    then greedy-picks Hz / Raga / Wave per pair.
    ~438 evaluations vs 473,200 in the original nested loop.
    """
    _sys.path.insert(0, str(Path(__file__).parent.parent))
    import storage as _storage
    from paths import DATA_DIR as _DD

    today      = _date.today()
    today_str  = today.isoformat()

    # ── 1. Load performance weights ONCE ──────────────────────────────────
    _pw = {}
    try:
        _pw_path = Path(__file__).parent.parent / "data" / "performance_weights.json"
        if _pw_path.exists():
            _pw = _json.loads(_pw_path.read_text())
    except Exception:
        pass

    # ── 2. Build exclusion sets (before any scoring) ──────────────────────
    parked_problems    = set()
    permanent_sigs     = set()
    cooldown_blocks_meta = {}

    def _sig(comp):
        def _g(key, sub):
            v = comp.get(key)
            return ((v.get(sub) or "") if isinstance(v, dict) else (v or "")).strip().lower()
        return "|".join([_g("problem","kw"), _g("instrument","name"),
                         _g("hz","hz"), _g("raga","name"), _g("wave","wave")])

    try:
        for row in _storage.read_dismissed_candidates():
            if row.get("dismissed_on", "").strip() == today_str:
                prob = row.get("problem_keyword", "").strip().lower()
                if not prob and row.get("signature"):
                    prob = row["signature"].split("|")[0].strip().lower()
                if prob:
                    parked_problems.add(prob)
    except Exception:
        pass

    try:
        for b in _storage.read_all_briefs():
            s = _sig(b.get("components", {}))
            if s and s != "||||":
                permanent_sigs.add(s)
    except Exception:
        pass

    try:
        SHIP_FLOOR = 14
        COMBO_BLOCK = 30
        for row in _storage.read_shipped_titles():
            try:
                days_ago = (today - _date.fromisoformat(row["shipped_on"])).days
                pkw  = row.get("problem_kw",  "").strip().lower()
                inst = row.get("instrument",  "").strip().lower()
                if not pkw:
                    continue
                if days_ago < SHIP_FLOOR and pkw not in cooldown_blocks_meta:
                    cooldown_blocks_meta[pkw] = {
                        "reason": f"shipped {days_ago}d ago (floor)", "video_title": row.get("title",""),
                        "video_id": row.get("brief_id",""), "days_since": days_ago, "views_14d": 0,
                    }
                if inst and days_ago < COMBO_BLOCK:
                    permanent_sigs.add(f"{pkw}|{inst}||||")
            except Exception:
                continue
    except Exception:
        pass

    try:
        ACTIVE_WIN = 7
        ACTIVE_THR = 30
        views_in_win = {}
        reach_path = _DD / "REACH_HISTORY.csv"
        if reach_path.exists():
            from collections import defaultdict as _dd
            win_start = today - _td(days=ACTIVE_WIN + 7)
            per_vid = _dd(list)
            with open(reach_path) as f:
                for row in _csv.DictReader(f):
                    try:
                        cd = _date.fromisoformat(row["capture_date"])
                        if cd >= win_start:
                            per_vid[row["video_id"]].append((cd, int(row["views"] or 0)))
                    except Exception:
                        continue
            for vid_id, snaps in per_vid.items():
                snaps.sort()
                views_in_win[vid_id] = max(0, snaps[-1][1]-snaps[0][1]) if len(snaps)>=2 else snaps[0][1]
        _STOPS = {"music","for","the","with","to","of","and","your","you","this","that","in","on","at","an","a"}
        for _vid in catalog:
            _title    = (_vid.get("title") or "").lower()
            _vid_id   = _vid.get("video_id", "")
            _pub      = _vid.get("publish_date")
            _days     = (today - _pub).days if hasattr(_pub, "year") else 999
            _v14      = views_in_win.get(_vid_id, _vid.get("views") or 0)
            if not (_days < ACTIVE_WIN or _v14 >= ACTIVE_THR):
                continue
            _ttoks = {w.strip("?!,.:;") for w in _title.replace("|"," ").split() if len(w)>=3}
            for _prob in PROBLEM_HOOKS:
                _pkw = _prob["kw"].lower()
                if _pkw in cooldown_blocks_meta:
                    continue
                _ptoks = [t for t in _pkw.split() if len(t)>=3 and t not in _STOPS]
                if not _ptoks:
                    continue
                if all(any(pt in tt or tt in pt for tt in _ttoks) for pt in _ptoks):
                    _r = (f"shipped {_days}d ago (floor {ACTIVE_WIN}d)"
                          if _days < ACTIVE_WIN else f"still active ({_v14} views last {ACTIVE_WIN}d)")
                    cooldown_blocks_meta[_pkw] = {
                        "reason": _r, "video_title": _vid.get("title",""),
                        "video_id": _vid_id, "days_since": _days, "views_14d": _v14,
                    }
    except Exception:
        pass

    cooldown_keys = set(cooldown_blocks_meta.keys())

    # ── 3. Pre-filter available problems ──────────────────────────────────
    # Exact keyword: 21-day block — never compete with your own video on the same search term.
    # Theme overlap: 7-day block — different keyword, same audience is OK after a week.
    _EXACT_WINDOW = 21
    _THEME_WINDOW = 7
    available_problems = []
    for p in PROBLEM_HOOKS:
        pkw = p["kw"].lower()
        if pkw in parked_problems or pkw in cooldown_keys:
            continue
        if any(d <= _EXACT_WINDOW for d, _ in find_in_titles(catalog, pkw)):
            continue
        if theme_overlap_with_recent(catalog, pkw, within_days=_THEME_WINDOW):
            continue
        available_problems.append(p)

    # ── 4. Pre-filter available instruments ───────────────────────────────
    available_instruments = [
        i for i in INSTRUMENTS
        if (instrument_last_used(catalog, i["name"]) or 999) >= RULES["own_recency_block_days"]
    ]

    # ── 5. Remove tonal-avoid (problem, instrument) pairs ─────────────────
    valid_pairs = []
    for p in available_problems:
        key        = tonal_match_keyword(p["kw"])
        avoid_set  = set(TONAL_FIT.get(key or "", {}).get("avoid", []))
        for inst in available_instruments:
            if inst["name"] not in avoid_set:
                valid_pairs.append((p, inst))

    # ── 6. Score valid pairs ───────────────────────────────────────────────
    best_hz       = _best_hz(catalog)
    recent_tokens = _recent_title_tokens(catalog, within_days=3)
    candidates    = []

    for problem, instrument in valid_pairs:
        raga  = _best_raga(catalog, problem["kw"])
        wave  = _best_wave(catalog, problem["kw"])
        # Pass recent_tokens so slot-2 keyword picker avoids recently-used tokens
        title = build_title(problem, best_hz, instrument, raga, wave, recent_tokens)
        passes, _ = title_passes_basic_filters(title)
        if not passes:
            continue
        if recent_tokens and (_title_tokens(title) & recent_tokens):
            continue
        comp_dict = {"problem": problem, "instrument": instrument,
                     "hz": best_hz, "raga": raga, "wave": wave}
        sig = _sig(comp_dict)
        if sig in permanent_sigs:
            continue
        if f"{problem['kw'].lower()}|{instrument['name'].lower()}||||" in permanent_sigs:
            continue
        score, reasons = score_candidate(
            problem, instrument, best_hz, raga, wave,
            catalog, competitor_data, _pw=_pw,
        )
        variants = build_variants(problem, best_hz, instrument, raga, wave, recent_tokens)
        candidates.append({"title": title, "score": score, "variants": variants,
                            "reasons": reasons, "components": comp_dict})

    candidates.sort(key=lambda c: -c["score"])
    # Dedupe + diversify across the top N:
    #   - 1 candidate per (problem, instrument) pair
    #   - max 2 of any single instrument in the top N
    #   - max 2 of any single raga in the top N
    #   - max 3 of any single Hz in the top N
    # Keeps the candidate list visually + structurally varied so we're not
    # proposing the same Sarangi×Bhairavi×174Hz combo for 5 different problems.
    # ═════════════════════════════════════════════
    # Strategic 3-bucket selection (user-requested portfolio thinking):
    #   🎯 competitor — counter Raga Heal / Shanti recent uploads
    #   💎 niche — double down on our top-performing audience cluster
    #   🌙 moonshot — fresh / unused / untested direction (high variance)
    # Each bucket gets exactly 1 candidate. Returns up to 3 total.
    # ═════════════════════════════════════════════
    own_top_clusters = _own_top_clusters(catalog, top_k=4)
    for c in candidates:
        _tag_strategy(c, competitor_data, own_top_clusters)

    # Apply moonshot novelty bonus — within the moonshot bucket, prefer
    # candidates with components we haven't used in 14+ days AND that have
    # untested or no competitor history.
    for c in candidates:
        if c.get("strategy") != "moonshot":
            continue
        novelty = 0
        comp = c["components"]
        days_inst = instrument_last_used(catalog, comp["instrument"]["name"])
        days_hz   = hz_last_used(catalog, comp["hz"]["hz"])
        days_raga = raga_last_used(catalog, comp["raga"]["name"])
        days_wave = wave_last_used(catalog, comp["wave"]["wave"])
        for d in (days_inst, days_hz, days_raga, days_wave):
            if d is None:        # never used
                novelty += 30
            elif d >= 14:        # cold — fresh again
                novelty += 15
            elif d >= 7:
                novelty += 5
        if comp["problem"].get("vidiq_score") is None:
            novelty += 25      # untested problem = real moonshot
        c["score"] += novelty
        c.setdefault("reasons", []).append(f"🌙 Moonshot novelty bonus +{novelty}")

    # Re-sort by updated scores
    candidates.sort(key=lambda c: -c["score"])

    # Group by strategy and pick top 1 per bucket
    buckets = {"competitor": [], "niche": [], "moonshot": []}
    for c in candidates:
        s = c.get("strategy", "moonshot")
        if s in buckets:
            buckets[s].append(c)
    # Capture pre-backfill counts for transparency in the UI
    bucket_counts = {k: len(v) for k, v in buckets.items()}

    # Cross-bucket constraint: top 3 must have different problem keywords,
    # different instruments, AND no theme-token overlap between problems.
    _STOPS = {"music","for","the","with","to","of","and","your","you",
              "this","that","in","on","at","an","a","after","work"}

    def _prob_tokens(kw):
        return {w for w in kw.lower().split() if len(w) >= 3 and w not in _STOPS}

    def _theme_clash(prob_kw, picked_token_sets):
        toks = _prob_tokens(prob_kw)
        return any(toks & s for s in picked_token_sets)

    picked_problems    = set()
    picked_instruments = set()
    picked_token_sets  = []
    deduped = []
    filled_buckets = set()
    for bucket_name in ["competitor", "niche", "moonshot"]:
        for c in buckets[bucket_name]:
            prob = c["components"]["problem"]["kw"]
            inst = c["components"]["instrument"]["name"]
            if prob in picked_problems or inst in picked_instruments:
                continue
            if _theme_clash(prob, picked_token_sets):
                continue
            picked_problems.add(prob)
            picked_instruments.add(inst)
            picked_token_sets.append(_prob_tokens(prob))
            c["bucket_filled"] = bucket_name
            c["backfilled"]    = False
            deduped.append(c)
            filled_buckets.add(bucket_name)
            break

    # Backfill empty buckets — same constraints apply
    empty_buckets = [b for b in ("competitor", "niche", "moonshot") if b not in filled_buckets]
    if len(deduped) < top_n:
        for c in candidates:
            prob = c["components"]["problem"]["kw"]
            inst = c["components"]["instrument"]["name"]
            if prob in picked_problems or inst in picked_instruments:
                continue
            if _theme_clash(prob, picked_token_sets):
                continue
            picked_problems.add(prob)
            picked_instruments.add(inst)
            picked_token_sets.append(_prob_tokens(prob))
            c["bucket_filled"] = c.get("strategy", "moonshot")
            c["backfilled"]    = True
            c["backfilled_for"] = empty_buckets[0] if empty_buckets else None
            if empty_buckets:
                empty_buckets.pop(0)
            deduped.append(c)
            if len(deduped) >= top_n:
                break

    # Stash bucket counts + cooldown blocks on the first candidate so the
    # proposal-builder can surface both at top level in the JSON output.
    if deduped:
        deduped[0]["_bucket_counts"] = bucket_counts
        deduped[0]["_cooldown_blocks"] = cooldown_blocks_meta

    return deduped[:top_n]


# ═══════════════════════════════════════════════════════════
# TAG GENERATION
# ═══════════════════════════════════════════════════════════
BROAD_TAGS = [
    "calm music", "relaxing music", "ambient music", "background music",
    "meditation music", "indian classical music", "instrumental music",
]

PROBLEM_CLUSTER_TAGS = {
    "overthinking":    ["overthinking music", "anxiety relief music", "stress relief music", "calm anxious mind", "music for overthinkers"],
    "anxiety":         ["anxiety relief music", "stress relief music", "anxiety music", "panic relief music", "music for anxiety"],
    "sleep":           ["sleep music", "deep sleep music", "delta wave sleep", "music for insomnia", "fall asleep fast"],
    "stress":          ["stress relief music", "stress reduction music", "cortisol reset", "calm music for stress"],
    "meditation":      ["deep meditation", "meditation music", "indian meditation", "raga meditation"],
    "nervous system":  ["nervous system reset", "vagus nerve music", "polyvagal theory", "parasympathetic music"],
    "emotional":       ["emotional healing music", "emotional release music", "heart healing music"],
    "unwind":          ["unwind music", "wind down music", "evening relaxation"],
    "rest":            ["deep rest music", "deep relaxation music"],
    "vagus":           ["vagus nerve music", "polyvagal theory", "parasympathetic music", "vagus nerve reset"],
    "dopamine":        ["dopamine reset", "dopamine detox", "digital reset music"],
}

INSTRUMENT_TAGS = {
    "Bansuri":  ["bansuri", "bansuri music", "bansuri instrumental music", "indian bamboo flute", "bamboo flute meditation"],
    "Sarangi":  ["sarangi", "sarangi music", "sarangi meditation", "bowed indian instrument"],
    "Dilruba":  ["dilruba", "dilruba music", "dilruba instrumental music", "dilruba strings"],
    "Veena":    ["veena", "veena music", "veena meditation", "ancient indian veena"],
    "Sarod":    ["sarod", "sarod music", "indian sarod"],
    "Santoor":  ["santoor", "santoor music"],
    "Esraj":    ["esraj", "esraj music"],
    "Tanpura":    ["tanpura", "tanpura drone", "tanpura meditation"],
    "Sitar":      ["sitar", "sitar music", "sitar meditation"],
    "Swarmandal": ["swarmandal", "swarmandal music", "swarmandal meditation", "indian harp music"],
    "Surbahar":   ["surbahar", "surbahar music", "surbahar meditation", "bass sitar", "surbahar instrumental"],
}


def build_tags(problem, instrument, hz, raga, wave, max_chars=500):
    """Generate a YouTube tag list within 500-char limit. Returns list[str]."""
    tags = []
    used_chars = 0

    def add(tag):
        nonlocal used_chars
        if not tag:
            return
        # +2 for comma+space separator (except first)
        cost = len(tag) + (2 if tags else 0)
        if used_chars + cost <= max_chars:
            tags.append(tag)
            used_chars += cost

    # Tier 1 — REQUIRED
    add(problem["kw"])
    for t in INSTRUMENT_TAGS.get(instrument["name"], []):
        add(t)
    add(f"{hz['hz']} music")
    add(f"{hz['hz']}")
    add(f"{wave['wave']} waves")
    add(f"{wave['wave']} wave music")
    add(f"raga {raga['name'].lower()}")
    add(f"{raga['name'].lower()} raga")

    # Tier 2 — BROAD
    for t in BROAD_TAGS:
        add(t)

    # Tier 3 — PROBLEM CLUSTER
    fit_key = tonal_match_keyword(problem["kw"])
    if fit_key and fit_key in PROBLEM_CLUSTER_TAGS:
        for t in PROBLEM_CLUSTER_TAGS[fit_key]:
            add(t)

    # Tier 4 — LONG-TAIL fillers
    long_tail = [
        f"1 hour {instrument['name'].lower()} music",
        f"{instrument['name'].lower()} for {fit_key}" if fit_key else None,
        f"indian classical {instrument['name'].lower()}",
        f"{wave['wave'].lower()} wave meditation",
        "raga focus",
        "indian flute meditation" if instrument["name"] == "Bansuri" else None,
        f"music to {fit_key}" if fit_key else None,
    ]
    for t in long_tail:
        add(t)

    return tags

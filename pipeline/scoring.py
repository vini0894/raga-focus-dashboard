"""
Raga Focus — Scoring + Title/Tag Generation

Pure functions. Inputs = static config + fresh signals. Outputs = scores + content.
"""

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
# TITLE BUILDING
# ═══════════════════════════════════════════════════════════
def _render(hook_text, hz, instrument, raga, wave):
    """Internal — renders the 5-slot template with whatever hook text is passed."""
    return f"{hook_text} | {hz['hz']} {instrument['name']} Raga {raga['name']} | {wave['wave']} Wave {wave['outcome']} | 1 Hour"


def build_title(problem, hz, instrument, raga, wave):
    """Default: SEO-led title (validated keyword phrase as the hook).

    The question hook lives on the THUMBNAIL, not the title.
    See A/B/C variants for question-led + outcome-led alternates.
    """
    seo_hook = problem.get("seo_phrase") or problem.get("phrase") or problem["kw"].title()
    return _render(seo_hook, hz, instrument, raga, wave)


def build_variants(problem, hz, instrument, raga, wave):
    """3 variants for YouTube A/B title testing.

    A — SEO-led:        leads with validated keyword phrase (best for search rank)
    B — Question-led:   leads with visceral question (best for cold-feed CTR)
    C — Outcome-led:    leads with imperative/promise (best for warm cohort)

    All share identical keyword stack after the first slot, so the test isolates
    the hook variable cleanly.
    """
    seo_hook      = problem.get("seo_phrase") or problem["kw"].title()
    question_hook = problem.get("question")   or problem.get("phrase") or seo_hook
    outcome_hook  = problem.get("outcome")    or seo_hook

    return {
        "A_seo":      _render(seo_hook,      hz, instrument, raga, wave),
        "B_question": _render(question_hook, hz, instrument, raga, wave),
        "C_outcome":  _render(outcome_hook,  hz, instrument, raga, wave),
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
def score_candidate(problem, instrument, hz, raga, wave, catalog, competitor_data):
    """Score a single candidate. Returns (total_score, reasons_list)."""
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
    own_theme_overlaps = theme_overlap_with_recent(catalog, problem["kw"], within_days=5)
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
def generate_candidates(catalog, competitor_data, top_n=3):
    """Generate, score, tag with strategy, return 1 per strategy bucket."""
    candidates = []
    # 3-day title-token block — no candidate's title may share a meaningful
    # token with our own catalog from the last 3 days.
    recent_tokens = _recent_title_tokens(catalog, within_days=3)

    for problem in PROBLEM_HOOKS:
        for instrument in INSTRUMENTS:
            for hz in FREQUENCIES:
                for raga in RAGAS:
                    for wave in WAVE_FRAMES:
                        title = build_title(problem, hz, instrument, raga, wave)
                        passes, reason = title_passes_basic_filters(title)
                        if not passes:
                            continue
                        # 3-day title-token gate
                        if recent_tokens and (_title_tokens(title) & recent_tokens):
                            continue
                        score, reasons = score_candidate(problem, instrument, hz, raga, wave, catalog, competitor_data)
                        candidates.append({
                            "title":      title,
                            "score":      score,
                            "reasons":    reasons,
                            "components": {
                                "problem":    problem,
                                "instrument": instrument,
                                "hz":         hz,
                                "raga":       raga,
                                "wave":       wave,
                            },
                        })

    # Build exclusion sets:
    #   1. data/dismissed_candidates.csv → PARKED PROBLEM KEYWORDS (today only)
    #   2. data/video_briefs/*.json → permanent EXACT 5-slot signature exclusion
    #      (briefs are explicit "we're building this" — never re-suggest the same
    #      5-tuple). Problem-keyword-only is NOT permanent — see cooldown logic.
    #   3. cooldown_blocks (NEW) → problem keywords blocked because we shipped
    #      a similar video recently or it's still pulling meaningful views.
    #      Auto-expires when (age >= 14d AND views_last_14d < threshold).
    #
    # Stashed on the candidates list as `_cooldown_blocks_meta` so the
    # generate_ideas writer can surface it transparently in the proposal JSON.
    cooldown_blocks_meta = {}  # {problem_kw: {reason, video_title, days_since, views_14d}}
    try:
        import csv as _csv, json as _json
        from datetime import date as _date
        from paths import DATA_DIR as _DD
        today = _date.today()
        today_str = today.isoformat()

        parked_problems = set()
        permanent_signatures = set()

        def _sig_from_components(comp):
            def _get(key, sub):
                v = comp.get(key)
                if isinstance(v, dict):
                    return (v.get(sub) or "").strip().lower()
                return (v or "").strip().lower()
            return "|".join([
                _get("problem",    "kw"),
                _get("instrument", "name"),
                _get("hz",         "hz"),
                _get("raga",       "name"),
                _get("wave",       "wave"),
            ])

        # 1. Today's parked problems
        dismissed_path = _DD / "dismissed_candidates.csv"
        if dismissed_path.exists():
            with open(dismissed_path) as f:
                for row in _csv.DictReader(f):
                    if row.get("dismissed_on", "").strip() == today_str:
                        prob = row.get("problem_keyword", "").strip().lower()
                        if not prob and row.get("signature"):
                            prob = row["signature"].split("|")[0].strip().lower()
                        if prob:
                            parked_problems.add(prob)

        # 2. Brief signature exclusion (5-tuple — permanent)
        briefs_dir = _DD / "video_briefs"
        if briefs_dir.exists():
            for brief_file in briefs_dir.glob("*.json"):
                try:
                    b = _json.loads(brief_file.read_text())
                    sig = _sig_from_components(b.get("components", {}))
                    if sig and sig != "||||":
                        permanent_signatures.add(sig)
                except Exception:
                    continue

        # 3. Cooldown rule applied per catalog video.
        #    Block IF (shipped < 14d ago) OR (≥30 views accrued in last 14d).
        SHIP_FLOOR_DAYS    = 14
        ACTIVE_WINDOW_DAYS = 14
        ACTIVE_THRESHOLD   = 30  # views in the active-window = "still pulling traffic"

        try:
            from signals import load_own_catalog as _load_own_cat
            _own_cat = _load_own_cat() or []
        except Exception:
            _own_cat = []

        # Build a per-video-id "views accrued in last 14d" map from REACH_HISTORY.
        # Diff = (latest snapshot views) - (oldest snapshot views in last 21d window).
        #        21d gives us a buffer for irregular daily captures.
        views_in_window = {}  # video_id → int
        reach_path = _DD / "REACH_HISTORY.csv"
        if reach_path.exists():
            from collections import defaultdict as _dd
            from datetime import timedelta as _td
            window_start = today - _td(days=ACTIVE_WINDOW_DAYS + 7)
            per_vid = _dd(list)  # video_id → [(capture_date, views), ...]
            with open(reach_path) as f:
                for row in _csv.DictReader(f):
                    try:
                        cd = _date.fromisoformat(row["capture_date"])
                        if cd >= window_start:
                            per_vid[row["video_id"]].append((cd, int(row["views"] or 0)))
                    except Exception:
                        continue
            for vid_id, snaps in per_vid.items():
                snaps.sort()
                if len(snaps) >= 2:
                    views_in_window[vid_id] = max(0, snaps[-1][1] - snaps[0][1])
                else:
                    views_in_window[vid_id] = snaps[0][1]  # only one capture — treat as accrued

        _STOPS = {"music", "for", "the", "with", "to", "of", "and", "your",
                  "you", "this", "that", "in", "on", "at", "an", "a"}
        for _vid in _own_cat:
            _title = (_vid.get("title") or "").lower()
            _vid_id = _vid.get("video_id", "")
            _pub = _vid.get("publish_date")
            _days_since = (today - _pub).days if hasattr(_pub, "year") else 999
            _v14 = views_in_window.get(_vid_id, _vid.get("views") or 0)

            in_floor = _days_since < SHIP_FLOOR_DAYS
            still_active = _v14 >= ACTIVE_THRESHOLD
            if not (in_floor or still_active):
                continue  # cooled-off video → theme refresh-eligible

            _title_tokens = {w.strip("?!,.:;") for w in _title.replace("|", " ").split() if len(w) >= 3}
            for _problem in PROBLEM_HOOKS:
                _pkw = _problem["kw"].lower()
                if _pkw in cooldown_blocks_meta:
                    continue
                _ptokens = [t for t in _pkw.split() if len(t) >= 3 and t not in _STOPS]
                if not _ptokens:
                    continue
                if all(any(pt in tt or tt in pt for tt in _title_tokens) for pt in _ptokens):
                    if in_floor:
                        _reason = f"shipped {_days_since}d ago (cooldown floor {SHIP_FLOOR_DAYS}d)"
                    else:
                        _reason = f"still active ({_v14} views last {ACTIVE_WINDOW_DAYS}d)"
                    cooldown_blocks_meta[_pkw] = {
                        "reason":      _reason,
                        "video_title": _vid.get("title", ""),
                        "video_id":    _vid_id,
                        "days_since":  _days_since,
                        "views_14d":   _v14,
                    }

        if parked_problems or permanent_signatures or cooldown_blocks_meta:
            cooldown_keys = set(cooldown_blocks_meta.keys())
            def _filter(c):
                comp = c["components"]
                pkw = comp["problem"]["kw"].lower()
                if pkw in parked_problems:
                    return False
                if pkw in cooldown_keys:
                    return False
                if _sig_from_components(comp) in permanent_signatures:
                    return False
                return True
            candidates = [c for c in candidates if _filter(c)]
    except Exception:
        pass

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
    from signals import instrument_last_used, hz_last_used, raga_last_used, wave_last_used
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

    # Cross-bucket constraint: top 3 must have 3 different problem keywords
    picked_problems = set()
    deduped = []
    filled_buckets = set()
    for bucket_name in ["competitor", "niche", "moonshot"]:
        for c in buckets[bucket_name]:
            prob = c["components"]["problem"]["kw"]
            if prob in picked_problems:
                continue
            picked_problems.add(prob)
            c["bucket_filled"] = bucket_name      # original bucket (not backfilled)
            c["backfilled"]    = False
            deduped.append(c)
            filled_buckets.add(bucket_name)
            break

    # If a bucket was empty, backfill with next best from any bucket and tag it
    empty_buckets = [b for b in ("competitor", "niche", "moonshot") if b not in filled_buckets]
    if len(deduped) < top_n:
        remaining_problems = picked_problems
        for c in candidates:
            prob = c["components"]["problem"]["kw"]
            if prob in remaining_problems:
                continue
            remaining_problems.add(prob)
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
    "Tanpura":  ["tanpura", "tanpura drone", "tanpura meditation"],
    "Sitar":    ["sitar", "sitar music", "sitar meditation"],
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

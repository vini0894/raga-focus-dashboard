"""
Raga Focus — Pipeline Config

DATA (which phrases exist + their VidIQ scores) lives in:
    raga-focus-dashboard/data/keyword_bank.csv
    (loaded via pipeline/keyword_bank.py)

CODE (musicology, rules, scoring weights, tonal-fit matrix) lives here.

Update this file when:
- Static musicology refines (raga time-of-day, Hz meaning, wave outcomes)
- Tonal-suitability matrix changes
- Kill list grows
- Scoring rules change

Update keyword_bank.csv (NOT this file) when:
- A new VidIQ score arrives
- A new keyword is validated / invalidated
"""

from keyword_bank import load_by_slot


# ═════════════════════════════════════════════════════════
# STATIC MUSICOLOGY — keyed on phrase; doesn't change with VidIQ scores
# ═════════════════════════════════════════════════════════

# Hand-curated creative copy for known problem hooks.
# Keys are lowercase phrases (matching the `phrase` column in keyword_bank.csv).
# `seo_phrase` = title-ready capitalized form (handles ADHD, Hz, etc.)
# `question`   = thumbnail overlay + B-variant title hook
# `outcome`    = C-variant imperative hook
PROBLEM_HOOK_META = {
    # action_phrase = slot-2 verb phrase for Variant A: "{seo_phrase} | {action_phrase} with {Instrument} | 1 Hour"
    # question      = slot-1 hook for Variant B:       "{question} | {outcome_short} with Raga {Raga} | 1 Hour"
    # outcome_short = slot-2 for Variant B (≤ 4 words, imperative)
    "stress relief music":    {"seo_phrase": "Stress Relief Music",       "action_phrase": "Release Stress",        "question": "Stressed Out?",            "outcome": "Calm Stress Now",            "outcome_short": "Release Stress"},
    "deep relaxation music":  {"seo_phrase": "Deep Relaxation Music",     "action_phrase": "Find Deep Calm",        "question": "Feeling Overwhelmed?",     "outcome": "Reach Deep Relaxation",      "outcome_short": "Find Deep Calm"},
    "overthinking music":     {"seo_phrase": "Overthinking Music",        "action_phrase": "Calm Down",             "question": "Can't Keep Calm?",         "outcome": "Calm an Overthinking Mind",  "outcome_short": "Stop Overthinking"},
    "meditation for anxiety": {"seo_phrase": "Meditation for Anxiety",    "action_phrase": "Find Peace",            "question": "Morning Anxiety?",         "outcome": "Release Anxiety",            "outcome_short": "Release Anxiety"},
    "unwind music":           {"seo_phrase": "Unwind Music",              "action_phrase": "Unwind Slowly",         "question": "Can't Switch Off?",        "outcome": "Unwind After Work",          "outcome_short": "Let It Go"},
    "deep rest music":        {"seo_phrase": "Deep Rest Music",           "action_phrase": "Find Stillness",        "question": "Need Deep Rest?",          "outcome": "Reach Deep Rest",            "outcome_short": "Find Stillness"},
    "deep meditation":        {"seo_phrase": "Deep Meditation Music",     "action_phrase": "Go Deeper",             "question": "Can't Meditate?",          "outcome": "Enter Deep Meditation",      "outcome_short": "Enter Deep Calm"},
    "nervous system reset":   {"seo_phrase": "Nervous System Reset",      "action_phrase": "Reset and Restore",     "question": "Nervous System Overload?", "outcome": "Reset Your Nervous System",  "outcome_short": "Reset Your System"},
    "racing thoughts music":  {"seo_phrase": "Racing Thoughts Music",     "action_phrase": "Still Your Mind",       "question": "Mind Racing at Night?",    "outcome": "Stop Racing Thoughts",       "outcome_short": "Still Your Mind"},
    "emotional overwhelm":    {"seo_phrase": "Emotional Overwhelm Music", "action_phrase": "Find Relief",           "question": "Emotionally Overwhelmed?", "outcome": "Release Emotional Overwhelm","outcome_short": "Find Relief"},
    "heavy heart music":      {"seo_phrase": "Heavy Heart Music",         "action_phrase": "Find Comfort",          "question": "Heavy Heart?",             "outcome": "Heal a Heavy Heart",         "outcome_short": "Find Comfort"},
    "vagus nerve music":      {"seo_phrase": "Vagus Nerve Music",         "action_phrase": "Reset and Restore",     "question": "Vagus Nerve Stuck?",       "outcome": "Reset Your Vagus Nerve",     "outcome_short": "Reset Your Nerve"},
    "sunday anxiety":         {"seo_phrase": "Sunday Anxiety Music",      "action_phrase": "Find Sunday Calm",      "question": "Sunday Night Dread?",      "outcome": "Calm Sunday Anxiety",        "outcome_short": "Calm Sunday Dread"},
    "dopamine reset":         {"seo_phrase": "Dopamine Reset Music",      "action_phrase": "Reset Your Mind",       "question": "Dopamine Burnt Out?",      "outcome": "Reset Your Dopamine",        "outcome_short": "Reset Your Mind", "competitor_proven": "Raga Heal 23K (Apr 20)"},
}

# Instrument display name + aliases for n-gram detection in titles
INSTRUMENT_META = {
    "bansuri":  {"name": "Bansuri",  "aliases": ["bansuri", "bamboo flute"]},
    "sarangi":  {"name": "Sarangi",  "aliases": ["sarangi"]},
    "dilruba":  {"name": "Dilruba",  "aliases": ["dilruba"]},
    "veena":    {"name": "Veena",    "aliases": ["veena"]},
    "sarod":    {"name": "Sarod",    "aliases": ["sarod"]},
    "santoor":  {"name": "Santoor",  "aliases": ["santoor", "santur"]},
    "esraj":    {"name": "Esraj",    "aliases": ["esraj"]},
    "tanpura":    {"name": "Tanpura",    "aliases": ["tanpura"]},
    "sitar":      {"name": "Sitar",      "aliases": ["sitar"]},  # ⚠️ saturated
    "swarmandal": {"name": "Swarmandal", "aliases": ["swarmandal", "swara mandal"]},
    "surbahar":   {"name": "Surbahar",   "aliases": ["surbahar"]},  # bass sitar — #1 performer (1,370 views)
}

# Hz semantic meaning + category
HZ_META = {
    "7.83hz":{"display": "7.83Hz", "category": "schumann resonance","meaning": "Earth's natural electromagnetic frequency / grounding"},
    "40hz":  {"display": "40Hz",   "category": "gamma",             "meaning": "focus / cognitive performance / gamma entrainment"},
    "174hz": {"display": "174Hz",  "category": "ancient healing",   "meaning": "pain relief / grounding"},
    "432hz": {"display": "432Hz",  "category": "classic healing",   "meaning": "universal harmony"},
    "528hz": {"display": "528Hz",  "category": "love/DNA repair",   "meaning": "DNA repair / love"},
    "639hz": {"display": "639Hz",  "category": "relationships",     "meaning": "connection / harmonious relationships"},
    "741hz": {"display": "741Hz",  "category": "awakening",         "meaning": "detox / problem solving"},
    "963hz": {"display": "963Hz",  "category": "pineal gland",      "meaning": "spiritual awakening / oneness"},
}

# Raga time-of-day + mood (Hindustani classical convention)
RAGA_META = {
    "yaman":      {"name": "Yaman",      "time": "evening",      "mood": "peace"},
    "bhairavi":   {"name": "Bhairavi",   "time": "morning",      "mood": "devotional"},
    "bhupali":    {"name": "Bhupali",    "time": "evening",      "mood": "serenity"},
    "darbari":    {"name": "Darbari",    "time": "night",        "mood": "grandeur"},
    "malkauns":   {"name": "Malkauns",   "time": "midnight",     "mood": "depth"},
    "kafi":       {"name": "Kafi",       "time": "late evening", "mood": "romance"},
    "puriya":     {"name": "Puriya",     "time": "evening",      "mood": "pathos"},
    "bhimpalasi": {"name": "Bhimpalasi", "time": "afternoon",    "mood": "longing"},
    "bilawal":    {"name": "Bilawal",    "time": "morning",      "mood": "cheerful"},
    "hamir":      {"name": "Hamir",      "time": "late evening", "mood": "majestic"},
    "todi":       {"name": "Todi",       "time": "morning",      "mood": "yearning"},  # claimed by Raga Heal Apr 24
    "chandra":    {"name": "Chandra",    "time": "night",        "mood": "lunar"},     # claimed by Raga Heal Mar 20
    "bhairav":    {"name": "Bhairav",    "time": "morning",      "mood": "austere"},   # competitor using — add to bank
}

# Wave outcome-text + which problems each wave fits
WAVE_META = {
    "alpha":    {"display": "Alpha",    "outcome": "Calm Session",         "matches": ["overthinking", "anxiety", "stress", "racing"]},
    "delta":    {"display": "Delta",    "outcome": "Deep Rest Session",    "matches": ["sleep", "rest", "unwind"]},
    "theta":    {"display": "Theta",    "outcome": "Meditation Session",   "matches": ["meditation", "creativity", "intuition"]},
    "binaural": {"display": "Binaural", "outcome": "Nervous System Reset", "matches": ["nervous system", "vagus", "reset"]},
}


# ═════════════════════════════════════════════════════════
# CSV BRIDGE — build the legacy list shapes from keyword_bank.csv + META
# Existing scoring.py / signals.py / etc. import these names. Same shape, new source.
# ═════════════════════════════════════════════════════════

# Cluster-based copy fallback for problem keywords not in PROBLEM_HOOK_META.
# Matched by substring — first matching cluster wins.
_CLUSTER_DEFAULTS = {
    "sleep":      {"action_phrase": "Drift to Sleep",   "question": "Can't Fall Asleep?",    "outcome_short": "Drift to Sleep"},
    "insomnia":   {"action_phrase": "Drift to Sleep",   "question": "Can't Fall Asleep?",    "outcome_short": "Find Sleep"},
    "rest":       {"action_phrase": "Find Stillness",   "question": "Need Deep Rest?",        "outcome_short": "Find Stillness"},
    "nostalgia":  {"action_phrase": "Feel the Feeling", "question": "Feeling Nostalgic?",     "outcome_short": "Feel the Feeling"},
    "healing":    {"action_phrase": "Start Healing",    "question": "Need Healing?",          "outcome_short": "Find Healing"},
    "anxiety":    {"action_phrase": "Find Peace",       "question": "Feeling Anxious?",       "outcome_short": "Find Peace"},
    "stress":     {"action_phrase": "Release Stress",   "question": "Feeling Stressed?",      "outcome_short": "Release Stress"},
    "overthink":  {"action_phrase": "Calm Down",        "question": "Can't Stop Overthinking?","outcome_short": "Stop Overthinking"},
    "focus":      {"action_phrase": "Find Focus",       "question": "Can't Focus?",           "outcome_short": "Find Focus"},
    "meditation": {"action_phrase": "Go Deeper",        "question": "Need Meditation?",       "outcome_short": "Go Deeper"},
    "unwind":     {"action_phrase": "Unwind Slowly",    "question": "Can't Unwind?",          "outcome_short": "Let It Go"},
    "emotional":  {"action_phrase": "Let It Out",       "question": "Feeling Emotional?",     "outcome_short": "Let It Out"},
    "calm":       {"action_phrase": "Find Calm",        "question": "Need Calm?",             "outcome_short": "Find Calm"},
    "relax":      {"action_phrase": "Relax Deeply",     "question": "Need to Relax?",         "outcome_short": "Relax Deeply"},
    "comfort":    {"action_phrase": "Find Comfort",     "question": "Need Comfort?",          "outcome_short": "Find Comfort"},
    "grounding":  {"action_phrase": "Find Ground",      "question": "Feeling Ungrounded?",    "outcome_short": "Find Ground"},
    "detox":      {"action_phrase": "Clear Your Mind",  "question": "Need a Reset?",          "outcome_short": "Clear Your Mind"},
    "morning":    {"action_phrase": "Start Fresh",      "question": "Sluggish Morning?",      "outcome_short": "Start Fresh"},
    "dopamine":   {"action_phrase": "Reset Your Mind",  "question": "Dopamine Depleted?",     "outcome_short": "Reset Your Mind"},
    "burnout":    {"action_phrase": "Recover Slowly",   "question": "Burnt Out?",             "outcome_short": "Start Recovery"},
    "homesick":   {"action_phrase": "Feel at Home",     "question": "Feeling Homesick?",      "outcome_short": "Feel at Home"},
    "missing":    {"action_phrase": "Feel the Warmth",  "question": "Missing Someone?",       "outcome_short": "Feel Close Again"},
    "lost":       {"action_phrase": "Find Your Way",    "question": "Feeling Lost?",           "outcome_short": "Find Your Way"},
    "heavy":      {"action_phrase": "Find Comfort",     "question": "Heart Feeling Heavy?",    "outcome_short": "Find Comfort"},
    "grief":      {"action_phrase": "Find Peace",       "question": "Carrying Grief?",         "outcome_short": "Find Peace"},
    "lonely":     {"action_phrase": "Feel Less Alone",  "question": "Feeling Lonely?",         "outcome_short": "Feel Less Alone"},
    "nervous":    {"action_phrase": "Reset and Restore","question": "Nervous System Overload?","outcome_short": "Reset Your System"},
    "vagus":      {"action_phrase": "Reset and Restore","question": "Vagus Nerve Stuck?",     "outcome_short": "Reset Your Nerve"},
}


def _cluster_defaults(kw_lower):
    """Return cluster-based copy defaults for keywords not in PROBLEM_HOOK_META."""
    for cluster_key, defaults in _CLUSTER_DEFAULTS.items():
        if cluster_key in kw_lower:
            return defaults
    return {}


def _build_problem_hooks():
    out = []
    for r in load_by_slot("problem"):
        kw = r["phrase"]
        meta = PROBLEM_HOOK_META.get(kw, {})
        cluster = _cluster_defaults(kw)
        seo = meta.get("seo_phrase") or kw.title()
        # Merge: PROBLEM_HOOK_META > cluster defaults > generic fallback
        action_default = cluster.get("action_phrase") or " ".join(w for w in seo.split() if w.lower() != "music") or seo
        q_default      = cluster.get("question",      seo + "?")
        os_default     = cluster.get("outcome_short", action_default)
        out.append({
            "kw":            kw,
            "seo_phrase":    seo,
            "action_phrase": meta.get("action_phrase", action_default),
            "question":      meta.get("question",      q_default),
            "outcome":       meta.get("outcome",       seo),
            "outcome_short": meta.get("outcome_short", os_default),
            "vidiq_score":   r["vidiq_score"],
            "vidiq_comp":    r["vidiq_comp"],
            **({"competitor_proven": meta["competitor_proven"]} if "competitor_proven" in meta else {}),
        })
    return out


def _build_instruments():
    """Build from INSTRUMENT_META (canonical). keyword_bank.csv supplies scores only."""
    bank = {r["phrase"]: r for r in load_by_slot("instrument")}
    out = []
    for kw, meta in INSTRUMENT_META.items():
        r = bank.get(kw, {})
        out.append({
            "name":        meta["name"],
            "vidiq_score": r.get("vidiq_score"),
            "vidiq_comp":  r.get("vidiq_comp") or "Unknown",
            "aliases":     meta["aliases"],
        })
    return out


def _build_frequencies():
    """Build from HZ_META (canonical). keyword_bank.csv supplies scores only."""
    bank = {r["phrase"]: r for r in load_by_slot("hz")}
    out = []
    for kw, meta in HZ_META.items():
        r = bank.get(kw, {})
        out.append({
            "hz":          meta["display"],
            "category":    meta["category"],
            "meaning":     meta["meaning"],
            "vidiq_score": r.get("vidiq_score"),
            "vidiq_comp":  r.get("vidiq_comp"),
        })
    return out


def _build_ragas():
    """Build from RAGA_META (canonical). keyword_bank.csv supplies scores only."""
    bank = {r["phrase"]: r for r in load_by_slot("raga")}
    out = []
    for kw, meta in RAGA_META.items():
        r = bank.get(kw, {})
        out.append({
            "name":        meta["name"],
            "time":        meta["time"],
            "mood":        meta["mood"],
            "vidiq_score": r.get("vidiq_score"),
            "vidiq_comp":  r.get("vidiq_comp"),
        })
    return out


def _build_wave_frames():
    """Build from WAVE_META (canonical). keyword_bank.csv supplies scores only."""
    bank = {r["phrase"]: r for r in load_by_slot("wave")}
    out = []
    for kw, meta in WAVE_META.items():
        r = bank.get(kw, {})
        out.append({
            "wave":        meta["display"],
            "outcome":     meta["outcome"],
            "matches":     meta["matches"],
            "vidiq_score": r.get("vidiq_score"),
            "vidiq_comp":  r.get("vidiq_comp"),
        })
    return out


PROBLEM_HOOKS = _build_problem_hooks()
INSTRUMENTS   = _build_instruments()
FREQUENCIES   = _build_frequencies()
RAGAS         = _build_ragas()
WAVE_FRAMES   = _build_wave_frames()

# ═════════════════════════════════════════════════════════
# TONAL SUITABILITY MATRIX — which instruments fit which problem moods
# Each problem keyword maps to: {"primary": [...], "secondary": [...], "avoid": [...]}
# ═════════════════════════════════════════════════════════
TONAL_FIT = {
    "overthinking": {
        "primary":   ["Sarangi", "Bansuri"],
        "secondary": ["Dilruba", "Esraj"],
        "avoid":     ["Sitar", "Tabla", "Shehnai"],
    },
    "anxiety": {
        "primary":   ["Sarangi", "Bansuri", "Dilruba"],
        "secondary": ["Veena", "Esraj", "Swarmandal"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
    "sleep": {
        "primary":   ["Bansuri", "Dilruba", "Surbahar"],
        "secondary": ["Tanpura", "Veena", "Swarmandal", "Sarangi"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
    "stress": {
        "primary":   ["Bansuri", "Veena"],
        "secondary": ["Sarangi", "Sarod", "Swarmandal", "Surbahar"],
        "avoid":     ["Tabla", "Shehnai"],
    },
    "meditation": {
        "primary":   ["Veena", "Bansuri", "Tanpura", "Surbahar"],
        "secondary": ["Sarangi", "Swarmandal"],
        "avoid":     ["Tabla", "Shehnai"],
    },
    "nervous system": {
        "primary":   ["Bansuri", "Sarangi"],
        "secondary": ["Veena", "Tanpura", "Swarmandal"],
        "avoid":     ["Shehnai", "Tabla"],
    },
    "emotional": {
        "primary":   ["Sarangi", "Dilruba", "Esraj"],
        "secondary": ["Sarod"],
        "avoid":     ["Sitar", "Bansuri"],  # too light
    },
    "focus": {
        "primary":   ["Sitar", "Santoor"],
        "secondary": ["Bansuri"],
        "avoid":     ["Sarangi", "Dilruba"],
    },
    "morning": {
        "primary":   ["Sitar", "Bansuri"],
        "secondary": ["Santoor"],
        "avoid":     ["Dilruba", "Sarangi"],  # melancholy
    },
    "unwind": {
        "primary":   ["Bansuri", "Dilruba"],
        "secondary": ["Sarangi"],
        "avoid":     ["Sitar", "Shehnai"],
    },
    "rest": {
        "primary":   ["Bansuri", "Tanpura"],
        "secondary": ["Veena"],
        "avoid":     ["Sitar", "Shehnai"],
    },
    "dopamine": {
        "primary":   ["Bansuri", "Sarangi"],
        "secondary": ["Veena"],
        "avoid":     ["Shehnai"],
    },
    "vagus": {
        "primary":   ["Bansuri", "Veena"],
        "secondary": ["Tanpura", "Sarangi"],
        "avoid":     ["Shehnai", "Tabla"],
    },
    "nostalgia": {
        "primary":   ["Sarangi", "Esraj"],       # bowed, vocal-like — carries longing
        "secondary": ["Dilruba", "Sarod"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
    "insomnia": {
        "primary":   ["Bansuri", "Surbahar"],
        "secondary": ["Tanpura", "Veena", "Dilruba"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
    "homesick": {
        "primary":   ["Sarangi", "Esraj"],
        "secondary": ["Dilruba", "Sarod"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
}

# ═════════════════════════════════════════════════════════
# KILL LIST — phrases NEVER to use in titles
# ═════════════════════════════════════════════════════════
KILL_PHRASES = [
    "quiet your mind",
    "too much screen time",
    "digital detox",
    "restless mind",
    "can't switch off",
    "evening raga",
    "40hz gamma",
    "calming dilruba raga to quiet your mind",
]

# ═════════════════════════════════════════════════════════
# COMPETITORS — RSS channel IDs
# ═════════════════════════════════════════════════════════
COMPETITORS = {
    "Raga Heal":            "UCnCW6fiX-6Jykcl2NBQBIbQ",
    "Shanti Instrumentals": "UCGVIda_EdGStdRAFMBh6LAA",
}

# Our own channel — for live catalog awareness (RSS has freshest data)
RAGA_FOCUS_CHANNEL_ID = "UCtNMs5bRntzvvzjSrTJIo_Q"

# ═════════════════════════════════════════════════════════
# CONCLUDED A/B TESTS — manual log of YouTube title-test outcomes
# Append every concluded A/B test result here. Pipeline uses these
# as the strongest signal for hook-template recommendation.
# ═════════════════════════════════════════════════════════
KNOWN_AB_RESULTS = [
    {
        "video_id":      "5UGTuyNHHHE",
        "concluded_on":  "2026-04-25",
        "winner":        "A_seo",
        "winner_title":  "Stress Relief Music | Deep Meditation with Veena Raga & 432Hz | 1 Hour",
        "loser_title":   "Mind Too Restless? | Raga Yaman Veena | 432Hz Stillness Session | 1 Hour",
        "win_margin":    0.75,   # SEO won by 75% (3:1)
        "notes":         "Decisive SEO win on identical music + same audience. Validates SEO-led title + question-on-thumbnail pattern.",
    },
    {
        "video_id":      "",  # native YouTube Test & Compare; backfill if needed
        "concluded_on":  "2026-04-27",
        "winner":        "A_seo",
        "winner_title":  "Calm Your Mind | Veena Healing Music | 1 hour",
        "loser_title":   "Feeling Lost? | Veena & 7.83Hz Schumann Resonance | 1 Hour Calming Music",
        "win_margin":    0.677,  # winner had 67.7% watch-time share vs 32.3%
        "notes":         "2nd consistent SEO-led win. SHORTER title (41 chars) beat the longer 80-char version. Key insight: dropping middle-slot Hz/Schumann stuffing INCREASED clicks. Validates user hypothesis — lean validated-keyword titles outperform stuffed titles in calm/healing niche.",
    },
]

# ═════════════════════════════════════════════════════════
# RULES (from playbook §9)
# ═════════════════════════════════════════════════════════
RULES = {
    "title_min_chars":          35,
    "title_max_chars":          88,
    "own_recency_block_days":   5,    # hard-block instrument if used in last 5d
    "competitor_recency_days":  5,    # penalty if competitor used in last 5d
    "trending_window_days":     30,   # instrument must appear in competitor feed this recent
    "min_vidiq_score":          60,   # below this = kill
    "rescue_min_avd_pct":       20,   # AVD% threshold for rescue candidates
    "rescue_max_ctr_pct":       2.0,  # CTR threshold for rescue candidates
    "rescue_max_impressions":   1500, # impressions threshold for rescue candidates
}

# ═════════════════════════════════════════════════════════
# SCORING WEIGHTS
# ═════════════════════════════════════════════════════════
WEIGHTS = {
    "problem_vidiq_boost_per_pt":   +2,   # per point above 60
    "problem_claimed_by_us":        -50,  # hard penalty
    "problem_needs_vidiq":          -15,  # untested keyword
    "problem_competitor_proven":    +10,  # competitor succeeded with similar
    "tonal_primary":                +20,
    "tonal_secondary":              +8,
    "tonal_avoid":                 -100,  # hard disqualify
    "instrument_vidiq_very_low":    +20,
    "instrument_vidiq_low":         +10,
    "instrument_vidiq_med":          +3,
    "instrument_vidiq_high":         -5,
    "instrument_competitor_unique": +15,  # no competitor used in last 30d
    "instrument_competitor_heavy":  -20,  # competitor used ≥3x in last 30d
    "instrument_used_last_5d":    -1000,  # hard skip
    "competitor_used_last_5d":      -15,
    "hz_used_last_7d":              -12,
    "raga_used_last_7d":            -10,
    "wave_used_last_7d":             -8,
    "wave_problem_match":           +12,
}


# ═════════════════════════════════════════════════════════
# SLOT ALTERNATIVES — used by regenerate.py when a slot fails VidIQ validation
# ═════════════════════════════════════════════════════════

# Wave + outcome alternates — if "Alpha Wave Calm Session" fails, try these
WAVE_OUTCOME_ALTS = {
    "Alpha Wave Calm Session": [
        "Alpha Wave Meditation",
        "10Hz Alpha Music",
        "Calm Mind Session",
        "Anxiety Relief Session",
        "Alpha Wave Relaxation",
    ],
    "Delta Wave Sleep Session": [
        "Delta Wave Deep Rest",
        "2Hz Delta Music",
        "Deep Sleep Session",
        "Insomnia Relief Session",
        "Delta Wave Meditation",
    ],
    "Theta Wave Meditation Session": [
        "Theta Wave Meditation",
        "6Hz Theta Music",
        "Deep Meditation Session",
        "Creative Flow Session",
    ],
    "Binaural Wave Nervous System Reset": [
        "Nervous System Reset",
        "Vagus Nerve Reset",
        "Polyvagal Reset Session",
    ],
}

# Raga substitutes by mood-bucket
RAGA_BY_MOOD = {
    "evening_serene":     ["Bhupali", "Yaman", "Hamir"],
    "evening_pathos":     ["Puriya", "Marwa", "Puriya Dhanashree"],
    "night_deep":         ["Darbari", "Malkauns", "Bageshri"],
    "night_lunar":        ["Chandra", "Chandrakauns"],
    "morning_calm":       ["Bhairavi", "Bilawal"],
    "morning_devotional": ["Bhairavi", "Bhairav"],
    "afternoon_longing":  ["Bhimpalasi", "Multani", "Madhuvanti"],
    "late_evening":       ["Kafi", "Khamaj"],
    "all_purpose_calm":   ["Yaman", "Bhupali", "Bhairavi"],
}

# Hz substitutes by intent bucket
HZ_BY_INTENT = {
    "classic_healing":     ["432Hz", "528Hz"],
    "ancient_healing":     ["174Hz", "417Hz"],
    "relationships":       ["639Hz"],
    "awakening":           ["741Hz"],
    "pineal":              ["963Hz"],
    "sleep_default":       ["432Hz", "174Hz", "528Hz"],
    "anxiety_default":     ["432Hz", "528Hz", "639Hz"],
    "focus_default":       ["432Hz", "528Hz"],
    "meditation_default":  ["432Hz", "528Hz", "741Hz", "963Hz"],
}

# Problem keyword fallbacks — if "overthinking music" fails, try "anxiety relief music"
PROBLEM_KEYWORD_ALTS = {
    "overthinking music":     ["anxiety relief music", "racing thoughts music", "calm anxious mind music"],
    "stress relief music":    ["anxiety relief music", "deep relaxation music", "calm music for stress"],
    "deep relaxation music":  ["stress relief music", "deep rest music", "relaxation music"],
    "meditation for anxiety": ["anxiety relief music", "calm music for anxiety"],
    "deep rest music":        ["deep relaxation music", "rest music"],
    "deep meditation":        ["deep meditation music", "meditation music", "indian classical meditation"],
    "nervous system reset":   ["nervous system music", "vagus nerve reset", "polyvagal music"],
    "unwind music":           ["evening relaxation music", "wind down music"],
    "racing thoughts music":  ["overthinking music", "anxiety relief music"],
    "vagus nerve music":      ["nervous system reset", "parasympathetic music"],
    "dopamine reset":         ["digital reset music", "dopamine detox music"],
}

# Problem keyword → raga mood bucket (used when picking raga substitute)
# AND for audience-cluster saturation detection in scoring.py
PROBLEM_TO_RAGA_MOOD = {
    "overthinking":     "evening_serene",
    "anxiety":          "evening_serene",
    "stress":           "evening_serene",
    "relaxation":       "evening_serene",   # deep relaxation = same audience as stress
    "deep relax":       "evening_serene",
    "calm":             "evening_serene",
    "racing":           "evening_serene",
    "meditation":       "evening_serene",   # changed from all_purpose — same audience as stress/anxiety
    "deep meditation":  "evening_serene",
    "nervous system":   "evening_serene",
    "vagus":            "evening_serene",
    "dopamine":         "evening_serene",
    "sleep":            "night_deep",
    "asleep":           "night_deep",
    "insomnia":         "night_deep",
    "rest":             "night_deep",
    "deep rest":        "night_deep",
    "unwind":           "late_evening",
    "morning":          "morning_calm",
    "cortisol":         "morning_calm",
    "emotional":        "evening_pathos",
    "overwhelm":        "evening_pathos",   # emotional overwhelm
    "heavy heart":      "evening_pathos",
    "grief":            "evening_pathos",
    "heartbreak":       "evening_pathos",
    "screen time":      "late_evening",
    "screen":           "late_evening",
}

# ═════════════════════════════════════════════════════════
# THUMBNAIL TEXT BANK — creative copy keyed by problem-bucket substring
# Used by thumbnail_text.py to generate Variant A/B/C overlay phrases.
# Built from competitor analysis (Raga Heal, Shanti) + own-channel patterns.
# ═════════════════════════════════════════════════════════
PROBLEM_THUMBNAIL_TEXT = {
    "overthinking": {
        "question": ["MIND RACING?", "CAN'T STOP THINKING?", "OVERTHINKING?"],
        "outcome":  ["QUIET YOUR MIND", "STOP OVERTHINKING", "CALM YOUR MIND"],
        "identity": ["OVERTHINKER?", "ANXIOUS MIND", "RACING MIND"],
    },
    "anxiety": {
        "question": ["ANXIOUS?", "PANIC RISING?", "FEELING ANXIOUS?"],
        "outcome":  ["CALM ANXIETY", "RELEASE ANXIETY", "EASE THE PANIC"],
        "identity": ["ANXIOUS MIND", "RESTLESS HEART", "ON EDGE?"],
    },
    "sleep": {
        "question": ["CAN'T FALL ASLEEP?", "STILL AWAKE?", "INSOMNIA?"],
        "outcome":  ["FALL ASLEEP NOW", "DEEP SLEEP TONIGHT", "SLEEP DEEPLY"],
        "identity": ["SLEEPLESS NIGHT", "TIRED BUT WIRED", "3AM AWAKE"],
    },
    "stress": {
        "question": ["STRESSED OUT?", "BURNT OUT?", "OVERWHELMED?"],
        "outcome":  ["RELEASE STRESS", "MELT THE TENSION", "DEEP RELIEF"],
        "identity": ["STRESS BUILD-UP", "HEAVY DAY", "TENSION HOLDING"],
    },
    "rest": {
        "question": ["NEED REST?", "EXHAUSTED?", "DEPLETED?"],
        "outcome":  ["DEEP REST NOW", "RESTORE YOUR ENERGY", "TRUE REST"],
        "identity": ["DEPLETED?", "RUNNING ON EMPTY", "BURNT OUT"],
    },
    "meditation": {
        "question": ["READY TO MEDITATE?", "NEED STILLNESS?", "SEEKING CALM?"],
        "outcome":  ["GO DEEPER", "REACH STILLNESS", "DROP IN"],
        "identity": ["INNER STILLNESS", "MEDITATION HOUR", "SACRED SPACE"],
    },
    "nervous system": {
        "question": ["NERVOUS SYSTEM ON?", "FIGHT-OR-FLIGHT?", "DYSREGULATED?"],
        "outcome":  ["RESET YOUR SYSTEM", "REGULATE NOW", "RETURN TO CALM"],
        "identity": ["NS OVERLOAD", "WIRED & TIRED", "STUCK IN ALERT"],
    },
    "vagus": {
        "question": ["VAGUS STUCK?", "CAN'T DOWN-REGULATE?", "STILL ACTIVATED?"],
        "outcome":  ["TONE YOUR VAGUS", "DOWN-REGULATE NOW", "POLYVAGAL RESET"],
        "identity": ["DYSREGULATED", "STUCK IN STRESS", "FROZEN STATE"],
    },
    "emotional": {
        "question": ["HEAVY HEART?", "EMOTIONAL DAY?", "GRIEF RISING?"],
        "outcome":  ["RELEASE THE WEIGHT", "FEEL & RELEASE", "MELT IT OPEN"],
        "identity": ["GRIEVING HEART", "TENDER PLACE", "HOLDING IT IN"],
    },
    "unwind": {
        "question": ["CAN'T SWITCH OFF?", "WORK MIND ON?", "STILL WIRED?"],
        "outcome":  ["UNWIND NOW", "SHIFT TO REST", "DROP THE DAY"],
        "identity": ["WORK BRAIN", "WOUND UP", "EVENING WIND-DOWN"],
    },
    "racing": {
        "question": ["MIND RACING?", "THOUGHTS WON'T STOP?", "RACING THOUGHTS?"],
        "outcome":  ["CALM THE RACE", "QUIET THE NOISE", "STILL THE MIND"],
        "identity": ["RACING MIND", "THOUGHT LOOPS", "STORM IN HEAD"],
    },
    "morning anxiety": {
        "question": ["MORNING ANXIETY?", "WAKING UP TENSE?", "ROUGH MORNING?"],
        "outcome":  ["EASE INTO DAY", "GROUND YOUR MORNING", "CALM WAKE-UP"],
        "identity": ["MORNING DREAD", "TENSE DAYBREAK", "WAKING ANXIOUS"],
    },
    "dopamine": {
        "question": ["DOPAMINE BURNT?", "NUMB OUT?", "OVERSTIMULATED?"],
        "outcome":  ["RESET DOPAMINE", "DETOX YOUR MIND", "RESTORE BALANCE"],
        "identity": ["DOPAMINE CRASH", "OVERSTIMULATED", "BURNT-OUT BRAIN"],
    },
    "breathe": {
        "question": ["WIRED?", "TOO FAST?", "CAN'T SLOW DOWN?"],
        "outcome":  ["PAUSE.", "SLOW DOWN.", "BREATHE."],
        "identity": ["RACING MIND", "TIGHT CHEST", "SHALLOW BREATH"],
    },
    "slow down": {
        "question": ["MOVING TOO FAST?", "ALWAYS RUSHING?", "CAN'T STOP?"],
        "outcome":  ["SLOW DOWN.", "EASE UP.", "BREATHE."],
        "identity": ["FAST PACED", "ALWAYS ON", "RUSHING MIND"],
    },
    "calm": {
        "question": ["WIRED?", "TENSE?", "ON EDGE?"],
        "outcome":  ["FIND CALM", "BE STILL", "SETTLE IN"],
        "identity": ["TENSE BODY", "WIRED MIND", "SEEKING CALM"],
    },
    "nostalgia": {
        "question": ["MISSING SOMEONE?", "FEELING WISTFUL?", "HOMESICK?"],
        "outcome":  ["FEEL IT FULLY", "HOLD THE MEMORY", "REMEMBER"],
        "identity": ["WISTFUL HEART", "MISSING HOME", "OLD MEMORIES"],
    },
    "homesick": {
        "question": ["MISSING HOME?", "FAR FROM FAMILY?", "FEELING ALONE?"],
        "outcome":  ["FIND COMFORT", "FEEL HELD", "GO HOME"],
        "identity": ["FAR FROM HOME", "MISSING HOME", "ACHING HEART"],
    },
    "comfort": {
        "question": ["NEED COMFORT?", "ROUGH DAY?", "NEED A HUG?"],
        "outcome":  ["FEEL HELD", "FIND COMFORT", "BE SOOTHED"],
        "identity": ["NEEDING COMFORT", "TENDER PLACE", "HEAVY HEART"],
    },
    "focus": {
        "question": ["BRAIN FOG?", "DISTRACTED?", "CAN'T FOCUS?"],
        "outcome":  ["LOCK IN", "DEEP WORK", "FOCUS UP"],
        "identity": ["FOGGY MIND", "SCATTERED", "BRAIN FOG"],
    },
    "concentration": {
        "question": ["CAN'T CONCENTRATE?", "BRAIN FOG?", "DISTRACTED?"],
        "outcome":  ["LOCK IN", "GO DEEP", "SHARPEN FOCUS"],
        "identity": ["SCATTERED MIND", "BRAIN FOG", "FOGGY DAY"],
    },
    "brain fog": {
        "question": ["BRAIN FOG?", "FOGGY HEAD?", "CAN'T THINK?"],
        "outcome":  ["CLEAR THE FOG", "THINK CLEARLY", "SHARPEN UP"],
        "identity": ["BRAIN FOG", "MENTAL HAZE", "FOGGY MIND"],
    },
    "healing": {
        "question": ["HURTING?", "READY TO HEAL?", "OPEN HEART?"],
        "outcome":  ["BEGIN HEALING", "RESTORE", "MEND"],
        "identity": ["HEALING JOURNEY", "TENDER HEART", "RAW PLACE"],
    },
    "burnout": {
        "question": ["BURNED OUT?", "DEPLETED?", "FRIED?"],
        "outcome":  ["RECOVER", "REPLENISH", "REBUILD"],
        "identity": ["BURNED OUT", "RUNNING ON EMPTY", "DEPLETED"],
    },
    "insomnia": {
        "question": ["3AM AGAIN?", "STILL AWAKE?", "INSOMNIA?"],
        "outcome":  ["DRIFT OFF", "DEEP SLEEP", "FALL ASLEEP"],
        "identity": ["INSOMNIA", "SLEEPLESS", "TIRED & WIRED"],
    },
    "grounding": {
        "question": ["UNGROUNDED?", "FLOATING?", "SCATTERED?"],
        "outcome":  ["GROUND DOWN", "ROOT IN", "ANCHOR"],
        "identity": ["UNGROUNDED", "FLOATING MIND", "DISCONNECTED"],
    },
    "detox": {
        "question": ["OVERSTIMULATED?", "PHONE FRIED?", "TOO MUCH SCREEN?"],
        "outcome":  ["DETOX NOW", "RESET", "DISCONNECT"],
        "identity": ["DIGITAL OVERLOAD", "PHONE BRAIN", "OVERSTIMULATED"],
    },
    "feel good": {
        "question": ["DRAINED?", "NEED A LIFT?", "ROUGH WEEK?"],
        "outcome":  ["FEEL GOOD.", "GET YOUR ENERGY BACK", "BOOST YOUR MOOD"],
        "identity": ["BRIGHT MORNING", "FEEL-GOOD HOUR", "GOOD VIBES"],
    },
    "positive vibes": {
        "question": ["LOW ENERGY?", "NEED A LIFT?", "MOOD DOWN?"],
        "outcome":  ["FEEL GOOD.", "LIFT YOUR MOOD", "BRIGHT START"],
        "identity": ["GOOD VIBES", "BRIGHT MORNING", "POSITIVE HOUR"],
    },
    "uplifting": {
        "question": ["NEED A LIFT?", "DRAINED?", "MOOD LOW?"],
        "outcome":  ["LIFT UP", "FEEL GOOD.", "BRIGHTEN UP"],
        "identity": ["BRIGHT MORNING", "FEEL-GOOD HOUR", "GOOD VIBES"],
    },
    "happy": {
        "question": ["NEED JOY?", "MOOD DOWN?", "ROUGH DAY?"],
        "outcome":  ["FEEL GOOD.", "FIND JOY", "LIFT YOUR MOOD"],
        "identity": ["HAPPY HOUR", "GOOD VIBES", "JOY HOUR"],
    },
    "good morning": {
        "question": ["TIRED MORNING?", "NEED ENERGY?", "ROUGH WAKE-UP?"],
        "outcome":  ["BRIGHT START", "WAKE UP HAPPY", "MORNING LIFT"],
        "identity": ["BRIGHT MORNING", "MORNING HOUR", "FRESH START"],
    },
    "energy": {
        "question": ["DRAINED?", "LOW ENERGY?", "NEED A BOOST?"],
        "outcome":  ["GET YOUR ENERGY BACK", "ENERGY BOOST", "FEEL GOOD."],
        "identity": ["LOW BATTERY", "DRAINED", "RECHARGE"],
    },
    "end of day": {
        "question": ["LONG DAY?", "BURNED OUT?", "HARD DAY?"],
        "outcome":  ["RESET YOUR EVENING", "RECHARGE", "WIND DOWN"],
        "identity": ["END OF DAY", "EVENING RESET", "AFTER WORK"],
    },
    "evening": {
        "question": ["LONG DAY?", "WORK MIND ON?", "STILL WIRED?"],
        "outcome":  ["WIND DOWN", "DROP THE DAY", "EASE INTO EVENING"],
        "identity": ["EVENING RESET", "END OF DAY", "WIND-DOWN HOUR"],
    },
    "after work": {
        "question": ["DRAINED FROM WORK?", "HARD DAY?", "STILL WIRED?"],
        "outcome":  ["UNWIND NOW", "DROP THE DAY", "RESET"],
        "identity": ["AFTER WORK", "POST-WORK", "WIND-DOWN"],
    },
    "wind down": {
        "question": ["CAN'T SWITCH OFF?", "STILL WIRED?", "WORK MIND ON?"],
        "outcome":  ["WIND DOWN.", "DROP THE DAY", "EASE INTO REST"],
        "identity": ["WIND-DOWN HOUR", "EVENING RESET", "END OF DAY"],
    },
}

# Problem keyword → Hz intent bucket
PROBLEM_TO_HZ_INTENT = {
    "overthinking":   "anxiety_default",
    "anxiety":        "anxiety_default",
    "stress":         "anxiety_default",
    "racing":         "anxiety_default",
    "sleep":          "sleep_default",
    "rest":           "sleep_default",
    "meditation":     "meditation_default",
    "nervous system": "anxiety_default",
    "vagus":          "anxiety_default",
    "morning":        "classic_healing",
    "emotional":      "ancient_healing",
    "dopamine":       "anxiety_default",
}

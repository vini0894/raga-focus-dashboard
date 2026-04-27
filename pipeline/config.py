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
    "stress relief music":    {"seo_phrase": "Stress Relief Music",       "question": "Stressed Out?",            "outcome": "Calm Stress Now"},
    "deep relaxation music":  {"seo_phrase": "Deep Relaxation Music",     "question": "Feeling Overwhelmed?",     "outcome": "Reach Deep Relaxation"},
    "overthinking music":     {"seo_phrase": "Overthinking Music",        "question": "Can't Stop Overthinking?", "outcome": "Calm an Overthinking Mind"},
    "meditation for anxiety": {"seo_phrase": "Meditation for Anxiety",    "question": "Morning Anxiety?",         "outcome": "Release Anxiety"},
    "unwind music":           {"seo_phrase": "Unwind Music",              "question": "Can't Unwind After Work?", "outcome": "Unwind After Work"},
    "deep rest music":        {"seo_phrase": "Deep Rest Music",           "question": "Can't Find Deep Rest?",    "outcome": "Reach Deep Rest"},
    "deep meditation":        {"seo_phrase": "Deep Meditation Music",     "question": "Need Deep Meditation?",    "outcome": "Enter Deep Meditation"},
    "nervous system reset":   {"seo_phrase": "Nervous System Reset",      "question": "Nervous System Overload?", "outcome": "Reset Your Nervous System"},
    "racing thoughts music":  {"seo_phrase": "Racing Thoughts Music",     "question": "Mind Racing at Night?",    "outcome": "Stop Racing Thoughts"},
    "emotional overwhelm":    {"seo_phrase": "Emotional Overwhelm Music", "question": "Emotionally Overwhelmed?", "outcome": "Release Emotional Overwhelm"},
    "heavy heart music":      {"seo_phrase": "Heavy Heart Music",         "question": "Heavy Heart?",             "outcome": "Heal a Heavy Heart"},
    "vagus nerve music":      {"seo_phrase": "Vagus Nerve Music",         "question": "Vagus Nerve Stuck?",       "outcome": "Reset Your Vagus Nerve"},
    "sunday anxiety":         {"seo_phrase": "Sunday Anxiety Music",      "question": "Sunday Night Dread?",      "outcome": "Calm Sunday Anxiety"},
    "dopamine reset":         {"seo_phrase": "Dopamine Reset Music",      "question": "Dopamine Burnt Out?",      "outcome": "Reset Your Dopamine", "competitor_proven": "Raga Heal 23K (Apr 20)"},
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
    "tanpura":  {"name": "Tanpura",  "aliases": ["tanpura"]},
    "sitar":    {"name": "Sitar",    "aliases": ["sitar"]},  # ⚠️ saturated
}

# Hz semantic meaning + category
HZ_META = {
    "7.83hz":{"display": "7.83Hz", "category": "schumann resonance","meaning": "Earth's natural electromagnetic frequency / grounding"},
    "174hz": {"display": "174Hz", "category": "ancient healing", "meaning": "pain relief / grounding"},
    "432hz": {"display": "432Hz", "category": "classic healing",  "meaning": "universal harmony"},
    "528hz": {"display": "528Hz", "category": "love/DNA repair",  "meaning": "DNA repair / love"},
    "639hz": {"display": "639Hz", "category": "relationships",    "meaning": "connection / harmonious relationships"},
    "741hz": {"display": "741Hz", "category": "awakening",        "meaning": "detox / problem solving"},
    "963hz": {"display": "963Hz", "category": "pineal gland",     "meaning": "spiritual awakening / oneness"},
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

def _build_problem_hooks():
    out = []
    for r in load_by_slot("problem"):
        kw = r["phrase"]
        meta = PROBLEM_HOOK_META.get(kw, {})
        seo = meta.get("seo_phrase") or kw.title()
        out.append({
            "kw":          kw,
            "seo_phrase":  seo,
            "question":    meta.get("question",  seo),
            "outcome":     meta.get("outcome",   seo),
            "vidiq_score": r["vidiq_score"],
            "vidiq_comp":  r["vidiq_comp"],
            **({"competitor_proven": meta["competitor_proven"]} if "competitor_proven" in meta else {}),
        })
    return out


def _build_instruments():
    out = []
    for r in load_by_slot("instrument"):
        kw = r["phrase"]
        meta = INSTRUMENT_META.get(kw, {"name": kw.title(), "aliases": [kw]})
        out.append({
            "name":        meta["name"],
            "vidiq_score": r["vidiq_score"],
            "vidiq_comp":  r["vidiq_comp"] or "Unknown",
            "aliases":     meta["aliases"],
        })
    return out


def _build_frequencies():
    out = []
    for r in load_by_slot("hz"):
        kw = r["phrase"]
        meta = HZ_META.get(kw, {"display": kw.upper(), "category": "", "meaning": ""})
        out.append({
            "hz":          meta["display"],
            "category":    meta["category"],
            "meaning":     meta["meaning"],
            "vidiq_score": r["vidiq_score"],
            "vidiq_comp":  r["vidiq_comp"],
        })
    return out


def _build_ragas():
    out = []
    for r in load_by_slot("raga"):
        kw = r["phrase"]
        meta = RAGA_META.get(kw, {"name": kw.title(), "time": "", "mood": ""})
        out.append({
            "name":        meta["name"],
            "time":        meta["time"],
            "mood":        meta["mood"],
            "vidiq_score": r["vidiq_score"],
            "vidiq_comp":  r["vidiq_comp"],
        })
    return out


def _build_wave_frames():
    out = []
    for r in load_by_slot("wave"):
        kw = r["phrase"]
        meta = WAVE_META.get(kw, {"display": kw.title(), "outcome": "Session", "matches": []})
        out.append({
            "wave":        meta["display"],
            "outcome":     meta["outcome"],
            "matches":     meta["matches"],
            "vidiq_score": r["vidiq_score"],
            "vidiq_comp":  r["vidiq_comp"],
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
        "secondary": ["Veena", "Esraj"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
    "sleep": {
        "primary":   ["Bansuri", "Dilruba", "Sarangi"],
        "secondary": ["Tanpura", "Veena"],
        "avoid":     ["Sitar", "Shehnai", "Tabla"],
    },
    "stress": {
        "primary":   ["Bansuri", "Veena"],
        "secondary": ["Sarangi", "Sarod"],
        "avoid":     ["Tabla", "Shehnai"],
    },
    "meditation": {
        "primary":   ["Veena", "Bansuri", "Tanpura"],
        "secondary": ["Sarangi"],
        "avoid":     ["Tabla", "Shehnai"],
    },
    "nervous system": {
        "primary":   ["Bansuri", "Sarangi"],
        "secondary": ["Veena", "Tanpura"],
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
    "title_min_chars":          60,
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
    "morning": {
        "question": ["MORNING ANXIETY?", "WAKING UP TENSE?", "ROUGH MORNING?"],
        "outcome":  ["EASE INTO DAY", "GROUND YOUR MORNING", "CALM WAKE-UP"],
        "identity": ["MORNING DREAD", "TENSE DAYBREAK", "WAKING ANXIOUS"],
    },
    "dopamine": {
        "question": ["DOPAMINE BURNT?", "NUMB OUT?", "OVERSTIMULATED?"],
        "outcome":  ["RESET DOPAMINE", "DETOX YOUR MIND", "RESTORE BALANCE"],
        "identity": ["DOPAMINE CRASH", "OVERSTIMULATED", "BURNT-OUT BRAIN"],
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

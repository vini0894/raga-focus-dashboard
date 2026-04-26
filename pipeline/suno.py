"""
Raga Focus — Suno prompt + production spec generator.

Calibrated against the user's actual working prompts (Apr 22 + Apr 24 videos).

Proven prompt template (comma-separated tag format, NOT flowing sentence):

    Raga {Raga} {instrument}, {use_case}, ambient Indian classical,
    tanpura drone, {melodic_structure}, {bpm} BPM, {wave} wave undercurrent,
    {phrasing_detail}, no percussion, no rhythm, {atmosphere},
    warm low-frequency hum, seamless loop, instrumental only,
    solo {instrument} with tanpura, {time_mood}, deeply calming,
    no abrupt changes

The Hz layer is post-production (tools/binaural_generator.py).
"""

# ─────────────────────────────────────────────────────────
# Per-instrument melodic structure + phrasing detail (Indian-classical specific)
# ─────────────────────────────────────────────────────────
INSTRUMENT_MELODIC = {
    "Bansuri":  "slow melodic descent, long sustained notes, gentle ornaments (meend, gamak)",
    "Sarangi":  "vocal-like phrases with long bow sustains, expressive meend slides, gamak vibrato",
    "Dilruba":  "slow mournful bowed lines, long sustained notes, expressive slides (meend)",
    "Veena":    "deep grounded plucks, long ringing decays, slow alaap-style phrasing",
    "Sarod":    "fretless plucks with sustained metallic-warm decay, expressive meends",
    "Santoor":  "crystalline hammered patterns with long shimmering decays, soft tremolos",
    "Esraj":    "lyrical bowed phrases with mournful long sustains, expressive vibrato",
    "Tanpura":  "rich harmonic drone with subtle shimmering overtones, sustained cycles",
    "Sitar":    "sparse plucked notes with 8-second reverb tails, slow alaap-style movement",
}

# ─────────────────────────────────────────────────────────
# Raga → traditional time-of-day mood (matches user's "evening to midnight mood")
# ─────────────────────────────────────────────────────────
RAGA_TIME_MOOD = {
    "Yaman":      "evening to midnight mood",
    "Bhairavi":   "early morning mood",
    "Bhupali":    "evening mood",
    "Darbari":    "late night mood",
    "Malkauns":   "midnight mood",
    "Kafi":       "late evening mood",
    "Puriya":     "evening mood",
    "Bhimpalasi": "late afternoon mood",
    "Bilawal":    "morning mood",
    "Hamir":      "late evening mood",
    "Todi":       "morning mood",
    "Chandra":    "night mood",
    "Khamaj":     "late evening mood",
}

# ─────────────────────────────────────────────────────────
# Wave → BPM + wave-name-for-prompt
# ─────────────────────────────────────────────────────────
WAVE_BPM = {
    "Delta":    60,    # sleep / deep rest
    "Theta":    55,    # meditation
    "Alpha":    65,    # calm awake / overthinking
    "Binaural": 65,
    "Beta":     70,
    "Gamma":    75,
}

WAVE_BINAURAL_HZ = {
    "Delta":    2.5, "Theta": 6.0, "Alpha": 10.0,
    "Beta":     18.0, "Gamma": 40.0, "Binaural": 8.0,
}

# ─────────────────────────────────────────────────────────
# Problem keyword → use-case phrase (used 2nd in prompt after raga+instrument)
# ─────────────────────────────────────────────────────────
PROBLEM_USE_CASE = {
    "sleep":          "deep sleep",
    "rest":           "deep rest",
    "overthinking":   "calm an overactive mind",
    "anxiety":        "anxiety relief",
    "stress":         "stress release",
    "meditation":     "deep meditation",
    "nervous system": "nervous system reset",
    "vagus":          "vagus nerve reset",
    "emotional":      "emotional release and healing",
    "unwind":         "evening unwind",
    "dopamine":       "dopamine reset",
    "racing":         "calm racing thoughts",
    "morning":        "morning calm",
}

# ─────────────────────────────────────────────────────────
# Atmosphere / mood adjectives by wave
# ─────────────────────────────────────────────────────────
WAVE_ATMOSPHERE = {
    "Delta":    "floating and meditative",
    "Theta":    "transcendent and contemplative",
    "Alpha":    "calm and grounding",
    "Binaural": "calm and grounding",
    "Beta":     "alert and clear",
    "Gamma":    "sharp and focused",
}


def _use_case_for(problem_kw):
    p = problem_kw.lower()
    for key, val in PROBLEM_USE_CASE.items():
        if key in p:
            return val
    return "deep meditation"


def build_suno_prompt(problem_kw, instrument_name, raga_name, wave_name="Delta", bpm=None):
    """Suno prompt matching user's proven template (comma-separated tags, ~280-380 chars)."""
    inst_lower = instrument_name.lower()
    use_case = _use_case_for(problem_kw)
    melodic = INSTRUMENT_MELODIC.get(instrument_name, f"slow {inst_lower} phrases")
    time_mood = RAGA_TIME_MOOD.get(raga_name, "deeply meditative mood")
    bpm = bpm or WAVE_BPM.get(wave_name, 60)
    wave_l = wave_name.lower()
    atmosphere = WAVE_ATMOSPHERE.get(wave_name, "floating and meditative")

    parts = [
        f"Raga {raga_name} {inst_lower}",
        use_case,
        "ambient Indian classical",
        "tanpura drone",
        melodic,
        f"{bpm} BPM",
        f"{wave_l} wave undercurrent",
        "no percussion",
        "no rhythm",
        atmosphere,
        "warm low-frequency hum",
        "seamless loop",
        "instrumental only",
        f"solo {inst_lower} with tanpura",
        time_mood,
        "deeply calming",
        "no abrupt changes",
    ]
    return ", ".join(parts)


def build_production_spec(candidate):
    """Full production spec: Suno prompt + binaural layer + mix levels + master target."""
    comp = candidate["components"]
    base_hz = int("".join(c for c in comp["hz"]["hz"] if c.isdigit()) or 0)
    wave = comp["wave"]["wave"]
    wave_hz = WAVE_BINAURAL_HZ.get(wave, 8.0)
    bpm = WAVE_BPM.get(wave, 60)

    return {
        "suno_prompt": build_suno_prompt(
            comp["problem"]["kw"],
            comp["instrument"]["name"],
            comp["raga"]["name"],
            wave_name=wave,
            bpm=bpm,
        ),
        "suno_strategy": (
            "Custom mode → paste prompt → style: Ambient → generate 2 songs → "
            "pick better → click Extend 3-4× to reach ~10-12 min. Generate a "
            "second seed with same prompt → extend → ~10 min. Total: ~20 min "
            "source. Loop in post to fill 60 min."
        ),
        "suno_critical_tips": [
            "Use Custom mode (not simple) so the full prompt is honored",
            "Style: Ambient (best for raga + drone combos)",
            "Generate 6-8 versions, use only the best 2-3",
            "Use 'Extend' for continuity across the source",
            "If Suno adds vocals despite prompt: regenerate (don't add 'no vocals' — it sometimes triggers them)",
        ],
        "duration_target_sec": 3600,
        "binaural": {
            "base_hz":  base_hz,
            "wave_hz":  wave_hz,
            "left_hz":  base_hz,
            "right_hz": base_hz + wave_hz,
            "level_db": -18,
            "command": (
                f"python3 tools/binaural_generator.py --base {base_hz} "
                f"--beat {wave_hz} --duration 3600 --output binaural.wav"
            ),
        },
        "drone": {
            "instrument": f"Tanpura tuned to root of Raga {comp['raga']['name']}",
            "level_db":   -24,
        },
        "mix_levels_db": {
            "suno_layer":     -3,
            "binaural_layer": -18,
            "drone_layer":    -24,
        },
        "fades": {"in_sec": 10, "out_sec": 30},
        "master_lufs": -14,
        "output": "MP4 1920×1080, AAC 320kbps, 48kHz, single thumbnail image, +faststart",
        "merge_pattern": (
            "ffmpeg -y -loop 1 -i thumbnail.png -i final_audio.wav "
            "-c:v libx264 -tune stillimage -preset medium -c:a aac -b:a 320k "
            "-ar 48000 -pix_fmt yuv420p -t 3600 -movflags +faststart output.mp4"
        ),
    }

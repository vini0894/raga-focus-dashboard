"""
Raga Focus — Description Hook Auto-Generator

Maps a problem keyword to the opening sentence of the YouTube description.
Style follows your validated pattern:
  - 1-sentence visceral problem statement + outcome promise
  - Active voice ("this does X", not "this is X")
  - No jargon in the opener — plain language, then technical detail later

Used by proposal_to_video.py to populate `cfg.description.hook` for the
existing templates/description.py renderer.

Reference example (from your Apr 24 Veena video):
  "When the mind won't stop, trying harder makes it worse. This does the opposite."
"""

from typing import Dict, List


# Hook sentences by problem keyword bucket
PROBLEM_HOOKS = {
    "overthinking": "When your mind won't stop, trying harder makes it worse. This does the opposite.",
    "anxiety":      "When anxiety rises, your nervous system needs grounding more than reasoning. This is grounding.",
    "stress":       "When stress builds up faster than you can release it, this is the reset.",
    "sleep":        "When sleep won't come, your nervous system needs the right signal — not silence.",
    "rest":         "When you're tired but can't actually rest, this is what 'deep rest' actually feels like.",
    "meditation":   "When you sit down to meditate but the mind won't settle, this lets the music do the work.",
    "racing":       "When thoughts race faster than you can follow, this slows them down without forcing.",
    "nervous system":"When your nervous system is stuck in alert, this gives it the signal to come back to baseline.",
    "vagus":        "When your vagus nerve is stuck in fight-or-flight, this is the opposite of trying to push through.",
    "emotional":    "When emotion sits heavy in your chest, this helps it move without pushing it away.",
    "heavy heart":  "When the heart feels heavy and there's nowhere to put it, this gives it room.",
    "morning":      "When morning brings tension instead of energy, this is how you ease into the day.",
    "unwind":       "When the work day ends but your mind hasn't, this is the bridge.",
    "dopamine":     "When you're overstimulated and numb at the same time, this is the slow restart.",
    "burnout":      "When you've gone past tired into something else, this isn't a fix — it's a place to rest.",
    "exhausted":    "When you're past tired and still can't stop, this is the slowdown signal your body is asking for.",
    "screen time":  "When screens have left your nervous system buzzing, this is the off-switch.",
    "digital":      "When digital noise has filled the inside of your head, this clears the static.",
}


# A second sentence — the "what this is" body opener
PROBLEM_BODY_INTROS = {
    "overthinking": "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer to ease an overactive mind.",
    "anxiety":      "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for nervous system grounding.",
    "stress":       "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for deep tension release.",
    "sleep":        "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer that signals the body it's safe to fall.",
    "rest":         "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for true restorative rest.",
    "meditation":   "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer to deepen the meditation.",
    "racing":       "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer to slow the mental tempo.",
    "nervous system":"One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer to regulate an activated nervous system.",
    "vagus":        "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for vagal toning.",
    "emotional":    "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for emotional release and softening.",
    "heavy heart":  "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for emotional release.",
    "morning":      "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer for a calm morning entry.",
    "unwind":       "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer to dissolve the work-day energy.",
    "dopamine":     "One unbroken hour of {instrument_phrase} playing Raga {raga_name}, tuned to {hz} healing frequency, with a subliminal {wave} wave layer to rebalance overstimulation.",
}


# Instrument descriptors (matches templates/description.py for consistency)
INSTRUMENT_PHRASES = {
    "Bansuri":  "ancient Indian bamboo flute",
    "Sarangi":  "bowed sarangi (vocal-like Indian string instrument)",
    "Dilruba":  "bowed dilruba (Indian string instrument with a mournful resonance)",
    "Veena":    "ancient Indian veena",
    "Sarod":    "fretless sarod (warm metallic Indian string)",
    "Santoor":  "hammered santoor (crystalline Indian dulcimer)",
    "Esraj":    "bowed esraj (lyrical Indian string)",
    "Tanpura":  "tanpura drone",
    "Sitar":    "Indian sitar",
}


# "Best for" lists per problem
PROBLEM_BEST_FOR = {
    "overthinking":  ["Calming an overactive mind", "Anxiety relief", "Mental rest", "Pre-sleep wind-down"],
    "anxiety":       ["Anxiety relief", "Nervous system grounding", "Pre-sleep calm", "Panic prevention"],
    "stress":        ["Stress release", "Tension melting", "End-of-day reset", "Deep relaxation"],
    "sleep":         ["Falling asleep", "Insomnia relief", "Night-time wind-down", "Pre-sleep meditation"],
    "rest":          ["Deep rest", "Yoga nidra", "Restorative pause", "Recovery"],
    "meditation":    ["Deep meditation", "Sacred practice", "Inner stillness", "Daily mindfulness"],
    "racing":        ["Racing thoughts relief", "Mental quieting", "Focus reset", "Anxiety calm"],
    "nervous system":["Nervous system reset", "Polyvagal regulation", "Burnout recovery", "Stress downshift"],
    "vagus":         ["Vagus nerve toning", "Polyvagal reset", "Parasympathetic activation", "Stress recovery"],
    "emotional":     ["Emotional release", "Grief and tenderness", "Heart-opening practice", "Sound healing"],
    "morning":       ["Morning calm", "Anxiety-free wake-up", "Cortisol regulation", "Day-start meditation"],
    "unwind":        ["After-work decompression", "Evening transition", "Letting go of the day", "Pre-dinner reset"],
    "dopamine":      ["Dopamine reset", "Overstimulation recovery", "Digital detox", "Rebalancing"],
}


def _bucket_for(problem_kw: str) -> str:
    """Find which problem bucket matches the keyword."""
    p = problem_kw.lower()
    for key in PROBLEM_HOOKS:
        if key in p:
            return key
    return "anxiety"  # safe fallback


def build_description_hook(problem_kw: str) -> str:
    """Return the 1-sentence opener for the description."""
    bucket = _bucket_for(problem_kw)
    return PROBLEM_HOOKS[bucket]


def build_description_body_intro(problem_kw, instrument_name, raga_name, hz, wave_name):
    """Return the second paragraph — what's in this video, technically."""
    bucket = _bucket_for(problem_kw)
    template = PROBLEM_BODY_INTROS.get(bucket, PROBLEM_BODY_INTROS["anxiety"])
    return template.format(
        instrument_phrase=INSTRUMENT_PHRASES.get(instrument_name, instrument_name),
        raga_name=raga_name,
        hz=hz,
        wave=wave_name,
    )


def build_best_for(problem_kw: str) -> List[str]:
    """List of bullet points for '⏱ Best for:' section."""
    bucket = _bucket_for(problem_kw)
    return PROBLEM_BEST_FOR.get(bucket, ["Stress relief", "Deep relaxation", "Meditation"])


# ═══════════════════════════════════════════════════════════
# FULL description (paste-ready into YouTube Studio)
# ═══════════════════════════════════════════════════════════

INSTRUMENT_BLURB = {
    "Sarangi":  "the Sarangi (a bowed Indian string instrument with a deep, vocal-like quality)",
    "Esraj":    "the Esraj (a haunting, vocal-like Indian string instrument)",
    "Dilruba":  "the Dilruba (a bowed Indian string instrument with mournful, resonant friction)",
    "Bansuri":  "the Bansuri (a bamboo flute with a breathy, meditative tone)",
    "Sitar":    "the Sitar (a plucked string instrument with shimmering overtones)",
    "Tanpura":  "the Tanpura (a drone instrument that creates a meditative harmonic foundation)",
    "Veena":    "the Veena (an ancient plucked Indian string instrument with deep spiritual resonance)",
    "Sarod":    "the Sarod (a fretless plucked instrument with rich, resonant low-end)",
    "Santoor":  "the Santoor (a hammered string instrument with crystalline cascading tones)",
}

HZ_INTENT_BLURB = {
    "7.83Hz":  "Schumann Resonance — Earth's natural electromagnetic frequency for deep grounding",
    "174Hz":   "ancient healing frequency for pain relief and grounding",
    "432Hz":   "classic healing frequency tuned to natural harmony",
    "528Hz":   "love frequency, said to support DNA repair and emotional release",
    "639Hz":   "frequency for harmonious relationships and connection",
    "741Hz":   "frequency for detoxification and problem-solving",
    "963Hz":   "frequency for spiritual awakening and oneness",
    "40Hz":    "Gamma wave frequency for peak focus and concentration",
}

HOW_TO_USE_BY_BUCKET = {
    "overthinking":   "Find a quiet space. Let the music play in the background — don't force focus on it. Within 10–15 minutes, the mental chatter slows on its own.",
    "anxiety":        "Sit or lie down. Breathe naturally. Don't try to feel calm — let the music do the work. The body recognises safety in the sound and follows.",
    "sleep":          "Play at low volume from a phone or speaker by your bed. Don't watch the screen. Within 20–30 minutes, the music loops you into sleep.",
    "stress":         "Press play, close your eyes, and let one full session move through you. Stress unwinds in layers — give it the full duration.",
    "rest":           "Lie down. Let the music play uninterrupted. True rest happens when you stop trying.",
    "meditation":     "Sit with a steady spine. Let the music carry your breath. No technique needed — the frequency does the work.",
    "emotional":      "Allow whatever rises to rise. The frequency keeps you grounded while the emotion moves.",
    "morning":        "Play during your morning routine — coffee, journaling, slow stretches. Sets the nervous system to a calm baseline for the day.",
    "vagus":          "Combine with slow deep breaths (4 in, 8 out). Music + breath together activate the parasympathetic response.",
    "nervous system": "Lie down with eyes closed. Let the binaural layer entrain your brainwaves. 20+ minutes is the minimum dose for nervous-system shift.",
    "racing":         "Don't try to slow your thoughts. Listen, breathe, let the music do the slowing for you.",
    "unwind":         "Play it the moment you close your laptop. The transition from work-mind to rest-mind needs a signal — this is yours.",
    "dopamine":       "Reduce screen brightness. Single-task on this one input — no scrolling. The reset comes from doing less, not more.",
    "heavy heart":    "Don't fight the heaviness. Sit with it. The Veena's resonance gives the heart a place to soften without forcing.",
}


def build_full_description(
    problem_kw: str,
    instrument_name: str,
    raga_name: str = "",
    hz: str = "",
    wave_name: str = "",
    duration_minutes: int = 60,
    top_tags: list = None,
) -> str:
    """Paste-ready YouTube description.

    Sections in order: hook → body intro → 🎵 what you'll hear → ⏱ chapters →
    🧠 how to use → ⏱ best for → 📺 channel CTA → 🌿 no-ads → hashtags.
    """
    p_lower = problem_kw.lower()

    hook = build_description_hook(problem_kw)
    body = build_description_body_intro(problem_kw, instrument_name, raga_name or "", hz or "", wave_name or "")
    # If raga is empty, strip the "playing Raga " phrase from the body intro
    if not raga_name:
        body = body.replace("playing Raga , ", "playing ")
        body = body.replace("playing Raga ,", "playing")
        body = body.replace("Raga , ", "")
        body = body.replace(" Raga ,", "")
    # If wave is empty, strip the wave layer phrase
    if not wave_name:
        body = body.replace(" with a subliminal  wave layer", "")
        body = body.replace("a subliminal  wave layer ", "")
    best_for = build_best_for(problem_kw)
    chapters = build_chapter_timestamps(duration_minutes, problem_kw)

    inst_blurb = INSTRUMENT_BLURB.get(instrument_name, instrument_name.lower())
    hz_blurb = HZ_INTENT_BLURB.get(hz, "a healing frequency") if hz else ""

    how_to = "Press play. Let the music run uninterrupted. The frequencies do the work."
    for key, txt in HOW_TO_USE_BY_BUCKET.items():
        if key in p_lower:
            how_to = txt
            break

    # Hashtags — top validated tags
    hashtags_pool = top_tags or [
        "calmingmusic", "healingmusic", "ambientmusic", "meditationmusic",
        "indianclassicalmusic", "schumannresonance", instrument_name.lower(),
    ]
    hashtags = []
    for t in hashtags_pool[:7]:
        tag = t.replace(" ", "").replace("-", "").replace(".", "").lower()
        if tag and len(tag) <= 30 and ("#" + tag) not in hashtags:
            hashtags.append("#" + tag)
    hashtags_line = " ".join(hashtags)

    L = []
    L.append(hook); L.append("")
    L.append(body); L.append("")
    L.append("🎵 What you'll hear:")
    L.append(f"- {inst_blurb}")
    if hz:
        L.append(f"- {hz} — {hz_blurb}")
    if wave_name:
        L.append(f"- A subliminal {wave_name} wave entrainment layer")
    L.append("- Seamless loops with smooth crossfades throughout")
    L.append("")
    L.append(chapters)
    L.append("")
    L.append("🧠 How to use:")
    L.append(how_to)
    L.append("")
    L.append("⏱ Best for:")
    for b in best_for:
        L.append(f"• {b}")
    L.append("")
    L.append("📺 If this helped, please subscribe to Raga Focus for daily uploads:")
    L.append("- Veena, Sarangi, Bansuri, Dilruba and other Indian instruments")
    L.append("- 1-hour sessions tuned to specific healing frequencies")
    L.append("- Music for anxiety, overthinking, sleep, stress, and emotional release")
    L.append("")
    L.append("🌿 No mid-roll ads. No interruptions. Just music.")
    L.append("")
    L.append("— Raga Focus")
    if hashtags_line:
        L.append("")
        L.append(hashtags_line)
    return "\n".join(L)


# ═══════════════════════════════════════════════════════════
# Chapter timestamps — narrative arc per duration
# ═══════════════════════════════════════════════════════════
def build_chapter_timestamps(duration_minutes: int = 60, problem_kw: str = "") -> str:
    """Return a markdown-ready chapters block for the description.

    Standard 4-section arc: Settling → Deepening → Peak resonance → Gradual return.
    Times scale to duration. YouTube auto-detects chapters when 0:00 is present
    and there are ≥3 timestamps with ≥10s gaps.

    Tone of section labels adapts to the problem bucket (sleep vs anxiety vs
    meditation) for tighter title-content match.
    """
    bucket = _bucket_for(problem_kw)
    # Bucket-specific narrative labels
    LABELS = {
        "sleep":        ["Settling", "Drift begins", "Deep delta", "Gentle return"],
        "rest":         ["Settling", "Restorative wave", "Deepest rest", "Gentle return"],
        "overthinking": ["Settling", "Mind softening", "Stillness peak", "Coming back"],
        "anxiety":      ["Settling", "Grounding deepens", "Nervous-system reset", "Return"],
        "stress":       ["Settling", "Tension release", "Full melt", "Slow return"],
        "meditation":   ["Settling", "Breath synchrony", "Peak depth", "Coming back"],
        "emotional":    ["Settling", "Feeling rises", "Release", "Softening home"],
        "morning":      ["Easing in", "Building presence", "Steady center", "Carrying forward"],
    }
    labels = LABELS.get(bucket, ["Settling", "Deepening", "Peak resonance", "Gradual return"])

    # Times scale to duration — settle 0%, deepen 13%, peak 50%, return 83%
    def fmt(t_min):
        h, m = divmod(int(t_min), 60)
        return f"{h}:{m:02d}" if h else f"{m}:00"

    times = [
        (0,                                              labels[0]),
        (max(1, int(duration_minutes * 0.13)),           labels[1]),
        (max(2, int(duration_minutes * 0.50)),           labels[2]),
        (max(3, int(duration_minutes * 0.83)),           labels[3]),
    ]
    out = ["⏱ Chapters"]
    for t_min, label in times:
        out.append(f"{fmt(t_min)}   {label}")
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_cases = [
        ("overthinking music", "Bansuri", "Bhupali", "432Hz", "Alpha"),
        ("can't fall asleep", "Bansuri", "Yaman", "432Hz", "Delta"),
        ("nervous system reset", "Sarangi", "Bhairavi", "432Hz", "Alpha"),
        ("heavy heart", "Sarangi", "Darbari", "174Hz", "Theta"),
    ]
    for problem, inst, raga, hz, wave in test_cases:
        print(f"\n─── {problem} | {inst} | Raga {raga} | {hz} | {wave} ───")
        print(f"\n  HOOK:")
        print(f"  {build_description_hook(problem)}")
        print(f"\n  BODY INTRO:")
        print(f"  {build_description_body_intro(problem, inst, raga, hz, wave)}")
        print(f"\n  BEST FOR: {build_best_for(problem)}")

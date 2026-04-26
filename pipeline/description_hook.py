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

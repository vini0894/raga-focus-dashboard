"""
Raga Focus — Thumbnail Image Prompt Generator (PLACEHOLDER)

To be calibrated against the user's actual thumbnail prompts.
User will paste 3-5 of their proven prompts; this module will then
parallel the Suno calibration approach:

  - LOCKED template parts (style, border, ratio, texture, negatives)
  - VARIABLE slots per video (instrument figure, time-of-day from raga,
    palette from mood, landscape from raga setting, motif)

Until calibration data lands, build_thumbnail_image_prompt() returns
a structured TODO with the candidate inputs visible, so downstream
code can integrate now and the body just fills in once we have
real prompts.
"""


def build_thumbnail_image_prompt(problem_kw, instrument_name, raga_name, wave_name):
    """
    PLACEHOLDER. Returns a TODO marker with all candidate inputs surfaced
    so the bridge / dashboard can carry it through. Will be replaced with
    real Pichwai/Kangra template once user pastes proven prompts.
    """
    return (
        f"[TODO: thumbnail image prompt — calibration pending] "
        f"problem={problem_kw}, instrument={instrument_name}, "
        f"raga={raga_name}, wave={wave_name}"
    )

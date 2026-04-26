"""
Raga Focus — Thumbnail Text Variant Generator

Generates 3 short overlay-text candidates for the thumbnail.
Each ≤ 4 words, scannable at 120px feed width.

Strategy:
  Variant A — Question form (visceral problem)         — best for cold-feed CTR
  Variant B — Imperative outcome promise               — best for warm cohort
  Variant C — Identity / state label                   — best for low-friction scan

User validates all 3 in VidIQ; pipeline picks the highest-scoring one.

The image base (Pichwai/Kangra) and design treatment are LOCKED via the
thumbnail_image.py prompt builder. This module owns ONLY the words on top.

Source of truth for variant phrases: config.PROBLEM_THUMBNAIL_TEXT
(creative copy keyed by problem-bucket substring; same pattern as
PROBLEM_TO_RAGA_MOOD).
"""

from typing import Dict, List, Any
from config import PROBLEM_THUMBNAIL_TEXT


def _bucket_for(problem_kw: str) -> str:
    """Find which thumbnail-text bucket matches the problem."""
    p = problem_kw.lower()
    for key in PROBLEM_THUMBNAIL_TEXT:
        if key in p:
            return key
    return "anxiety"  # safe default


def build_thumbnail_text_variants(problem_kw: str) -> List[Dict[str, str]]:
    """
    Return 3 variants in this order:
      A: question form (cold-feed CTR play)
      B: outcome / imperative (warm cohort)
      C: identity / state label (low-friction scan)

    Each variant: {"label": "A_question", "text": "...", "vidiq_kw": "..."}
    The vidiq_kw is what the user should paste into VidIQ to validate.
    """
    bucket = _bucket_for(problem_kw)
    bank = PROBLEM_THUMBNAIL_TEXT[bucket]

    return [
        {
            "label":     "A_question",
            "strategy":  "Question form — cold-feed CTR",
            "text":      bank["question"][0],
            "alts":      bank["question"][1:],   # backups if A fails VidIQ
            "vidiq_kw":  bank["question"][0].lower(),
        },
        {
            "label":     "B_outcome",
            "strategy":  "Outcome / imperative — warm cohort",
            "text":      bank["outcome"][0],
            "alts":      bank["outcome"][1:],
            "vidiq_kw":  bank["outcome"][0].lower(),
        },
        {
            "label":     "C_identity",
            "strategy":  "Identity / state label — low-friction scan",
            "text":      bank["identity"][0],
            "alts":      bank["identity"][1:],
            "vidiq_kw":  bank["identity"][0].lower(),
        },
    ]


def pick_thumbnail_winner(variants: List[Dict[str, str]],
                          scores: Dict[str, int]) -> Dict[str, Any]:
    """
    Given user-pasted VidIQ scores per variant, return the winner.
    Falls back to alternates within a variant if its primary failed.
    """
    from typing import Any
    MIN = 50  # thumbnail text bar — slightly lower than title since it's not the main SEO carrier

    candidates = []
    for v in variants:
        primary_score = scores.get(v["vidiq_kw"])
        if primary_score is not None and int(primary_score) >= MIN:
            candidates.append({**v, "score": int(primary_score), "used_alt": False})
        else:
            # try alternates within this variant
            for alt_text in v["alts"]:
                alt_kw = alt_text.lower()
                if alt_kw in scores and int(scores[alt_kw]) >= MIN:
                    candidates.append({
                        **v, "text": alt_text, "vidiq_kw": alt_kw,
                        "score": int(scores[alt_kw]), "used_alt": True,
                    })
                    break

    if not candidates:
        return {
            "winner": None,
            "reason": "no variant passed VidIQ ≥ 50",
            "fallback_recommended": variants[0]["text"],
        }

    candidates.sort(key=lambda c: -c["score"])
    return {
        "winner":    candidates[0],
        "ranked":    candidates,
        "reason":    f"Best: {candidates[0]['label']} ({candidates[0]['score']} score)",
    }


# remove inner Any import (we already imported at top)


# ═══════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("─── Variants for 'overthinking music' ───")
    variants = build_thumbnail_text_variants("overthinking music")
    for v in variants:
        print(f"  {v['label']:14s}  {v['text']:30s}  ({v['strategy']})")

    print("\n─── Simulated VidIQ scores → winner pick ───")
    test_scores = {
        "mind racing?":     58,   # variant A primary
        "quiet your mind":  72,   # variant B primary — strongest
        "overthinker?":     45,   # variant C — fail
        "anxious mind":     54,   # variant C alternate — passes
    }
    result = pick_thumbnail_winner(variants, test_scores)
    if result["winner"]:
        print(f"  Winner: {result['winner']['text']} ({result['winner']['label']}, score {result['winner']['score']})")
        print(f"  Reason: {result['reason']}")
        print(f"\n  Full ranking:")
        for c in result["ranked"]:
            print(f"    {c['score']:>3}  {c['text']:30s}  ({c['label']})")
    else:
        print(f"  No winner: {result['reason']}")
        print(f"  Fallback: {result['fallback_recommended']}")

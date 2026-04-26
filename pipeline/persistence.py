"""
Raga Focus — Auto-Persistence Layer

When user inputs arrive (VidIQ scores, thumbnail text scores, A/B results,
Suno quality ratings), this module ensures they get stored in long-term
memory files so future pipeline runs benefit from them.

Memory files (all under raga-focus-dashboard/data/):
  - keyword_bank.csv          → validated/invalidated title keywords
  - thumbnail_text_bank.csv   → validated thumbnail-overlay phrases
  - suno_results.csv          → which Suno prompts produced shipped audio
  - approval_log.csv          → audit trail of approvals + rejection reasons
  - ab_results.csv            → concluded A/B title tests (existing)

The pipeline reads these on every run (via keyword_bank.py, historical.py, etc.).
So the loop closes: today's inputs improve tomorrow's recommendations.
"""

import csv
from datetime import date
from pathlib import Path
from typing import Dict, List, Any

from paths import DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)

KEYWORD_BANK_CSV    = DATA_DIR / "keyword_bank.csv"
THUMBNAIL_BANK_CSV  = DATA_DIR / "thumbnail_text_bank.csv"
SUNO_RESULTS_CSV    = DATA_DIR / "suno_results.csv"
APPROVAL_LOG_CSV    = DATA_DIR / "approval_log.csv"
INVALIDATED_CSV     = DATA_DIR / "invalidated_keywords.csv"

MIN_BANK_SCORE = 60


def _append_csv(path: Path, header: List[str], row: Dict[str, Any]):
    """Append a row to a CSV, creating the file with header if needed."""
    new_file = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if new_file:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in header})


# ─────────────────────────────────────────────────────────
# Promote VidIQ scores from a session into the long-term keyword bank
# ─────────────────────────────────────────────────────────
def auto_promote_vidiq_scores(scores: Dict[str, int],
                              slot_hint: Dict[str, str] = None,
                              source: str = "session"):
    """
    Walk a {keyword: score} dict from a session.
    Append passing keywords (≥60) to keyword_bank.csv.
    Append failing keywords to invalidated_keywords.csv (so we stop suggesting them).
    `slot_hint` (optional): {keyword: "problem"|"wave"|"raga"|"hz"} — if known.
    """
    promoted = []
    invalidated = []
    today = date.today().isoformat()
    slot_hint = slot_hint or {}

    for kw, score in scores.items():
        if not isinstance(score, (int, float)):
            continue
        slot = slot_hint.get(kw, _infer_slot(kw))
        if int(score) >= MIN_BANK_SCORE:
            if not _kw_already_in_bank(kw):
                _append_csv(KEYWORD_BANK_CSV,
                    ["phrase", "slot", "vidiq_score", "vidiq_comp",
                     "source", "first_added", "last_score_check"],
                    {
                        "phrase":           kw.strip().lower(),
                        "slot":             slot,
                        "vidiq_score":      int(score),
                        "source":           source,
                        "first_added":      today,
                        "last_score_check": today,
                    },
                )
                promoted.append(kw)
        else:
            # Track invalidations so we don't keep suggesting the same dead phrase
            _append_csv(INVALIDATED_CSV,
                ["phrase", "slot", "vidiq_score", "tested_on"],
                {
                    "phrase":      kw,
                    "slot":        slot,
                    "vidiq_score": int(score),
                    "tested_on":   today,
                },
            )
            invalidated.append(kw)

    return {"promoted": promoted, "invalidated": invalidated}


def _kw_already_in_bank(kw: str) -> bool:
    if not KEYWORD_BANK_CSV.exists():
        return False
    with open(KEYWORD_BANK_CSV) as f:
        for row in csv.DictReader(f):
            if row.get("phrase", "").strip().lower() == kw.strip().lower():
                return True
    return False


def _infer_slot(keyword: str) -> str:
    """Best-effort slot inference if user didn't tell us. Used only for auto-promote."""
    k = keyword.lower()
    if "wave" in k or "session" in k or "binaural" in k:
        return "wave"
    if "raga " in k or k.startswith("raga"):
        return "raga"
    if "hz" in k:
        return "hz"
    if any(inst in k for inst in ["bansuri","sarangi","dilruba","sitar","veena","sarod","santoor","tanpura","esraj"]):
        return "instrument"
    return "problem"  # default


def is_invalidated(keyword: str) -> bool:
    """Check if a keyword has been tried and failed in the past."""
    if not INVALIDATED_CSV.exists():
        return False
    with open(INVALIDATED_CSV) as f:
        for row in csv.DictReader(f):
            if row.get("phrase", "").strip().lower() == keyword.strip().lower():
                return True
    return False


# ─────────────────────────────────────────────────────────
# Thumbnail text bank — track which overlays got validated
# ─────────────────────────────────────────────────────────
def log_thumbnail_text_result(phrase: str, vidiq_score: int,
                              problem_kw: str, won_ab: bool = False):
    _append_csv(THUMBNAIL_BANK_CSV,
        ["phrase", "vidiq_score", "problem_kw", "won_ab", "logged_on"],
        {
            "phrase":      phrase,
            "vidiq_score": int(vidiq_score),
            "problem_kw":  problem_kw,
            "won_ab":      "true" if won_ab else "false",
            "logged_on":   date.today().isoformat(),
        },
    )


# ─────────────────────────────────────────────────────────
# Suno prompt outcome — track which prompts produced shipped audio
# ─────────────────────────────────────────────────────────
def log_suno_result(video_id: str, prompt: str, instrument: str,
                    raga: str, quality_rating: int, notes: str = ""):
    """
    quality_rating: 1-5
      5 = shipped as-is, perfect
      4 = shipped with minor edits
      3 = shipped after re-generation
      2 = had to swap the prompt template
      1 = abandoned, prompt didn't work for this combo
    """
    _append_csv(SUNO_RESULTS_CSV,
        ["video_id", "prompt", "instrument", "raga", "quality_rating", "notes", "logged_on"],
        {
            "video_id":       video_id,
            "prompt":         prompt,
            "instrument":     instrument,
            "raga":           raga,
            "quality_rating": int(quality_rating),
            "notes":          notes,
            "logged_on":      date.today().isoformat(),
        },
    )


# ─────────────────────────────────────────────────────────
# Approval log — owner audit trail
# ─────────────────────────────────────────────────────────
def log_approval(video_id: str, decision: str, reviewer: str = "owner",
                 reason: str = ""):
    """decision: 'approved' | 'rejected'"""
    _append_csv(APPROVAL_LOG_CSV,
        ["video_id", "decision", "reviewer", "reason", "logged_on"],
        {
            "video_id":  video_id,
            "decision":  decision,
            "reviewer":  reviewer,
            "reason":    reason,
            "logged_on": date.today().isoformat(),
        },
    )

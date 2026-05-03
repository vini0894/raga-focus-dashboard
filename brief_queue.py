"""Brief Queue — dynamic loader for the new dashboard tab.

Reads JSON briefs written by `pipeline/proposal_to_video.py` to
`raga-focus-dashboard/data/video_briefs/{slug}.json`.

Status persistence: `data/brief_status.json` (parallel to `data/queue_status.json`
used by the old static production_queue.py — they don't conflict).

Why a new module instead of editing production_queue.py:
- Old queue is a static VIDEOS = [...] list edited by hand
- New queue is a dynamic file scanner that picks up briefs automatically as
  the pipeline writes them
- Both tabs run side-by-side until the new one is comfortable, then we kill
  the old.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import storage

DATA_DIR = Path(__file__).resolve().parent / "data"
BRIEFS_DIR = DATA_DIR / "video_briefs"
STATUS_OVERRIDE = DATA_DIR / "brief_status.json"

# 6-state machine matching CHANNEL_PLAYBOOK.md state machine
STATUS_VALUES = [
    "DRAFT",            # Just generated, not yet reviewed
    "PENDING_REVIEW",   # Submitted for owner approval
    "APPROVED",         # Owner approved, ready for production
    "IN_PRODUCTION",    # Suno/thumbnail/render in progress
    "RENDERED",         # MP4 produced, awaiting upload
    "PUBLISHED",        # Live on YouTube
    "COMPLETE",         # A/B test concluded, fully done
]


def _load_overrides():
    return storage.read_brief_statuses()


def _save_overrides(overrides):
    pass


def load_all_briefs():
    """Load every JSON brief, apply status overrides, sort newest-first."""
    return storage.read_all_briefs()


def set_brief_status(brief_id: str, status: str):
    """Persist a status change. Idempotent.

    Side effect: when a brief transitions to PUBLISHED, log its title structure
    to data/shipped_titles.csv so the pipeline learns from real-ship outcomes.
    """
    if status not in STATUS_VALUES:
        raise ValueError(f"status must be one of {STATUS_VALUES}, got {status!r}")
    prev_status = storage.read_brief_statuses().get(brief_id, "DRAFT")
    storage.set_brief_status_gs(brief_id, status)

    # Log on PUBLISHED transition (idempotent — only logs once per brief)
    if status == "PUBLISHED" and prev_status != "PUBLISHED":
        try:
            _log_shipped_title(brief_id)
            _stamp_date_shipped(brief_id)
        except Exception:
            pass


def _stamp_date_shipped(brief_id: str):
    """Write date_shipped into the brief JSON so the queue can display it."""
    brief = get_brief_by_id(brief_id)
    if not brief:
        return
    brief["date_shipped"] = datetime.utcnow().isoformat()[:10]
    storage.write_brief(brief)


def _log_shipped_title(brief_id: str):
    """Append a row to shipped_titles.csv capturing the structure of a shipped title."""
    import csv
    brief = get_brief_by_id(brief_id)
    if not brief:
        return
    title = brief.get("title", "")
    parts = [p.strip() for p in title.split("|") if p.strip()]
    comp = brief.get("components", {})
    row = {
        "shipped_on":   datetime.utcnow().isoformat()[:10],
        "brief_id":     brief_id,
        "title":        title,
        "title_length": len(title),
        "slot_count":   len(parts),
        "lead_hook":    parts[0] if parts else "",
        "instrument":   comp.get("instrument", "") if isinstance(comp.get("instrument"), str) else comp.get("instrument", {}).get("name", ""),
        "hz":           comp.get("hz", "") if isinstance(comp.get("hz"), str) else comp.get("hz", {}).get("hz", ""),
        "raga":         comp.get("raga", "") if isinstance(comp.get("raga"), str) else comp.get("raga", {}).get("name", ""),
        "wave":         comp.get("wave", "") if isinstance(comp.get("wave"), str) else comp.get("wave", {}).get("wave", ""),
    }
    # Extract problem_kw from components (handles both flat string and nested dict)
    prob = comp.get("problem", "")
    row["problem_kw"] = (prob.get("kw", "") if isinstance(prob, dict) else prob).lower()

    storage.append_shipped_title(row)


def get_brief_by_id(brief_id: str):
    return storage.read_brief_by_id(brief_id)


def count_by_status():
    """Quick stats for tab header."""
    briefs = load_all_briefs()
    out = {s: 0 for s in STATUS_VALUES}
    for b in briefs:
        s = b.get("status", "DRAFT")
        if s in out:
            out[s] += 1
    return out

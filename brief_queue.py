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
from pathlib import Path

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
    if not STATUS_OVERRIDE.exists():
        return {}
    try:
        return json.loads(STATUS_OVERRIDE.read_text())
    except Exception:
        return {}


def _save_overrides(overrides):
    STATUS_OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_OVERRIDE.write_text(json.dumps(overrides, indent=2, sort_keys=True))


def load_all_briefs():
    """Load every JSON brief, apply status overrides, sort newest-first."""
    if not BRIEFS_DIR.exists():
        return []
    briefs = []
    for f in sorted(BRIEFS_DIR.glob("*.json")):
        try:
            briefs.append(json.loads(f.read_text()))
        except Exception:
            continue
    overrides = _load_overrides()
    for b in briefs:
        if b.get("id") in overrides:
            b["status"] = overrides[b["id"]]
    briefs.sort(key=lambda b: b.get("created_at", ""), reverse=True)
    return briefs


def set_brief_status(brief_id: str, status: str):
    """Persist a status change. Idempotent."""
    if status not in STATUS_VALUES:
        raise ValueError(f"status must be one of {STATUS_VALUES}, got {status!r}")
    overrides = _load_overrides()
    overrides[brief_id] = status
    _save_overrides(overrides)


def get_brief_by_id(brief_id: str):
    for b in load_all_briefs():
        if b.get("id") == brief_id:
            return b
    return None


def count_by_status():
    """Quick stats for tab header."""
    briefs = load_all_briefs()
    out = {s: 0 for s in STATUS_VALUES}
    for b in briefs:
        s = b.get("status", "DRAFT")
        if s in out:
            out[s] += 1
    return out

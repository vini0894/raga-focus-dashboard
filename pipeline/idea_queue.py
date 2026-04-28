"""
Idea Queue — persistent workshop space between Idea Gen and Brief Queue.

A queued idea is a candidate the user has decided is worth working on. It
persists across sessions so title refinement (scoring, alternate keywords,
raga fit, rebuild) can happen iteratively over hours/days before promotion
to a production brief.

Storage: data/idea_queue/<id>.json — one file per queue item.

Lifecycle:
    Idea Gen card → ➕ Add to Queue → Idea Queue (status: drafting)
                 → workshop title  → status: title_locked
                 → 📤 Generate Brief → moves to Brief Queue (this module
                                       deletes the queue item or marks shipped)
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
QUEUE_DIR = DATA_DIR / "idea_queue"


def _ensure_dir():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def _slug(text: str) -> str:
    """Slugify a string for use in filenames."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower())
    return s.strip("_")[:50]


def _id_from_candidate(cand: dict) -> str:
    comp = cand.get("components", {}) or {}
    today = datetime.now().date().isoformat()
    parts = [
        today,
        _slug(comp.get("problem", {}).get("kw", "")),
        _slug(comp.get("instrument", {}).get("name", "")),
        _slug(comp.get("raga", {}).get("name", "")),
    ]
    return "q_" + "_".join(p for p in parts if p)


def add_from_candidate(cand: dict) -> dict:
    """
    Take a raw candidate dict from a proposal JSON and persist it as a queue
    item. Returns the queue item with assigned id.
    Idempotent: if an item already exists for this candidate signature, returns
    the existing one untouched.
    """
    _ensure_dir()
    qid = _id_from_candidate(cand)
    path = QUEUE_DIR / f"{qid}.json"
    if path.exists():
        return json.loads(path.read_text())

    comp = cand.get("components", {}) or {}
    problem_kw = comp.get("problem", {}).get("kw", "")
    instrument = comp.get("instrument", {}).get("name", "")
    raga = comp.get("raga", {}).get("name", "")
    concept = f"{instrument} for {problem_kw}".strip(" .")

    item = {
        "id":            qid,
        "queued_at":     datetime.now().isoformat(timespec="seconds"),
        "status":        "drafting",
        "bucket":        cand.get("strategy", "moonshot"),
        "score":         cand.get("score"),
        "concept":       concept or "(unnamed concept)",
        "components":    comp,
        "strategy_note": cand.get("strategy_note", ""),
        "reasons":       cand.get("reasons", []) or [],
        "working_title": cand.get("title", ""),
        "title_variants": cand.get("title_variants") or {},
        "look_and_feel": {
            "thumbnail_style": "Pichwai/Kangra miniature, ornate border, cream parchment, dark-teal serif overlay",
            "vibe":            "",
        },
        "decision_log": [
            {"ts": datetime.now().isoformat(timespec="seconds"),
             "event": "Queued from Idea Gen",
             "detail": f"score={cand.get('score')} bucket={cand.get('strategy', 'moonshot')}"}
        ],
        "notes": "",
    }
    path.write_text(json.dumps(item, indent=2, default=str))
    return item


def list_items() -> List[dict]:
    """Return all queue items sorted by queued_at descending."""
    _ensure_dir()
    out = []
    for f in QUEUE_DIR.glob("q_*.json"):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            continue
    out.sort(key=lambda x: x.get("queued_at", ""), reverse=True)
    return out


def get_item(qid: str) -> Optional[dict]:
    p = QUEUE_DIR / f"{qid}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def update_item(qid: str, updates: dict, log_event: Optional[str] = None) -> Optional[dict]:
    """Patch an existing queue item. Auto-appends to decision log if log_event given."""
    item = get_item(qid)
    if not item:
        return None
    item.update(updates)
    if log_event:
        item.setdefault("decision_log", []).append({
            "ts":    datetime.now().isoformat(timespec="seconds"),
            "event": log_event,
        })
    (QUEUE_DIR / f"{qid}.json").write_text(json.dumps(item, indent=2, default=str))
    return item


def delete_item(qid: str) -> bool:
    p = QUEUE_DIR / f"{qid}.json"
    if not p.exists():
        return False
    p.unlink()
    return True


def bucket_counts() -> Dict[str, int]:
    counts = {"competitor": 0, "niche": 0, "moonshot": 0}
    for it in list_items():
        b = it.get("bucket", "moonshot")
        if b in counts:
            counts[b] += 1
        else:
            counts["moonshot"] += 1
    return counts

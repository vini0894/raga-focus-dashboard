"""
storage.py — Persistent storage layer for Raga Focus dashboard.

Backends:
  1. Google Sheets (primary) — survives Streamlit Cloud redeploys.
  2. Local CSV/JSON files    — fallback for local dev and when Sheets is
                               unavailable (no credentials, network error, etc.)

Sheet name : "Raga Focus Data"
Worksheets : shipped_titles | dismissed_candidates | brief_status | video_briefs

Each worksheet auto-creates with correct headers on first write.

Caching: module-level dicts with 60-second TTL to avoid hammering the Sheets
API on every Streamlit re-render. Call invalidate_cache() to clear all entries
(e.g. right after a write that the current session needs to read back).
"""

from __future__ import annotations

import csv
import json
import time
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Paths for the local fallback
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
DATA_DIR = _HERE / "data"
BRIEFS_DIR = DATA_DIR / "video_briefs"

_SHIPPED_CSV      = DATA_DIR / "shipped_titles.csv"
_DISMISSED_CSV    = DATA_DIR / "dismissed_candidates.csv"
_BRIEF_STATUS_JSON = DATA_DIR / "brief_status.json"

_SHIPPED_HEADER    = ["shipped_on", "brief_id", "title", "title_length",
                      "slot_count", "lead_hook", "instrument", "hz", "raga",
                      "wave", "problem_kw"]
_DISMISSED_HEADER  = ["signature", "problem_keyword", "title", "dismissed_on"]
_BRIEF_STATUS_HEADER = ["brief_id", "status"]
_VIDEO_BRIEFS_HEADER = ["id", "json_data"]

# ---------------------------------------------------------------------------
# Module-level TTL cache
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 60.0  # seconds


def _cache_get(key: str):
    """Return cached value if still fresh, else None."""
    entry = _CACHE.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _CACHE[key]
        return None
    return value


def _cache_set(key: str, value: object) -> None:
    _CACHE[key] = (time.monotonic(), value)


def invalidate_cache() -> None:
    """Clear all cached data immediately (call after writes)."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Google Sheets client (lazy singleton)
# ---------------------------------------------------------------------------
_GS_CLIENT = None   # gspread client, None until first successful auth
_GS_SHEET  = None   # opened Spreadsheet object
_GS_FAILED = False  # set True after a fatal auth failure so we stop retrying


def _get_sheet():
    """Return the gspread Spreadsheet, or None if unavailable."""
    global _GS_CLIENT, _GS_SHEET, _GS_FAILED

    if _GS_FAILED:
        return None
    if _GS_SHEET is not None:
        return _GS_SHEET

    try:
        import gspread

        # --- credentials ---------------------------------------------------
        creds_dict: Optional[dict] = None

        # 1. Streamlit Cloud — secrets injected as a dict
        try:
            import streamlit as st
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
        except Exception:
            pass

        # 2. Local dev — file on disk
        if creds_dict is None:
            local_creds = DATA_DIR / "gcp_credentials.json"
            if local_creds.exists():
                creds_dict = json.loads(local_creds.read_text())

        if creds_dict is None:
            _GS_FAILED = True
            return None

        # gspread 6.x API
        _GS_CLIENT = gspread.service_account_from_dict(creds_dict)
        _GS_SHEET  = _GS_CLIENT.open("Raga Focus Data")
        return _GS_SHEET

    except Exception:
        _GS_FAILED = True
        return None


def _get_worksheet(tab_name: str, headers: list[str]):
    """Return (worksheet, is_new). Auto-creates the tab with headers if absent."""
    sheet = _get_sheet()
    if sheet is None:
        return None, False

    try:
        try:
            ws = sheet.worksheet(tab_name)
            return ws, False
        except Exception:
            # Worksheet doesn't exist — create it
            ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
            ws.append_row(headers, value_input_option="RAW")
            return ws, True
    except Exception:
        return None, False


# ---------------------------------------------------------------------------
# shipped_titles
# ---------------------------------------------------------------------------

def read_shipped_titles() -> list[dict]:
    """Return all shipped-title rows as a list of dicts."""
    cached = _cache_get("shipped_titles")
    if cached is not None:
        return cached

    # Try Google Sheets first
    ws, _ = _get_worksheet("shipped_titles", _SHIPPED_HEADER)
    if ws is not None:
        try:
            records = ws.get_all_records(expected_headers=_SHIPPED_HEADER)
            _cache_set("shipped_titles", records)
            return records
        except Exception:
            pass

    # Fallback: local CSV
    rows = _read_csv(_SHIPPED_CSV, _SHIPPED_HEADER)
    _cache_set("shipped_titles", rows)
    return rows


def append_shipped_title(row: dict) -> None:
    """Append one row to shipped_titles. row must have the 11 canonical columns."""
    ordered = [str(row.get(h, "")) for h in _SHIPPED_HEADER]

    ws, _ = _get_worksheet("shipped_titles", _SHIPPED_HEADER)
    if ws is not None:
        try:
            ws.append_row(ordered, value_input_option="RAW")
            invalidate_cache()
            return
        except Exception:
            pass

    # Fallback: local CSV
    _append_csv(_SHIPPED_CSV, _SHIPPED_HEADER, row)
    invalidate_cache()


def shipped_titles_as_df() -> pd.DataFrame:
    """Return shipped_titles as a pandas DataFrame."""
    rows = read_shipped_titles()
    if not rows:
        return pd.DataFrame(columns=_SHIPPED_HEADER)
    return pd.DataFrame(rows, columns=_SHIPPED_HEADER)


# ---------------------------------------------------------------------------
# dismissed_candidates
# ---------------------------------------------------------------------------

def read_dismissed_candidates() -> list[dict]:
    """Return all dismissed-candidate rows as a list of dicts."""
    cached = _cache_get("dismissed_candidates")
    if cached is not None:
        return cached

    ws, _ = _get_worksheet("dismissed_candidates", _DISMISSED_HEADER)
    if ws is not None:
        try:
            records = ws.get_all_records(expected_headers=_DISMISSED_HEADER)
            _cache_set("dismissed_candidates", records)
            return records
        except Exception:
            pass

    rows = _read_csv(_DISMISSED_CSV, _DISMISSED_HEADER)
    _cache_set("dismissed_candidates", rows)
    return rows


def append_dismissed_candidate(row: dict) -> None:
    """Append one dismissed-candidate row."""
    ordered = [str(row.get(h, "")) for h in _DISMISSED_HEADER]

    ws, _ = _get_worksheet("dismissed_candidates", _DISMISSED_HEADER)
    if ws is not None:
        try:
            ws.append_row(ordered, value_input_option="RAW")
            invalidate_cache()
            return
        except Exception:
            pass

    _append_csv(_DISMISSED_CSV, _DISMISSED_HEADER, row)
    invalidate_cache()


# ---------------------------------------------------------------------------
# brief_status
# ---------------------------------------------------------------------------

def read_brief_statuses() -> dict:
    """Return {brief_id: status} dict."""
    cached = _cache_get("brief_status")
    if cached is not None:
        return cached

    ws, _ = _get_worksheet("brief_status", _BRIEF_STATUS_HEADER)
    if ws is not None:
        try:
            records = ws.get_all_records(expected_headers=_BRIEF_STATUS_HEADER)
            result = {r["brief_id"]: r["status"] for r in records if r.get("brief_id")}
            _cache_set("brief_status", result)
            return result
        except Exception:
            pass

    # Fallback: local JSON
    result = _read_brief_status_json()
    _cache_set("brief_status", result)
    return result


def set_brief_status_gs(brief_id: str, status: str) -> None:
    """Upsert brief_id → status in the brief_status store."""
    ws, _ = _get_worksheet("brief_status", _BRIEF_STATUS_HEADER)
    if ws is not None:
        try:
            # Find existing row to update, or append
            cell = ws.find(brief_id, in_column=1)
            if cell:
                ws.update_cell(cell.row, 2, status)
            else:
                ws.append_row([brief_id, status], value_input_option="RAW")
            invalidate_cache()
            return
        except Exception:
            pass

    # Fallback: local JSON
    overrides = _read_brief_status_json()
    overrides[brief_id] = status
    _write_brief_status_json(overrides)
    invalidate_cache()


# ---------------------------------------------------------------------------
# video_briefs
# ---------------------------------------------------------------------------

def read_all_briefs() -> list[dict]:
    """Return all briefs as a list of dicts (parsed from json_data column)."""
    cached = _cache_get("video_briefs")
    if cached is not None:
        return cached

    ws, _ = _get_worksheet("video_briefs", _VIDEO_BRIEFS_HEADER)
    if ws is not None:
        try:
            records = ws.get_all_records(expected_headers=_VIDEO_BRIEFS_HEADER)
            briefs = []
            for r in records:
                raw = r.get("json_data", "")
                if raw:
                    try:
                        briefs.append(json.loads(raw))
                    except Exception:
                        pass
            _cache_set("video_briefs", briefs)
            return briefs
        except Exception:
            pass

    # Fallback: local JSON files
    briefs = _read_briefs_from_disk()
    _cache_set("video_briefs", briefs)
    return briefs


def write_brief(brief: dict) -> None:
    """Upsert a brief by brief['id'] into the video_briefs store."""
    brief_id = brief.get("id", "")
    json_str = json.dumps(brief, default=str)

    ws, _ = _get_worksheet("video_briefs", _VIDEO_BRIEFS_HEADER)
    if ws is not None:
        try:
            cell = ws.find(brief_id, in_column=1)
            if cell:
                ws.update_cell(cell.row, 2, json_str)
            else:
                ws.append_row([brief_id, json_str], value_input_option="RAW")
            invalidate_cache()
            return
        except Exception:
            pass

    # Fallback: local JSON file
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    slug = brief_id.replace("/", "_").replace("\\", "_") or "unnamed"
    (BRIEFS_DIR / f"{slug}.json").write_text(json.dumps(brief, indent=2, default=str))
    invalidate_cache()


def read_brief_by_id(brief_id: str) -> Optional[dict]:
    """Return a single brief dict by id, or None if not found."""
    for b in read_all_briefs():
        if b.get("id") == brief_id:
            return b
    return None


# ---------------------------------------------------------------------------
# Internal helpers — CSV read/write
# ---------------------------------------------------------------------------

def _read_csv(path: Path, headers: list[str]) -> list[dict]:
    """Read a CSV into a list of dicts; return empty list if file missing."""
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []


def _append_csv(path: Path, headers: list[str], row: dict) -> None:
    """Append one row to a CSV, writing headers if the file is new."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if new_file:
            writer.writeheader()
        writer.writerow({h: row.get(h, "") for h in headers})


def _write_csv_full(path: Path, headers: list[str], rows: list[dict]) -> None:
    """Overwrite a CSV with the full list of rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


# ---------------------------------------------------------------------------
# Internal helpers — brief_status JSON (local fallback)
# ---------------------------------------------------------------------------

def _read_brief_status_json() -> dict:
    if not _BRIEF_STATUS_JSON.exists():
        return {}
    try:
        return json.loads(_BRIEF_STATUS_JSON.read_text())
    except Exception:
        return {}


def _write_brief_status_json(overrides: dict) -> None:
    _BRIEF_STATUS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _BRIEF_STATUS_JSON.write_text(json.dumps(overrides, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Internal helpers — video_briefs from disk (local fallback)
# ---------------------------------------------------------------------------

def _read_briefs_from_disk() -> list[dict]:
    """Read all *.json files from data/video_briefs/."""
    if not BRIEFS_DIR.exists():
        return []
    briefs = []
    for f in sorted(BRIEFS_DIR.glob("*.json")):
        try:
            briefs.append(json.loads(f.read_text()))
        except Exception:
            continue
    return briefs

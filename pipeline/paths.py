"""
Pipeline path resolver.

Works in two layouts:
1. **Standalone (local dev):** pipeline/ lives at project root, data at
     `../raga-focus-dashboard/data/`
2. **Bundled (deployed dashboard):** pipeline/ lives inside the dashboard repo,
     data at `../data/` relative to pipeline/

Every module that needs a data file imports DATA_DIR / PROPOSALS_DIR from here
instead of building paths against `Path(__file__).parent.parent`.
"""
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Try the bundled layout first (most common in deployed mode), then standalone.
_CANDIDATES = [
    _HERE.parent / "data",                              # bundled: dashboard/pipeline + dashboard/data
    _HERE.parent / "raga-focus-dashboard" / "data",     # standalone: project_root/pipeline + project_root/raga-focus-dashboard/data
]

DATA_DIR = next((c for c in _CANDIDATES if c.exists()), _CANDIDATES[0])

# Proposals dir — usually one level up from data
PROPOSALS_CANDIDATES = [
    _HERE.parent / "videos" / "proposals",                                     # bundled
    _HERE.parent / "videos" / "proposals",                                     # also standalone (same path)
]
PROPOSALS_DIR = next((c for c in PROPOSALS_CANDIDATES if c.exists()), PROPOSALS_CANDIDATES[0])

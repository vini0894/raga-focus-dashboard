"""OAuth authentication for YouTube Data + Analytics APIs.

Supports two modes:
1. Local: reads token.json + credentials.json from disk (gitignored)
2. Streamlit Cloud: reads from st.secrets

The refresh_token allows infinite access without re-auth, so once you've
run the OAuth flow locally once and saved token.json, the app can auth
forever (or until the user revokes access in their Google settings).
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

HERE = Path(__file__).parent
TOKEN_FILE = HERE / "token.json"
CREDENTIALS_FILE = HERE / "credentials.json"


def _get_credentials() -> Credentials:
    """Load Google OAuth credentials from either disk (local) or st.secrets (cloud)."""
    # Try Streamlit secrets first (cloud deployment)
    try:
        import streamlit as st  # only available when running in Streamlit

        if hasattr(st, "secrets") and "oauth" in st.secrets:
            oauth = st.secrets["oauth"]
            creds = Credentials(
                token=None,  # access token will be refreshed
                refresh_token=oauth["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=oauth["client_id"],
                client_secret=oauth["client_secret"],
                scopes=SCOPES,
            )
            if not creds.valid and creds.refresh_token:
                creds.refresh(Request())
            return creds
    except (ImportError, Exception):
        pass

    # Fall back to local disk
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Missing {TOKEN_FILE}. Run the OAuth flow first (see README) "
            f"or configure st.secrets for cloud deployment."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        # Persist refreshed token
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def yt_data():
    """YouTube Data API v3 client."""
    return build("youtube", "v3", credentials=_get_credentials(), cache_discovery=False)


def yt_analytics():
    """YouTube Analytics API v2 client."""
    return build("youtubeAnalytics", "v2", credentials=_get_credentials(), cache_discovery=False)


def iso_date(d: date) -> str:
    """Format a date as ISO 8601 (YYYY-MM-DD)."""
    return d.isoformat()

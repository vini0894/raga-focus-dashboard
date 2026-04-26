"""One-shot OAuth re-auth: opens browser, mints a fresh token.json,
writes it to BOTH the dashboard and the youtube-mcp locations (same scopes,
same client_id, so one auth flow covers both), and prints the TOML block
for Streamlit Cloud Secrets.

Usage:
    python3 regen_token.py
"""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# Both locations need the same fresh token.
HERE = Path(__file__).parent
DASHBOARD_TOKEN = HERE / "token.json"
MCP_TOKEN       = HERE.parent / "youtube-mcp" / "token.json"

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0, prompt="consent")
token_json = creds.to_json()

DASHBOARD_TOKEN.write_text(token_json)
print(f"✓ wrote {DASHBOARD_TOKEN}")

if MCP_TOKEN.parent.exists():
    MCP_TOKEN.write_text(token_json)
    print(f"✓ wrote {MCP_TOKEN}")
else:
    print(f"⚠️  MCP dir not found at {MCP_TOKEN.parent} — skipping MCP token write")

t = json.loads(token_json)
print("\n" + "=" * 60)
print("✅ Tokens refreshed. Paste this into Streamlit Cloud Secrets:")
print("=" * 60)
print(f'''[oauth]
client_id = "{t["client_id"]}"
client_secret = "{t["client_secret"]}"
refresh_token = "{t["refresh_token"]}"
''')

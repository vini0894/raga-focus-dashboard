# Raga Focus — Intelligence Dashboard

Channel analytics + competitor tracking + production queue dashboard for the Raga Focus YouTube channel.

## What it shows

- **Overview** — channel stats + 28-day trends
- **Videos** — sortable table of all videos with retention, impressions, CTR
- **Video Detail** — drill-down into any video with keyword analysis + auto-recommendations
- **Competitors** — Raga Heal + Shanti Instrumentals side-by-side
- **Reach Data** — manually captured impressions + CTR from Studio
- **Production Queue** — next 7 videos with full briefs (titles, descriptions, tags, Suno prompts, thumbnail prompts)

## Local development

### First-time setup

```bash
# 1. Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone this repo (or cd into it locally)
cd raga-focus-dashboard

# 3. Install Python deps
uv venv --python 3.11
uv pip install -r requirements.txt

# 4. Set up OAuth credentials
# Follow the "OAuth setup" section below to generate token.json
```

### Run locally

```bash
uv run streamlit run dashboard.py
```

Opens at http://localhost:8501

### OAuth setup (one-time)

You need a `token.json` file (cached Google OAuth credentials) to fetch YouTube data.

**Option A: Copy existing token.json**

If you already have `token.json` in another location (e.g. the parent `youtube-mcp/` folder), copy it here:

```bash
cp ../youtube-mcp/token.json .
cp ../youtube-mcp/credentials.json .  # optional — only needed for first-time auth flow
```

**Option B: Generate fresh token**

1. Go to https://console.cloud.google.com/
2. Create project → enable YouTube Data API v3 + YouTube Analytics API
3. Create OAuth 2.0 Desktop credentials → download as `credentials.json`
4. Save `credentials.json` in this folder
5. Run the OAuth flow:

```python
# python run_oauth.py
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)
open("token.json", "w").write(creds.to_json())
```

## Deploy to Streamlit Cloud

### 1. Push to GitHub (private repo)

```bash
cd raga-focus-dashboard
git init
git add .
git commit -m "Initial dashboard"
gh repo create raga-focus-dashboard --private --source=. --remote=origin --push
```

### 2. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repo
4. Main file path: `dashboard.py`
5. Click "Advanced settings" → Paste in secrets (see next section)
6. Click "Deploy"

### 3. Configure secrets

In Streamlit Cloud → your app → Settings → Secrets, paste:

```toml
[app]
password = "your-shared-password"

[oauth]
client_id = "<from credentials.json>"
client_secret = "<from credentials.json>"
refresh_token = "<from token.json>"
```

**Where to find these values:**

- `client_id` and `client_secret`: open your `credentials.json` file → under `installed` → `client_id` and `client_secret`
- `refresh_token`: open your `token.json` file → `refresh_token` field

### 4. Share

After deployment, you'll get a URL like `https://raga-focus-dashboard.streamlit.app`.

Share the URL + password with your collaborators.

## Security notes

- `token.json`, `credentials.json`, and `secrets.toml` are in `.gitignore` — never committed
- The OAuth refresh_token gives perpetual access (until the user revokes it in Google account settings)
- Anyone with the password can see the dashboard. Rotate the password if a collaborator leaves.
- The dashboard is read-only — viewers can't modify channel data

## Updating content

### Reach data (impressions / CTR)

Edit `data/REACH_DATA.md`. Push to GitHub → Streamlit Cloud auto-redeploys.

### Production queue

Edit `production_queue.py` (the `VIDEOS` list). Update status field as you publish:

- `"not_started"` → `"in_progress"` → `"published"`

### Competitor list

Edit `COMPETITORS` dict at the top of `dashboard.py`.

## Architecture

```
raga-focus-dashboard/
├── dashboard.py           # Main Streamlit app
├── auth.py               # OAuth (local file OR st.secrets)
├── production_queue.py   # 7-video production briefs
├── data/
│   ├── REACH_DATA.md    # Manual impressions/CTR capture
│   └── KEYWORD_DATA.md  # VidIQ-validated keywords
├── requirements.txt     # Python dependencies
├── .streamlit/
│   ├── config.toml     # Dark theme (Raga Focus palette)
│   └── secrets.toml    # OAuth + password (gitignored)
├── .gitignore
└── README.md
```

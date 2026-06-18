# Raga Focus — Channel Automation Master Plan

> **Status:** design / blueprint (not yet built). Drafted 2026-06-18.
> **Goal:** automate the *spine* of the channel — data, analysis, validation, monitoring, learning, and planning-prep — so the human spends time only on **creative judgment, music/art production, and publishing**, not on data wrangling or manual checks.
> **Guiding principle:** automation *feeds* the validation gates and the human; it never bypasses judgment or auto-publishes against thin data.

---

## 0. Why now (the case this session made)

The work that slowed us down was never ideas or strategy — it was:
- **Stale data:** `shipped_titles`, cooldown, locks, and per-video CTR all lagged days/weeks, producing false "clear" signals and wrong thumbnail-refresh picks.
- **Manual monitoring:** the human shares Studio screenshots so day-1/day-7 health can be checked by hand.
- **Status drift:** the dashboard reverts brief status on every push (committed `brief_status.json` is the Cloud source of truth; gspread fails).

All three are mechanical and automatable. That's the wedge.

---

## 1. Human vs Agent — the split

| The AGENT owns | The HUMAN owns |
|---|---|
| Data ingestion + freshness | Final title/thumbnail **choice** (from agent's shortlist) |
| Analysis + digests | Music generation (Suno) |
| Validation (preflight, cooldown, cannibalization, locks) | Thumbnail art creation |
| Post-ship monitoring + recommendations | The **publish** action (upload + go-live) |
| A/B + refresh tracking, learning loop | Strategic direction (what bet to make) |
| Brief scaffolding, candidate generation | VidIQ scoring (until/unless API) |
| Planning-prep (candidate slate) | Approvals at each gate |

**Human-in-the-loop stays at:** creative picks, production, publish, and final approval. The agent prepares and recommends; the human decides and ships.

---

## 2. The pipeline — 9 stages, current state, automation target

| # | Stage | Now | Target | Hard wall |
|---|---|---|---|---|
| 1 | **Data ingestion** | MCP/API live (views/AVD/retention/geo) + manual Studio export (CTR/impr) | Scheduled auto-refresh of all derivable stores; flag overdue Studio export | per-video **CTR + impressions = Studio-only** |
| 2 | **Analysis** | manual / in-chat | Scheduled digest: top/decliners, relRet, hidden gems, click-capped, lane fit, topline trend | — |
| 3 | **Idea generation** | in-chat (Claude) | Assist: surface fresh-vs-owned lanes, untapped clusters, competitor gaps; pre-generate candidate leads for review | judgment stays human |
| 4 | **Validation** | preflight + cooldown + cannibalization + locks (auto); VidIQ (manual) | Full 4-source conflict check auto; VidIQ API if available | **VidIQ = manual paste** |
| 5 | **Brief assembly** | manual JSON (Claude) | Auto-scaffold (structure, tags, Suno per patterns, binaural per lane, desc + thumb templates); human fills creative | — |
| 6 | **Production** (Suno, thumb) | manual (human) | Auto-generate the *prompts*; generation stays human (explore image-gen for thumb later) | **creative = human** |
| 7 | **Publish / timing** | manual upload | Auto **recommend** publish time per strategy (India-morning / US-seed / evening) | **upload = human** (API later, optional) |
| 8 | **Post-ship monitoring** | manual (screenshots) | Scheduled per-ship health vs brief criteria → keep/kill/swap-thumb; A/B conclusion + refresh-due detection | needs CTR (Studio) for full picture |
| 9 | **Learning loop** | semi-auto | Auto-bank A/B verdicts, regenerate locks/lane-fit, update playbook + keyword bank | — |

---

## 3. The build roadmap (phased)

### Phase 1 — DATA SPINE  ⭐ build first
**One job: never be stale again.**
- `pipeline/refresh_data.py` — pulls latest via YT Data + Analytics API (token.json), then:
  - Appends new uploads to `shipped_titles.csv` (the manual `get_recent_videos` flow, automated).
  - Updates views/AVD/watch-time per video (REACH_HISTORY + enriched).
  - Regenerates `phrase_locks.json` + `instrument_lane_fit.json` (calls `playbook_generators.py`).
  - **Auto-status:** any brief whose `video_id`/title is now live on YT → flip `brief_status.json` to PUBLISHED + stamp `date_shipped`. **(This kills the status-revert bug for good.)**
  - Writes a `data/_freshness.json` manifest: last refresh, Studio-export age, row counts.
  - Flags: "⚠️ Studio CTR export is N days old — please export" when stale.
- **Output:** every cooldown/lock/lane check downstream runs on current data. No more false clears.
- **Scheduling:** daily (see §5). Runs locally (token.json) or wherever token is reachable.

### Phase 2 — MONITORING
**One job: replace screenshot checks.**
- `pipeline/ship_monitor.py` — for each live ship, read its brief's `success_good` / `failure_mode` / `ab_test`, compare to fresh data:
  - Day-1 and Day-7 verdicts: **keep / watch / kill / swap-thumbnail-to-backup**.
  - Detect concluded A/B tests → prompt to bank the verdict.
  - Surface thumbnail-refresh queue items that are **due today**.
  - Trigger `thumbnail_backup.swap_if` conditions (e.g. CTR < threshold at day 7).
- **Output:** a daily "ship health" digest with specific actions, not raw numbers.

### Phase 3 — ANALYSIS DIGEST + PLANNING-PREP
- `pipeline/digest.py` — scheduled report: top performers, decliners, relRet leaderboard, **hidden gems** (high relRet + low reach), **click-capped** list (thumbnail-refresh candidates), lane/instrument fit, topline trend, concentration risk.
- `pipeline/plan_prep.py` — weekly: run cooldowns for the next 7 days, classify lanes **fresh vs owned**, word-saturation scan, draft a **candidate slate** (instrument × lane × fresh-lead suggestions). Human starts from a prepared board.

### Phase 4 — ASSIST GENERATION
- `pipeline/brief_scaffold.py` — given (instrument, lane, raga, title), emit the brief JSON skeleton: tags from title, **Suno prompt** per `suno_prompt_patterns` (physical instrument desc, raga + characteristic, BPM/Hz/binaural by lane, no-vocals, loop), **description** template (accessible voice), **thumbnail prompt** template. Human edits the creative lines.
- **Candidate-lead generator** (LLM-assisted): per lane/theme, propose fresh leads (offering-framed, music-intent-aware) → human scores via VidIQ. All still pass the gate.

### Phase 5 — ORCHESTRATION + SCHEDULING
- Tie it together with **scheduled cloud/local routines** (§5).
- Optional, later: **publish automation** via YouTube upload API (schedule the go-live time the planner recommends). Higher risk — gate behind explicit human approval per video.

---

## 4. Data architecture (single source of truth)

**Problem today:** status lives in 3 places (Google Sheets → fails on Cloud → committed `brief_status.json` → overwrites dashboard edits on push). Hence the revert bug.

**Target:**
- **`brief_status.json` (in git) = the single source of truth.** No GS dependency for status.
- **Status is *derived*, not hand-set:** the Phase-1 refresh detects published videos and sets PUBLISHED automatically. Humans rarely touch status.
- **`data/_freshness.json`** = the freshness contract every script checks before trusting a store.
- **Revenue stays gitignored** (`data/private/`, `reach_exports/`) — never pushed.
- **Studio exports** land in `data/reach_exports/pervideo_YYYY-MM-DD.csv`; the refresh agent ingests the newest and records its age.

---

## 5. Scheduled routines (the "automation" layer)

| Routine | Cadence | Does |
|---|---|---|
| **Daily refresh + health** | every morning | `refresh_data.py` + `ship_monitor.py` → fresh stores + ship-health digest + "export overdue" flag |
| **Weekly planning-prep** | weekly (e.g. Sun) | `plan_prep.py` + `digest.py` → candidate slate + analysis report for the week |
| **Weekly retro** | weekly | what shipped, what worked, A/B verdicts banked, playbook updates |
| **Monthly competitor pull** | monthly | refresh competitor snapshots |

**Where they run (decision needed):** the YT API needs `token.json` (OAuth refresh token).
- **Option A — local cron / Claude Code scheduled (local):** simplest; token already on the Mac. Mac must be on.
- **Option B — cloud routine with token in env/secret:** always-on; requires storing the refresh token securely in the cloud runner.
- Recommendation: start **local** (Option A), move to cloud once stable.

---

## 6. Hard walls (permanent manual handoffs)

1. **Per-video CTR + impressions** — Studio-only, no API. Agent *reminds* + *ingests* the export; can't pull it. (Everything else — views, AVD, retention, geo, traffic, subs — is API-available.)
2. **VidIQ scoring** — manual paste today. Explore VidIQ API; until then, the candidate-generator hands the human a list to score.
3. **Suno music generation** — human + tool. Agent writes the prompt.
4. **Thumbnail art** — human + image tool. Agent writes the prompt; explore image-gen API later for the Pichwai base.
5. **Publish / go-live** — human action. Agent recommends the time/strategy.

---

## 7. Guardrails (so automation helps, not harms)

- **Gates are never bypassed.** Preflight, cooldown, cannibalization, word-saturation still gate every title; automation *feeds* them.
- **No auto-kill on thin data.** Honor the 7-day patience window; don't act on day-1 noise.
- **Human approval at: final title/thumb pick, production, publish.**
- **Confidence over completeness.** A recommendation states its evidence + sample size; low-N stays flagged, not asserted.
- **Don't over-experiment.** The system tracks how many A/B variables ride concurrent thin-reach ships and warns when reads will be unresolvable.
- **Revenue never leaves the machine.**

---

## 8. Sequencing / priorities

1. **Phase 1 — Data spine** (`refresh_data.py` + auto-status + freshness manifest). *Chosen first.* Removes staleness + the status bug.
2. **Phase 2 — Ship monitor.** Removes manual screenshot checks.
3. **Phase 3 — Digest + planning-prep.** Each week starts prepared.
4. **Phase 4 — Brief scaffold + candidate generator.** Cuts brief-writing time.
5. **Phase 5 — Scheduling + (optional) publish automation.**

**The end state:** the human opens a daily digest ("here's what's healthy, what to swap, what's due"), a weekly prepared slate ("here are the viable, fresh, validated candidate ships"), picks + approves, generates the music/art, and publishes. The agent does everything else and learns continuously.

---

## 9. Open decisions before building

- **Run location** for routines: local cron vs cloud (token handling). → start local.
- **VidIQ:** is there an API/automatable path, or stays manual?
- **Publish automation:** do we ever want the agent to schedule the actual YouTube go-live (API), or keep upload fully manual?
- **Thumbnail generation:** explore an image model for the Pichwai base + text overlay, or keep fully manual?
- **Idea generation:** how much do we want the agent to *propose* (candidate leads) vs the human driving the creative brief in chat?

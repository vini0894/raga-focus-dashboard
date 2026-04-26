# Raga Focus — Idea Pipeline

Daily video idea generator. Fresh signals + scoring rules → ranked candidates with A/B variants and tag stacks.

## Usage

```bash
cd pipeline
python3 generate_ideas.py
```

Outputs `videos/proposals/YYYY-MM-DD.md` with:
- Top 5 ranked candidates (SEO-led titles, A/B/C variants, full tag stack)
- Hook-template recommendation (data-driven from own catalog + competitor RSS)
- Competitor pulse (last 14 days from Raga Heal + Shanti RSS)
- Rescue queue (high-AVD, low-CTR videos for repackaging)
- Manual validation checklist per candidate

## Daily routine

1. Run `python3 generate_ideas.py` (~5 sec)
2. Open today's proposal markdown
3. Run VidIQ on the manual gates listed (full title, primary keyword)
4. If gates pass → approve top candidate, brief thumbnail + Suno
5. If any gate fails → fall to candidate #2

## Files

| File | Role |
|---|---|
| `config.py` | Static reference: keyword bank, instruments, tonal-fit matrix, kill list, scoring weights |
| `signals.py` | Fresh data: own catalog dates, competitor RSS, recency calculations (computed each run, never cached) |
| `scoring.py` | Pure functions: candidate scoring, title generation (5-slot), A/B/C variants, 4-tier tag stack |
| `historical.py` | Title-hook classification (SEO / question / outcome) + CTR analysis from own catalog and competitor RSS |
| `generate_ideas.py` | Orchestrator — wires it all together, writes the proposal markdown |

## What the pipeline checks (per candidate)

1. ✅ Problem keyword: VidIQ ≥60 HIGH (or flagged for VidIQ check)
2. ✅ Problem not already in our catalog (cannibalization)
3. ✅ Tonal fit: instrument matches problem mood (Bansuri = sleep, Sarangi = anxiety, etc.)
4. ✅ Instrument not used in last 5 days (own channel)
5. ✅ Instrument is "trending" (competitor used in last 30d OR has VidIQ score)
6. ✅ Hz not used in last 7 days
7. ✅ Raga not used in last 7 days
8. ✅ Wave not used in last 7 days
9. ✅ Wave matches problem (Alpha=anxiety, Delta=sleep, etc.)
10. ✅ Title length 60-88 chars
11. ✅ No kill phrases in title
12. ✅ Competitor saturation on this instrument (last 30d)
13. ✅ Competitor recently posted same problem (last 7d)
14. ⚠️ Manual: VidIQ score on full title string
15. ⚠️ Manual: YouTube search top-5 dominance check

## Scheduling (optional)

To run daily at 9am IST, add to crontab:
```
30 3 * * * cd /Users/vinichhajed/Desktop/Claude/Youtube\ project/pipeline && /usr/bin/python3 generate_ideas.py >> ../logs/pipeline.log 2>&1
```
(3:30 UTC = 9:00 IST)

Or use the `anthropic-skills:schedule` skill.

## Updating the keyword bank

When you validate a new keyword in VidIQ:
1. Add to `KEYWORD_DATA.md` (source of truth for human reference)
2. Add to `config.py PROBLEM_HOOKS` with `seo_phrase`, `question`, `outcome`, `kw`, `vidiq_score`, `vidiq_comp`
3. Re-run pipeline — it picks up immediately

When a new instrument is validated, add to `config.py INSTRUMENTS` and to `TONAL_FIT` matrix entries.

## Extending

- **Dashboard integration:** the proposal MD + a JSON sidecar can feed `raga-focus-dashboard/dashboard.py` (planned: Today's Idea tab + Rescue Queue tab)
- **Own RSS pull:** add Raga Focus channel ID to `signals.py` so newly-published videos are caught immediately (without waiting for REACH_HISTORY export)
- **Title manifest:** `videos/manifest.csv` appended on every ship for always-fresh own-catalog state

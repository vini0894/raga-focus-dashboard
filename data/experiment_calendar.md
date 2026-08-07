# Experiment calendar — week on week

> **The single place that answers: what is each ship testing, and WHEN do we read the result.**
> Created 2026-08-07 (user directive: hypotheses were "flowing here and there" — the Aug-3 Hz test
> and the modern-vs-traditional image test had NO read date anywhere, and their d7 read is due Aug 10).
>
> **How the loop works:**
> 1. **At lock** — every brief that carries a test gets a row here (hypothesis · arms · read-due dates).
> 2. **Daily** — `tools/refresh_daily.py` step 4b now runs `tools/experiment_reads.py --no-geo`
>    (auto-links live ships to `hypotheses.json`, cohort-reads every ship ≤21d, flags underpowered
>    A/Bs). Private report → `warehouse/experiment_reads_<date>.md`.
> 3. **On a read-due date** — run the read (Studio per-arm shares are MANUAL — the API cannot see
>    per-arm data or per-arm geo), log to `ab_raw_data.csv` / `ab_results.csv`, write the verdict
>    into `hypotheses.json` (CONFIRMED / KILLED / iterate), and mark the row here ✅.
> 4. **Rules that apply to every read:** YT "no clear winner" = data-insufficiency → always pull
>    post-test CTR · never judge a decayed video on its latest snapshot (survivor bias) · <~10K
>    impressions/week during the test = LIKELY-VOID (Test #42 rule).
> No revenue figures in this file — it lives in the public dashboard repo.

---

## ⚠️ OVERDUE READS (capture from Studio now)

| Test | Ship | Age | What to capture |
|---|---|---|---|
| #45 | Nervous System (52YU6Q64zVw) — STRESS DETOX vs CAN'T RELAX? | 27d+ | per-arm share + post-test CTR |
| #48 | Morning/Uplifting Sitar — FIND YOUR SPARK title pair | 25d+ | per-arm share + post-test CTR |
| #49 | Emotional Healing Sarangi — FIND YOUR SMILE vs NEED SOME COMFORT? | 25d+ | per-arm share + post-test CTR |

---

## wk_2026-08-03 (retro-logged 2026-08-07 — these tests had no read dates recorded anywhere)

| Ship (live) | Test | Arms | Launched | Read d7 | Read d14 | Status |
|---|---|---|---|---|---|---|
| Morning Routine Music \| Slow Sitar & 432Hz (vD-GBhRqEV8, Aug 3) | **IMAGE A/B #1 — the channel's FIRST image test** (modern world vs traditional world, matched pose, identical text) | img: modern vs traditional | 2026-08-03 | **2026-08-10 ⬅ DUE MONDAY** — per-arm share + **country split per arm (Studio only)** | 2026-08-17 post-CTR | 🔴 read not done |
| same ship | **Hz-in-title** (B `Slow Sitar & 432Hz` VidIQ 66 vs C `Wake Up Slowly` 25) — ⚠ Hz CONFOUNDED with lead; a B-win isolates neither | title B vs C | 2026-08-03 | 2026-08-10 | 2026-08-17 | 🔴 read not done · ⚠ 432Hz pitch-shift had to be applied in post — verify it was |
| Can't Sleep Tonight? \| Tanpura (Jul 25) | tanpura-drone sleep viability (track_record override ship) | single | 2026-07-25 | d14 passed | — | capture verdict → hypotheses |

## wk_2026-08-07 (tonight)

| Ship | Test | Arms | Launched | Read d7 | Status |
|---|---|---|---|---|---|
| Sleep Without Waking \| Sitar & Tanpura \| 3 Hours | **VidIQ-floor override at scale** (lead scores 25 vs the ≥60 bar; "THIS WEEK IS THE TEST" per brief title_note) + first Sitar × sleep × 3hr cell | single title | 2026-08-07 19:00 | **2026-08-14** — d7 views/CTR vs sleep-3hr cohort (Surbahar 3,076 / Bansuri 9,712 benchmarks) | ⬜ ships tonight |

## wk_2026-08-10 (current plan)

| Day | Ship | Hypothesis (one per ship) | Arms | Read d7 | Read d14 |
|---|---|---|---|---|---|
| Mon 10 | Quiet Morning \| Sarangi Raga Bilawal | `h_2026-08-10_thumb_composition_bed` — in-bed rest-framing beats other viewer-moments (**image A/B #2**; read #1's Aug-10 result FIRST — it may already answer part of this) | img: bed vs window-tea · title+text fixed | **2026-08-17** per-arm share | 2026-08-24 post-CTR |
| Tue 11 | Brain Fog Music vs Mental Space Music (Bansuri) | Does the VidIQ floor predict anything in browse? (66-scored state lead vs 34-scored abstract register) | title A/B, shared slot-2 | **2026-08-18** | 2026-08-25 |
| Wed 12 | Racing Thoughts vs Anxiety Detox Music (Veena) | `h_2026-07-22_clinical_hook_recovery` ship #3 — state-hook vs clinical-detox register | title A/B, shared slot-2 | **2026-08-19** | 2026-08-26 |
| Thu 13 | Evening Wind Down vs Cozy Evening Music (Santoor) | Functional-unwind vs cozy-aesthetic (T1 comfort register) — first test of the aesthetic register | title A/B, shared slot-2 | **2026-08-20** | 2026-08-27 |
| Fri 14 | Bedtime Music vs Wake Up Rested (Surbahar 3hr) | Search-noun vs morning-after outcome promise (§7b parked direction) + does the PROVEN-cell swap (Surbahar for blocked Bansuri) hold anchor reach? | title A/B, shared slot-2 | **2026-08-21** | 2026-08-28 |

**Standing weekly rhythm from here:** every new brief adds its row at lock · every Monday planning session starts by clearing the previous week's due reads (they're all due by then) · verdicts land in `hypotheses.json` so `recommend_slot.py` inherits them automatically.

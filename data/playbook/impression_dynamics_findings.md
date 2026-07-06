# Impression Dynamics — Data-Backed Findings

**Source data (stored locally — do not re-read from Downloads):**
- `data/daily_channel_impressions.csv` — daily channel-level impressions, 2026-04-04 → 2026-05-29
- `data/REACH_HISTORY.csv` — per-video cumulative snapshots; latest capture `2026-05-31` (71 videos)
- `data/reach_exports/reach_2026-05-31.csv` — raw export (revenue stripped)
- Revenue is PRIVATE only: `data/private/revenue_history.csv` (gitignored) — NEVER surface on dashboard or public repo

**Derived:** 2026-05-31. Re-derive when a new daily-impressions export arrives.
**DOW anchor:** 2026-05-31 = Sunday.

---

## Finding 1 — Mondays always spike (instrument sets the size, not whether)
Every scale-era Monday ship produced a D+1 rising tail. Channel impressions on Monday ship day + next day are consistently above trend.

| Monday | Instrument | D0 | D+1 |
|--------|-----------|-----|-----|
| May 4 | Sarangi | 164K | 424K (ramp) |
| May 11 | Sitar | 1.349M | 1.407M ← biggest single-day jump (+462K) |
| May 18 | Sarangi | 1.376M | 1.537M |
| May 25 | Sarangi | 1.350M | 1.511M |

**Rule:** Place the most rested hero (Sitar > Bansuri) on Monday PM. Monday + Sitar = the channel's strongest combination.

## Finding 2 — Double-shipping does NOT add channel impressions
The channel gets one impression pool per day; extra ships split it, they don't multiply it.
- Tuesday single-ship avg: **1.41M** vs double-ship avg: **1.16M** (single HIGHER)
- Wednesday: double ≈ single (−1%)

**Rule:** One ship per day. Do not stack ships expecting a channel-impression boost. (Extra ships still add catalog value / watch hours — just not same-day channel impressions.)

## Finding 3 — Wednesday drop is real but mild, and recent-only
Wed beat Tue 5 of 8 times historically. BUT last 3 weeks (post-scale) Wed dropped −7% to −16% vs Tue every time. Not a cliff.

**Rule:** Don't waste a rested hero on Wednesday. Use for catalog/filler or skip.

## Finding 4 — Saturday is dead, even for heroes
May 16 Sitar shipped on a Saturday → channel DROPPED −29K. No instrument has beaten the Saturday dip.

**Rule:** Never place a hero on Saturday. Skip or filler only.

## Finding 5 — Instrument tier (post-scale, May 13+) — Sitar is in a league of its own
| Instrument | Avg impr/ship | Notes |
|-----------|---------------|-------|
| 🔥 Sitar | **241K** | 6–11× everything else; consistent |
| Bansuri | 60K avg / **30–40K standard** | 155K outlier was 3-hour format; declining (May 29 = 10K) |
| Sarod | 48K | most consistent non-hero |
| Dilruba | 41K | May 9 had a 2.12M outlier (not repeatable) |
| Surbahar | 30K | variable |
| Sarangi | 22K | |
| Santoor | 21K | filler floor |

**Correction to prior assumption:** Bansuri is NOT a current 247K-hero. The 247K avg was inflated by May 5 (607K) + May 7 (1.19M) outlier week. Standard 90-min Bansuri now = 30–40K. Sitar is the only reliable hero.

## Finding 6 — Lane saturation (same lane back-to-back) is NOT proven
Anxiety/stress lane back-to-back with DIFFERENT instruments within 1–3 days showed no consistent suppression (2nd ship beat 1st in 3 of 4 cases). Instrument tier + Monday slot dominate any lane-proximity effect.

**Rule:** Lane cooldown is not a hard constraint. Only same-INSTRUMENT spacing matters (see weekly_planning_rules.yaml §3). Exception: if Sitar(anxiety) + another anxiety ship land within 24h, Sitar absorbs the algo budget — space those 2+ days.

## Finding 7 — When 2 instruments ship same day, the stronger absorbs the weaker
Sitar beats any co-shipped instrument by 3–11×. Reinforces Finding 2 — don't co-ship a hero with anything you want to perform.

## Finding 8 — The one-off giants are non-repeatable surge artifacts; only Sitar repeats
Every instrument's single biggest video was born in the **May 5–9 algorithmic discovery surge** (channel-wide daily impressions ramped 164K → 1.35M that week). None of these lanes replicated afterward:

| Instrument | The one giant | When | Every ship after |
|-----------|--------------|------|------------------|
| Bansuri | 1.2M (Sleep) | May 7 | 38K, 155K, 35K, 10K |
| Dilruba | 2.1M (Morning Energy, Raga Yaman) | May 9 | **37K (May 19, SAME lane), 28K** |
| Sitar | 701K (Nervous System) | May 5 | 164K, 224K, 388K, 111K — **kept producing** |

- **Dilruba Morning Energy was explicitly re-attempted on May 19 ("Uplifting Music | Dilruba for Morning Energy") → 37,664 impr — a 98% drop.** The lane does not replicate. Do NOT plan around copying it.
- The giants were the *surge* lifting everything, not the lane/instrument/raga. When the surge normalized, Bansuri and Dilruba fell to their true ~30-40K level and stayed.
- **Sitar is the ONLY repeatable hero** — its audience keeps refreshing; the others were captured once and saturated.

**Rule:** You cannot manufacture winner #4 by copying a one-off windfall. The only real levers to raise the floor: (1) Sitar's repeatable weekly engine, (2) genuinely new formats — 3-hour long-form is the one fresh, non-surge signal (155K + 6.17% CTR, channel's highest, on otherwise-tired Bansuri).

---

## Net planning implications
1. Two clean spikes per week max — one per Monday. Build the week around two rested Monday heroes.
2. Sitar = the prize. Protect its cooldown (≥5d, ideally 8d) above all else.
3. Skip Wed + Sat for heroes. Tue/Thu/Sun = catalog days.
4. Don't double-ship for channel impressions. One ship/day.
5. Bansuri is now a strong-tier instrument on standard ships, not a hero — set expectations at 30–60K.

---

# Title / Thumbnail / Lane strategy (added 2026-05-31, from the June 1-8 locking session)

## Finding 9 — Offering > Problem framing (STRONG)
Titles that lead with what the music *gives* beat titles that name the *pain*, by a wide margin:

| OFFERING-led (what you get) | views | | PROBLEM-led (names the pain) | views |
|---|---|---|---|---|
| Morning Energy Music | 114K | | Mental Clarity / Brain Fog | 3.3K |
| Deep Rest Music | 41K | | Restless Mind | 2.0K |
| Anxiety Relief Music | 10K | | Tired Mind | 0.8K |
| Comfort Music | 7.8K | | Brain Fog? | 0.2K |

**Every problem-led title is <3.3K; every offering-led one beats it.** Rule: lead with the offering/outcome ("Restore Your Mind", "Emotional Comfort", "Deep Rest"), not the complaint ("Drained Mind", "Heavy Heart", "Overthinking").

## Finding 10 — Cannibalization hurts the NEWCOMER, not the old winner
Reusing a lead/lane that already has a catalog winner = the **new** video competes against your own established authority and loses. Surbahar deep-rest lane on repeat: **836K (Apr28) → 41K (May21) → 22K (May27).** "The old one is still getting views" = that query is **owned** = do NOT reuse it; pick a **fresh** lead to open a new query and expand coverage. Manufacture winner #4 by opening unclaimed ground, not by re-fighting owned ground.

## Finding 11 — Diversify LANES across the week (segmentation is uncertain) ⭐
We do not actually know YouTube's segmentation. Recommendation is **viewer-based collaborative filtering**, not clean "lane×instrument buckets." Practical consequence: a **lane-concentrated week competes internally for the same viewer pool** (Finding 2 — "doubles don't add" — scaled to the whole week). Sitar's cross-lane consistency (100–388K across dopamine/cortisol/brain/morning) suggests **instrument-following is real**, so instrument spread is good — but **instrument diversity ≠ lane diversity.** Plan each week as a deliberate **lane SPREAD** (anxiety / cognitive / sleep / emotional / cortisol / morning-energy / relaxation), NOT 8 shades of "calm." A single-lane-heavy week is a concentration bet that only pays off if you're dominating that lane with a *fresh* winner — which "calm" is not.

## Finding 12 — Match lane to BOTH time-of-day AND runtime; AVD is the engine, impressions are downstream ⭐
Proven the hard way by the May 31 ship: **Sitar 3hr "mental clarity / unclog brain," launched Sunday PM.** CTR was fine (3.5% = channel avg) but **AVD = 14:00 → only ~7.8% of a 3hr video, and BELOW the channel's ~17.5-min blended norm.** Result: 5.2K impressions at 14h — a below-baseline ship.

Three rules fall out of it:

- **Lane × time-of-day must fit.** Cognitive / clarity / focus = a **morning / weekday-daytime** intent (a *task* mindset). Do NOT ship it Sunday evening — that audience is in wind-down mode and won't engage, so retention craters. Evening = wind-down / anxiety / sleep / emotional. Morning = energy / focus / clarity.
- **Lane × runtime must fit.** **3-hour long-form ONLY for true long-session lanes — sleep, deep rest, study/deep-work background** — where viewers leave it running for hours. For cognitive / evening / anxiety / emotional, use **1.5hr**; those are shorter-session intents and the extra 90 min just tanks AVD%. (Contrast: May 17 "3hr Bansuri Relaxation / Deep Sleep" = 155K, 6.17% CTR — 3hr *worked* because sleep is a genuine long-session use-case.)
- **AVD is the engine; impressions are a symptom.** Weak retention → weak watch-time/session signal → the algo won't expand → low impressions. A fresh ship's low impressions are usually *caused by* soft AVD, not a separate distribution quirk. **Judge a new ship on CTR + AVD, never the impression count.** And for long-form, judge AVD in **absolute minutes vs the runtime** (target ~25–45+ min for a 3hr), not the channel's blended ~17.5-min %.

**Rule:** match the format to the *session length the lane implies*, and the lane to the *slot's browse intent*. 3hr = sleep/deep-rest/study only. Cognitive = morning/daytime + 1.5hr. When a ship underperforms, look at AVD first — if CTR is fine, do NOT swap the thumbnail.

## Operating rules (title + thumbnail)
- **Calm/healing lane thumbnails:** offering / abstract-noun / outcome-state WIN; Q-hooks LOSE (DECISIVE; A/B Test 12: "EMOTIONAL HEALING" beats "HEAL YOUR HEART" 52/48). Use "FEEL BETTER", "FIND PEACE", "RESTORE", "DEEP MEDITATION" — not "DRAINED?", "HEAVY HEART?".
- **"Healing Music" as a lead underperforms** (1.4–7.8K; the good ones were carried by *other* lead words like Comfort/Nervous System). Avoid the generic Healing Music lead.
- **Don't burn an A/B re-testing a known answer.** Reserve A/B for genuinely untested questions — e.g., keyword × *slot* novelty ("Meditation Music" had only run AM → trying it PM is a real test).
- **Track word-saturation across the WHOLE week**, not per-title. Cap repeated theme-words (calm / mind / relax). "Calm" hit 4× in the June 1-8 plan — too many.
- **Lead with a phrase, not a single abstract word** ("Solace Music" not bare "Solace") — matches the channel's lead pattern.
- **Binaural tag does NOT belong in the Suno prompt** (it's a post-production layer). Keep binaural spec in `production_spec` only; the actual winning prompts never request it.

## Per-ship lock checklist (run before locking each ship)
1. **VidIQ on the lead** (paste-bank fresh phrases; ≥~55 acceptable for fillers, prefer higher)
2. **Overlap scan** — vs live REACH_HISTORY titles + this week's briefs + the SAME instrument's title history (catch twins like "Music for Morning Anxiety" / "Release the Day" vs "Let Go of the Day")
3. **Week-wide word-saturation** — don't pile the same theme-word
4. **Cooldown** — instrument ≥5d (≥3-4d only on a genuine lane-switch)
5. **Thumb format vs lane A/B rules** (thumbnail_format_rules.json — calm/healing = offering/outcome, not Q-hook)
6. **Offering-not-problem framing** on the lead

## Net planning implications (extended)
6. **Offering-framed leads only** — never lead with the problem/pain word.
7. **Fresh leads, not reused winners** — opening new queries grows the catalog; re-fighting owned queries sinks the newcomer.
8. **Lane spread > lane concentration** — diversify the week's lanes (hedge against unknown segmentation), even while keeping instrument diversity.

---

## ⏳ OPEN EXPERIMENT — full-volume vs lean (decide for the week AFTER June 1-8)
**June 1-8 is a deliberate full-volume test:** 10 ships (1+/day + Tue/Thu doubles). Hypothesis (from Findings 1-2): all that volume will **NOT** beat the ~1.2M/day catalog floor + the two Monday heroes — most ships just compete for the same pool. **Decision rule:** capture daily channel impressions (the "Content type … Totals.csv" export) across June 1-8; if the weekly total doesn't clearly beat the floor, **go LEAN next week** — 1 ship/day, skip the dead days (Wed/Sat for heroes), and put the saved effort into manufacturing a catalog winner #4 (Sitar engine + 3-hour long-form). **Must paste the daily Totals CSV to make this call.**

---

## ⭐ Findings banked 2026-06-04 (from first per-video × per-day impressions export: May 26 – Jun 2, N=12 ships covered)

### Finding 13 — 7-day patience window (not 48 hours)
Channel was previously judging new ships on 48-hour data. The per-day data shows this is wrong: **Music for Morning Anxiety Sarod (May 28)** decayed from 20K → 14K → 10K → 7K through day 4, looking like a normal failure. Then on **day 5 it recovered to 13K, holding 13K through day 6** — algorithm gave it a second push driven by its 32% AVD.

**Rule:** Do not declare a ship a failure or pull its thumbnail/title before day 7. If AVD ≥ 27% and CTR ≥ 3.5%, the algorithm may re-push the ship in the day 5-7 window. Pulling early forfeits the recovery.

**Exceptions where 72h is enough:** day-1 impressions <8K AND AVD <18%. That combo never recovers (Surbahar Rest Your Mind, Sitar 3hr cognitive, Jun 1 Dilruba — all matched this pattern, all stayed dead).

### Finding 14 — Cannibalization is fatal within 4 days (Surbahar evidence)
**Surbahar "Rest Your Mind" (May 27)** had the worst observed decay curve in the export: **12K → 6K → 3K → 1K → 1K → 1K → 1K**. Dead by day 4, flat at 1K for 4 more days. This is in the same deep-rest/Surbahar lane as the April hero "Deep Rest Music | Find Stillness with Surbahar" (797K impressions lifetime, still earning 2K+/day).

**Rule:** Never reuse an instrument + lane pair where the channel already has a >500K-impression hero, UNLESS the new ship leads with a clinically different sub-lane (anxiety vs deep-rest, cortisol vs sleep, etc.). Same-lane same-instrument NEW ships will be killed by the old hero within 4 days. The cannibalization isn't "splits the audience 50/50" — it's "algorithm starves the newcomer entirely."

**Audit list to apply this rule:** Surbahar deep-rest (owned), Sitar cognitive/dopamine (owned by Dopamine Reset), Bansuri sleep (owned by Sound Sleep), Dilruba morning energy (owned by Yaman Morning), Bansuri morning productivity (owned by Productive Day).

### Finding 15 — Algorithm preference is narrower than expected (1-2 growth slots at a time)
In 14 days of new ships (N=10), only **Sitar Morning Right (May 26)** is in true growth mode (32K → 38K day 1 → day 8 = accelerating). One other ship is in recovery (Morning Anxiety Sarod). The remaining 8 ships are in normal-to-severe decay.

**Implication:** The algorithm appears to hold open ~2 "growth slots" for new content at any time. Trying to ship 8-10 new videos/week to fill those slots doesn't multiply impressions — they just compete for the same 2 slots. **This data argues for LEAN — ship fewer, better-targeted videos, give each one a real shot at the growth slot.**

### Finding 16 — Day-1 impressions are a strong predictor (but not deterministic)
Across the N=10 cohort:
- Day-1 ≥20K → 2/2 ended hero-tier or near-hero (Sitar Morning Right, Morning Anxiety Sarod, Sarod Clear Your Head)
- Day-1 12K-20K → variable (Surbahar Rest Your Mind died; Sleep Bansuri held)
- Day-1 5K-12K → 4/5 dead by day 7 (Yoga Sarangi, Good Energy Santoor, Dilruba, Sitar 3hr)
- Day-1 <5K → none recovered

**Rule:** Day-1 impressions below 8K = strong signal the title/thumbnail isn't earning the algorithm push. Don't wait for recovery on these — pull the thumbnail for an A/B retry and ship the next slot fresh.

### Finding 17 — Title patterns that fail to earn day-1 push
From the 4 weakest day-1 ships in the cohort (all <8K day 1):
1. **"Calming Music for Anxiety | Slow Bansuri | Indian Classical" (Jun 2 Bansuri, 7K day 1)** — calm-saturated week + generic "Calming" lead
2. **"Deep Relaxation | Release the Day | 1.5 Hours Dilruba Instrumental" (Jun 1 Dilruba, 7K day 1)** — instrument suffix in slot 3 is unusual on this channel + "Deep Relaxation" generic
3. **"Sitar to Unclog Your Brain | Instrumental Music | 3 Hours" (May 31 Sitar, 6K day 1)** — format/lane mismatch (cognitive lane + 3hr)
4. **"Good Energy Music | Santoor for Positive Vibes | 1.5 Hours" (May 28 Santoor PM, 5K day 1)** — PM slot for AM-only lane

**Banked title-pattern anti-rules:**
- Calm-family lead in a calm-saturated week (4+ calm leads in 7d) → day-1 push is ~50% of normal
- Instrument descriptor in slot 3 ("...Dilruba Instrumental" suffix) → underperforms "Instrument | Outcome | Duration" structure
- Wrong format-lane pair (cognitive + 3hr, uplifting + PM) → no day-1 push regardless of title quality
- "Generic emotional-word + Music" leads (Calming, Soothing, Deep Relaxation as bare phrases) → weakest day-1 impressions


### Finding 18 — Upload "room"/spacing has NO independent effect at hour granularity (tested 2026-07-05)
Hypothesis (user): more hours of room before the next upload → better impressions for the live video.
Test: exact publishedAt timestamps backfilled via Data API for all 106 uploads (`data/publish_times.csv`),
joined to earliest 1-14d launch capture, impressions normalized per day live. n=98 full-length ships.

- **Surge era (≤May): correlation is NEGATIVE** (Spearman −0.21 to −0.31) — confounded by deliberate
  double-placement on hot Mon/Tue hero days, but clearly no positive room effect.
- **Decay era (Jun+): apparent +0.25 collapses on inspection** — the 29-44h "room" bucket is n=3 and
  ALL are AM ships. In the fixed AM(07:00)/PM(19:00) grid, room is **collinear with slot**:
  AM→next-day-PM = 36h, PM→next-day-AM = 12h. "36h room" ≈ "AM ship" — the already-banked
  AM>PM(+70% median) + Monday + hero effects explain it. Tue–Fri decay-only Spearman = +0.09 ≈ zero.
- Counter-example: top decay-era launcher (Clear Your Head Sarod, 34.8K impr/day, Jun 2 AM) had only
  12h room on BOTH sides (double day).
- **Rule: do NOT plan around inter-upload spacing at 1/day cadence.** Slot-by-intent (Finding 12) and
  viewer-pool separation (§2 pools) already capture the real mechanism (same-pool push competition).
  Skipping a day to "make room" costs a slot for an effect indistinguishable from zero.
- **Open natural experiment:** Fri ships get ~60h weekend room for free under Mon-Fri cadence. Compare
  Fri vs Mon-Thu day-2/day-3 impression retention after 3-4 weeks before revisiting.

### Finding 19 — Cannibalization decomposed: INSTRUMENT spacing + LEAD-PHRASE ownership, NOT lane labels (tested 2026-07-06)
2x2 scan, n=73 ships (exact timestamps × earliest 1-14d launch capture, impressions/day):
- Same INSTRUMENT within <=4d (lane fresh): **1,346/d vs 5,133/d baseline — ~4x penalty [n=4]**.
  Independently consistent with the §3 Sitar gap table (39K @3d vs 139K @5d). Two methods agree.
- Same coarse LANE within <=4d (instrument fresh): 6,826/d [n=33] — **no penalty**.
- Known cannibalization deaths were LEAD-PHRASE/query-level, not lane-level: Tanpura "Sound Sleep"
  6d after the Bansuri "Sound Sleep" owner → 2.2K views (different instrument, same phrase);
  Surbahar "rest"-phrase sequence vs its own owner (836K→41K→22K).
- Working model: (a) same instrument too soon = same sound-audience pool split + feed sameness →
  day-scale spacing penalty; (b) same lead phrase as a BIG catalog owner = newcomer loses the
  ranking fight at any spacing; (c) coarse lane repeat costs nothing measurable.
- **Rules:** keep the 5-day instrument cooldown (best-supported rule we have) · enforce freshness at
  the LEAD-PHRASE level vs catalog owners (4-source conflict check) · do NOT block plans on
  lane-label repetition alone. Caveat: penalty cell n=4 — direction solid, magnitude soft.

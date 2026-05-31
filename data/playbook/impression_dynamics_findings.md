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

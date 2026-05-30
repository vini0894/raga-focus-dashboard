# A/B Test Reference — Title & Thumbnail Decision Guide

**N=32 tests (23 concluded, 8 running, 1 superseded) · Last updated: 2026-05-30 · Next update due: when any running test concludes**
Raw data: `ab_raw_data.csv` · Full verdicts: `ab_results.csv`

Use this doc before writing any brief. Start with the two quick-reference tables, then check the universal rules, then check open questions for your specific lane.

---

## TABLE 1 — Thumbnail Text by Lane

| Lane | ✅ Use | ❌ Avoid | Confidence | Evidence |
|---|---|---|---|---|
| **Focus** | Outcome-imperative (BOOST YOUR FOCUS, START YOUR DAY STRONG) | Q-hook | HIGH | #5 (73/27) |
| **Morning** | Outcome or lifestyle (FRESH START, WAKE UP PEACEFULLY, CALM MORNING VIBES) | Q-hook — 0 wins across 5 tests | VERY HIGH | #12,17,20,22,23 |
| **Sleep** | Intent-descriptor (SLEEP MUSIC, DRIFT TO SLEEP, FALL ASLEEP FAST) | Problem-state Q-hook (TOO TENSE TO REST?, DEEPLY DRAINED?) | MEDIUM | #13,15,24 |
| **Cognitive-Clarity** | Mental-state Q-hook (MENTALLY EXHAUSTED?, MIND WON'T STOP?) | Statement/declarative (RESET YOUR THOUGHTS) | HIGH | #16 (63/37) |
| **Relaxation / Evening** | Mental-state Q-hook (STRESSED?) | Generic outcome (RELAX DEEPLY) | MEDIUM-HIGH | #14 (55/45) — clean isolation |
| **Overthinking** | Specific mental Q-hook (TOO MANY THOUGHTS?) | Generic outcome (THINK LESS) | MEDIUM | #8 — confounded |
| **Burnout / Stress** | Permission-statement (IT'S OKAY TO REST, REST WITHOUT WORRY) — strongest signal in rest lanes | Generic outcome or exhaustion-descriptor | MEDIUM | #29 (58.6/41.4 decisive), #11 tie, #26,27 running |
| **Deep Rest** | Soft lifestyle (BREATHE & RELAX) | Urgent Q-hook (NEED DEEP REST?) | LOW — running | #2,23 |
| **Calm / Stillness** | No signal — format-tolerant | — | NONE | #21 concluded tie |
| **Comfort / Emotional** | No signal — format-tolerant | — | NONE | #6 tie, #30 tie |
| **Healing / Nostalgia** | Abstract emotional noun (EMOTIONAL HEALING) | Imperative (HEAL YOUR HEART) | LOW-MEDIUM | #10 concluded 53.8/46.2 — user stopped, variables not isolated |
| **Uplifting / Positive-Vibes** | Not yet tested (thumbs were identical in Test 32) | — | NONE — pending | #32 title-only clean test; thumb untested |

**Key thumb pattern:** Q-hooks work when they name a *mental/cognitive* state (STRESSED?, MENTALLY EXHAUSTED?, TOO MANY THOUGHTS?). They lose when they name a *physical exhaustion or time-of-day* state (TIRED?, FEELING LOW THIS MORNING?, TOO TENSE TO REST?). Lane matters — but so does the *type* of Q-hook.

---

## TABLE 2 — Title Type by Lane

| Lane | ✅ Use | ❌ Avoid | Confidence | Evidence |
|---|---|---|---|---|
| **Focus** | SEO-led (Instant Focus Music \| ...) | Q-hook lead (Need Energy Reset? \| ...) | HIGH | #5 |
| **Morning** | Lifestyle/mood SEO (Morning Energy Music, Morning Motivation) | Practice/utility (Breathing Exercise Music) | HIGH | #12,17,25 |
| **Sleep** | Clinical SEO (Insomnia Relief Music \| ...) | Sleep-outcome word as lead (Sound Sleep \| ...) | MEDIUM | #15 |
| **Cognitive-Clarity** | Clean SEO 3-slot (Mental Clarity Music \| Slow Sitar \| Brain Detox) | Q-hook lead or duration-led (1.5 Hour Sitar to...) | HIGH | #16,19 |
| **Burnout / Stress** | Plain-language state (Restless Mind, Stress Relief Music) | Clinical jargon (Adrenaline Reset) or duration-led | MEDIUM | #3,26,27 |
| **Relaxation / Anxiety** | SEO-led, pick higher VidIQ score when choosing between two | Lower-VidIQ variant | MEDIUM | #8,14 |
| **Overthinking** | Higher-VidIQ SEO (Meditation Music for Overthinking) | Lower-VidIQ variant (Overthinking Music) | MEDIUM | #8 — confounded |
| **Deep Rest** | SEO-led (Deep Rest Music, Deep Relaxation Music) | Lifestyle phrase (Unwind After Work) | LOW | #2 |
| **Calm / Healing** | Short clean SEO, 3 slots, no stuffing | Long/stuffed (Hz, Schumann, binaural in title) | MEDIUM | #1 (68/32) |
| **Healing / Nostalgia** | SEO descriptor (Nostalgia Music \| ...) | Instrument-led + poetic phrase | LOW-MEDIUM | #10 concluded 53.8/46.2 — user stopped, variables not isolated |
| **Comfort / Emotional** | No signal | — | NONE | #6,7 |
| **Uplifting / Positive-Vibes** | Energy-descriptor lead (Good Energy Music) + specific vibe descriptor in slot 2 (Positive Vibes) | Generic-feeling lead (Feel Good Music) + instrument-category in slot 2 (Instrumental) | MEDIUM | #32 (58.9/41.1 — clean title-only, 17.8pp decisive) |

---

## UNIVERSAL RULES — Apply to every lane, every brief

### Titles
| Rule | Record | Confidence |
|---|---|---|
| Q-hook as title lead loses across all lanes | 0–3–1 (only tie was comfort/emotional lane) | HIGH |
| 3-slot clean title beats long/stuffed title | 2–0, margins 68/32 and 62/38 | HIGH |
| Higher VidIQ score wins when both titles are SEO-led in the same lane | 2–0 | MEDIUM |
| Duration as title lead (1.5 Hour Sitar to...) is weak | 0–1 | MEDIUM |
| IFO format (Instrument for Outcome) ties but never wins outright | 0–0–2 | MEDIUM |

### Thumbnails
| Rule | Record | Confidence |
|---|---|---|
| Q-hook belongs in the **thumb**, not the title lead — same energy, different placement wins | Multiple tests | HIGH |
| Generic outcome thumbs (RELAX DEEPLY, THINK LESS, RESTORE YOUR ENERGY) are weak | 0 clean wins | MEDIUM — see caveat below |
| Mental-state Q-hooks win across multiple lanes; physical/morning Q-hooks lose | Pattern across 9 tests | MEDIUM-HIGH |

**⚠️ Caveat on generic outcome thumbs:** The "0 wins" finding is only cleanly isolated in Test 14 (thumb-only, RELAX DEEPLY lost to STRESSED? 45/55). In Tests 2 and 8, the losing side also had a weaker title — so the title may have done most of the damage, not the thumb. Do not treat this as a hard rule yet. A thumb-only test with a strong title on both sides would confirm it.

---

## CONFIDENCE TIERS — How much to trust each rule

| Tier | What it means | How to use |
|---|---|---|
| **HIGH** | 2+ tests with decisive margins (>10pp) or 1 clean isolation with large gap | Follow without hesitation |
| **MEDIUM** | Consistent direction but confounded variables or small margins | Default to this, but don't stake a swing on it alone |
| **LOW** | 1 test, still running, or marginal gap (<5pp) | Directional only — treat as a lean, not a rule |
| **NONE** | Tie or no tests | Format-tolerant lane — content quality dominates, pick what feels right |

---

## OPEN QUESTIONS — Don't treat these as settled

| Question | Why it's open | Test needed |
|---|---|---|
| Does intent-descriptor thumb beat Q-hook in sleep cleanly? | Test 24 (SLEEP MUSIC) is confounded — title is also different phrasing style | Thumb-only: DEEP SLEEP NOW vs CAN'T FALL ASLEEP? |
| Does permission thumb beat Q-hook in a clean isolation? | Test 29 (REST WITHOUT WORRY, 17.2pp win) is confounded — title also changed. Strong directional signal but needs thumb-only test | Thumb-only with same title: REST WITHOUT WORRY vs BURNED OUT AND TIRED? |
| Does morning anti-Q-hook rule hold with better isolation? | Test 28 (Morning Santoor) saw YT promote NEED A BOOST? Q-hook despite near-tie — 5 prior tests showed outcome wins. May be title-driven not thumb-driven | Thumb-only morning test: MORNING BOOST vs FEEL UNMOTIVATED? |
| Do mental Q-hooks beat physical Q-hooks in the same lane? | Pattern is suggestive across tests but never isolated | Same lane/title: MIND WON'T SLOW DOWN? vs BODY FEELS HEAVY? |
| Does plain-language state beat clinical jargon in burnout title? | Test 26 confounded (title + thumb both changed) | Title-only: Exhausted Mind \| Slow Veena vs Nervous System Reset \| Slow Veena |
| Are permission thumbs (IT'S OKAY TO REST) a winning category vs Q-hooks? | Only leading marginally in one running test | 3-way thumb test: IT'S OKAY TO REST vs BURNED OUT AND TIRED? vs RELEASE THE TENSION |
| Does a strong title rescue a generic outcome thumb? | Generic outcome thumb finding only cleanly proven once | Thumb-only with proven strong title: STRESSED? vs RELAX DEEPLY |
| Deep rest lane thumb rule | Test 23 running (BREATHE & RELAX vs NEED DEEP REST?) | Wait for conclusion |
| Morning lane title — does lead keyword VidIQ score drive the result? | Test 25 near-tie (both SEO-led, 50.4/49.6) | Title-only: higher-VidIQ morning lead vs lower-VidIQ morning lead |

---

## CURRENTLY RUNNING TESTS — Don't draw conclusions yet

These are active. Scores shown are directional only — wait for "Test finished" before banking any rule.
**Scores last captured: 2026-05-28. Paste new screenshots to update.**

| # | Video | Lane | What's being tested | A | A score | B | B score | Leading | Time left |
|---|---|---|---|---|---|---|---|---|---|
| 9 | Cortisol Reset Sitar | Stress/Reset | Title-only | Calm Music \| Sitar for Cortisol Reset \| 1.5 hours | 51.5% | Sitar Healing Music \| Calm Your Stress \| Find Stillness | 48.5% | A | Unknown — may have concluded |
| ~~16~~ | ~~Brain Fog Sarod~~ | ✅ CONCLUDED May 15–18 | B won 62% vs 38% — Mental Clarity Music + MENTALLY EXHAUSTED? crushed Q-hook title + statement thumb | — | — | — | — | — | — |
| 17 | Morning Motivation Sitar | Morning/Motivation | Title+Thumb | Morning Motivation \| Sitar Music Instrumental + START YOUR DAY STRONG | 59.1% | Day Start Music \| Calming Sitar for a Positive Day + FEELING UNMOTIVATED? | 40.9% | A | Unknown — may have concluded |
| 22 | Morning Tanpura | Morning | Thumb-only | WAKE UP PEACEFULLY | 56.6% | RUSHED MORNING? | 43.4% | A | ~9d |
| 23 | Deep Relaxation Surbahar | Deep Rest | Thumb-only | NEED DEEP REST? | 48% | BREATHE & RELAX | 52% | B | ~10d |
| 24 | Bansuri Unwind | Sleep/Relaxation | Thumb-only | SLEEP MUSIC | 51.4% | TOO TENSE TO REST? | 48.6% | A | ~11d |
| 25 | Morning Reset Sarod | Morning | Title-only | Morning Reset Music \| Clear Your Head with Sarod Instrumental \| 1.5 hours | 49.6% | Morning Reset Music \| Slow Sarod \| Clear Your Head | 50.4% | B (near tie) | ~12d |
| 26 | Restless Mind Veena | Burnout/Rest | Title+Thumb | Restless Mind \| Slow Veena \| 1.5 Hours of Rest + BURNED OUT AND TIRED? | 52.8% | Adrenaline Reset \| Slow Veena \| 1.5 Hours + EASE DOWN | 47.2% | A | ~12d |
| 27 | Santoor Stress Relief | Stress Relief | Title+Thumb | Stress Relief Music \| Santoor Instrumental \| 3 Hours + IT'S OKAY TO REST | 51.8% | 3 Hour Santoor Music for Stress Relief \| Indian Instrumental Classical Music + FEELING DRAINED? | 48.2% | A | ~13d |

**Recently concluded (banked 2026-05-30):**

| # | Video | Lane | Result | Winner | Loser | Margin |
|---|---|---|---|---|---|---|
| 32 | Santoor Positive Vibes | Uplifting/Positive-Vibes | ✅ CONCLUDED May 28–30 (user stopped) | Good Energy Music \| Santoor for Positive Vibes \| 1.5 Hours | Feel Good Music \| Santoor Instrumental \| 1.5 Hours | 58.9% vs 41.1% (17.8pp) — ⭐ clean title-only isolation, specificity in slot 2 wins |
| 16 | Brain Fog Sarod | Cognitive-Clarity | ✅ CONCLUDED May 15–18 | Mental Clarity Music \| Slow Sarod \| Brain Fog Reset + MENTALLY EXHAUSTED? | Can't Think Clearly? \| Sarod for Mental Reset + RESET YOUR THOUGHTS | 62% vs 38% (24pp) |
| 28 | Morning Santoor | Morning | ✅ CONCLUDED May 14–17 (tie) | Morning Energy Music \| Santoor Instrumental \| Positive Vibes + NEED A BOOST? (YT promoted) | Start Your Day \| Santoor for Morning Energy + START YOUR DAY | 52.1% vs 47.9% — format-tolerant tie, ⚠️ confounded |
| 29 | Surbahar Rest | Burnout/Rest | ✅ CONCLUDED May 15–20 (user stopped) | Sound Healing Music \| Slow Surbahar \| 1.5 Hours of Rest + REST WITHOUT WORRY | Healing Frequency Music \| Slow Surbahar + FOR DRAINED MINDS | 58.6% vs 41.4% (17.2pp) — ⭐ strongest permission thumb signal |
| 30 | Sarangi Emotional Release | Emotional/Stress | ✅ CONCLUDED May 20–24 (tie) | CARRYING TOO MUCH EMOTION? (YT promoted) | HEAVY HEART? | 48.6% vs 51.4% — format-tolerant tie, ⚠️ confounded |

**⚠️ Tests 9 and 17** — started May 12–16, no recent screenshot. May have concluded. Paste latest screenshots to update.

---

## NEXT TESTS TO RUN — Hypotheses queued

These are gaps in the data worth structuring a deliberate test around. Set these up on the next relevant ship.

| Priority | Hypothesis | Lane | Test design | What it will settle |
|---|---|---|---|---|
| 🔴 1 | Intent-descriptor thumb beats Q-hook in sleep lane cleanly | Sleep | Thumb-only: **DEEP SLEEP NOW** vs **CAN'T FALL ASLEEP?** | Whether sleep lane is intent-match or just anti-Q-hook |
| 🔴 2 | Permission thumb beats both Q-hook and outcome-imperative — **now strongly supported by Test 29 (REST WITHOUT WORRY, 17.2pp win)** | Burnout/Rest | 3-way thumb-only: **IT'S OKAY TO REST** vs **BURNED OUT AND TIRED?** vs **RELEASE THE TENSION** | Isolates permission as a distinct category (Test 29 was confounded — title also changed) |
| 🟡 3 | Mental-state Q-hook beats physical-exhaustion Q-hook | Any rest lane | Thumb-only: **MIND WON'T SLOW DOWN?** vs **BODY FEELS HEAVY?** | Explains why some Q-hooks win and others lose |
| 🟡 4 | Plain-language state beats clinical jargon in burnout title | Burnout | Title-only: **Exhausted Mind \| Slow Veena \| 1.5 Hours** vs **Nervous System Reset \| Slow Veena \| 1.5 Hours** | Settles title lead style for burnout lane |
| 🟢 5 | Strong title rescues generic outcome thumb | Any lane | Thumb-only with proven strong title: **STRESSED?** vs **RELAX DEEPLY** | Confirms whether generic thumb finding is real or title-confounded |

---

## QUICK CHECKLIST — Before locking title + thumb in any brief

**Title:**
- [ ] Is the lead slot SEO-led or lifestyle/mood? (Not Q-hook, not duration, not practice/utility)
- [ ] Is it 3 slots? (Not 2, not 4+)
- [ ] Is the lead keyword the highest VidIQ score available for this lane?
- [ ] No Hz, wave type, raga jargon stuffed in?

**Thumbnail:**
- [ ] Is the thumb type right for the lane? (Check Table 1)
- [ ] If using Q-hook: is it a *mental/cognitive* state? (Not physical exhaustion or time-of-day)
- [ ] Avoiding generic soft outcomes? (RELAX DEEPLY, THINK LESS, LET YOURSELF REST — treat as weak until proven)
- [ ] Mobile readable? (2–3 words, 14–18 chars)
- [ ] Thumb energy matches music energy? (No mismatch between anxious thumb + calm music)

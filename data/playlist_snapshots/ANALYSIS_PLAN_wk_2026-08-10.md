# Playlist routing — analysis plan for the wk_2026-08-10 read

**Baseline:** `playlists_2026-08-07.json` (positions + per-video RPM/impressions/CTR at capture)
**Changes being measured:** user playlist shuffles on **2026-08-02** and **2026-08-07**
**Read on/after:** ~2026-08-16 (a full fortnight past the first change; analytics lags ~3 days)

---

## What changed

| playlist | videos | top 3 after the shuffles |
|---|---|---|
| Sleep Music | 21 | Sleep Through the Night · 3hr Bansuri Relaxation · Quiet Night |
| Peaceful Music | 48 | Dopamine Reset *(donor)* · Stress Relief Santoor · Mental Clarity Sarod |
| Healing & Anxiety Relief | 40 | Nervous System *(donor)* · Peace of Mind · Stress Relief Santoor |
| Meditation Music | 28 | Dopamine Reset *(donor)* · Morning Gratitude · Calm Your Mind |
| Morning Energy | 24 | Morning Energy *(donor)* · Morning Right · Productive Day |

Peaceful Music grew 42 → 48 and Healing 37 → 40 across the two sessions.

---

## ⚠️ Measure at CHANNEL level, not per video

This is the main lesson from the 2026-08-07 attempt. Per-target playlist traffic runs **1–5 views/day**, and unmoved control videos swung **−56% to +19%** over the same window. Everything is inside the noise. Per-video counts will never resolve.

**The metric:** `insightTrafficSourceType == PLAYLIST` share of channel **watch-time**.

```
dimensions=insightTrafficSourceType, metrics=views,estimatedMinutesWatched
```

**Readings so far:**

| window | playlist % of views | playlist % of watch-time | playlist views/day |
|---|---|---|---|
| pre — Jul 28–31 | 4.94% | 8.92% | 1,163 |
| post shuffle 1 — Aug 2–4 | 5.27% | 9.44% | 1,313 |
| **post shuffle 2 — read ~Aug 16** | ? | ? | ? |

Use **share**, not absolute — the channel grew from ~21K to ~25K views/day across this period, so absolutes will rise regardless.

---

## Confounds that must be stated in the read

1. **New ships enter playlists.** Five shipped Aug 3–7, all added to playlists. Some of any share rise is new inventory, not better ordering. Check how much playlist traffic went to videos published after Aug 2.
2. **The channel inflected independently.** Daily views went 19,255 (Jul 25 trough) → ~25,000 (Aug 2–4). Rising tide, not the shuffle.
3. **Two shuffles, five days apart.** Aug 2 and Aug 7 can't be separated. Treat as one intervention.
4. **Aug-2 window was only 3 days.** The +0.33pp reading is soft.

---

## ⚠️ Do NOT rank on RPM alone

Measured 2026-08-07 across the sleep pool — every rising RPM belonged to a *shrinking* video:

| video | earn-rate | impressions |
|---|---|---|
| Quiet Night | 7.15 → 8.56 | 104k → **40k (−62%)** |
| Deep Sleep Surbahar | 5.55 → 6.58 | 62k → **31k (−50%)** |
| 3hr Bansuri Relaxation | 5.92 → 6.85 | 337k → **234k (−31%)** |
| **Sleep Through the Night** | 6.39 → 6.86 | 50k → **98k (+96%)** |

RPM rises as reach falls because the surviving audience is higher-intent. **Rank on RPM × impressions trend together.** Only Sleep Through the Night grew on both — which is why it was moved to position 1.

---

## Expected magnitude — keep it honest

The original modelled figure assumed 3× impressions on 17 starved targets. Total playlist traffic is ~1,313 views/day ≈ **36,800 per 28 days channel-wide**. Doubling that and landing all of it on the higher-earning targets is roughly **low hundreds**, not four figures.

**Treat this as a low-hundreds-per-month lever.** If the read comes back at +0.3–0.6pp of watch-time share, that is success, not disappointment.

---

## Checklist for the read

- [ ] Pull playlist share of views + watch-time for Aug 9–15, compare to the two rows above
- [ ] Split playlist traffic: videos published before vs after Aug 2 (isolates new-inventory effect)
- [ ] Re-pull positions and diff against `playlists_2026-08-07.json` — confirm the order still holds
- [ ] For the 3 videos moved to position 1–3, check impressions trend, not RPM
- [ ] State the confounds above in whatever conclusion gets banked

# Suno Prompt Patterns — Raga Focus

Last updated: 2026-05-30
Source: Analysis of channel's Suno prompt CSV vs actual YouTube view performance (N=17 videos)

---

## What the data shows

### Pattern 1: Physical instrument description is the #1 consistent marker
Every video above 25K views includes HOW the instrument sounds mechanically — not just the instrument name.

| ❌ Generic | ✅ Physical |
|---|---|
| "sitar melodies" | "warm plucked sitar with meend glissando slides and gamak ornamentation" |
| "bansuri flute" | "breath-driven bamboo flute with long sustained notes and natural breath pauses" |
| "santoor music" | "hammered dulcimer with characteristic bright percussive attack and warm resonant sustain" |
| "sarangi" | "expressive bowed sarangi like a human voice, slow emotional phrases" |
| "surbahar" | "deep resonant string tones, deep meend slides and gamak ornamentation with long pauses" |

### Pattern 2: Emotional direction beats generic mood tags
High performers describe how the music should FEEL to the listener — specific and visceral.

| ❌ Generic mood | ✅ Specific emotional direction |
|---|---|
| "meditative, calming, healing" | "like the body finally getting permission to put down the weight it has been carrying" |
| "peaceful, relaxing" | "like a window opening in a quiet room — clear light, no weight" |
| "stress relief mood" | "like the evening finally giving the anxiety somewhere to go" |
| "healing atmosphere" | "dopamine reset, inner stillness" |
| "grounding" | "like the body finding its own breath before the day asks anything of it" |

### Pattern 3: Named raga matters, especially for Sitar
All high-performing Sitar videos name the raga. Bansuri and Surbahar are more forgiving (instrument alone signals the genre). Include ONE defining characteristic of the raga alongside its name.

| Raga | Defining characteristic for prompt |
|---|---|
| Bhairav | flat 2nd and flat 6th, serious grounding morning quality |
| Bhairavi | deeply emotional, komal-dominant, cathartic evening feel |
| Bilawal | all-natural intervals, bright open ascending morning character |
| Bhupali | pentatonic, joyful, positive and light |
| Yaman | raised 4th (teevra Ma), expansive outward open evening character |
| Kedar | alternates natural and raised 4th, oscillating settling devotional quality |
| Darbari Kanada | heavy, komal-dominant, deep midnight gravity |
| Bageshri | late evening, longing, introspective |
| Khamaj | folk-ish, warm, earthy emotion |

### Pattern 4: Tabla presence correlates with Sitar performance
| Instrument | Tabla rule | Evidence |
|---|---|---|
| Sitar | Include light tabla | 764K, 11.8K, 9.7K all had tabla. Only no-tabla Sitar (8.3K cortisol May 11) was lowest |
| Bansuri | No tabla | 56K sleep, 35K productive, 15K sleep — all no tabla or minimal |
| Surbahar | No tabla | 40K deep rest — no percussion |
| Sarangi | No tabla | Works without, emotional instrument carries space |
| Santoor | Optional light tabla | Varies by lane |

---

## Format rules (confirmed by data + Suno documentation)

### Optimal length
- **Target: 400–650 chars** — all top performers are in this range
- Under 300: too vague, generic output
- Over 800: Suno ignores later tags, quality doesn't improve

### Two prompt formats — use A/B in brief, test which sounds better

**Format A — CSV reference style** (~550–650 chars)
Modelled on 764K Dopamine Reset and 44K Dilruba prompts. More descriptive, raga character + instrument physics + emotional metaphor integrated naturally. No-vocal can appear anywhere (data shows position doesn't strictly matter — 764K has it in middle, still 764K views).

Structure:
```
[Genre description], [Raga name + one defining note characteristic], [mood], [physical instrument description], [supporting instruments], [Hz tuning], [BPM], [register], [production quality], [loop spec], [emotional metaphor], [no vocals, no humming, no human voice]
```

**Format B — Suno docs compact style** (~370–430 chars)
Per Suno documentation: 8-15 focused comma-separated tags, "Instrumental only, no vocals" first.

Structure:
```
Instrumental only, no vocals, no humming, [genre + instrument], [Raga — defining characteristic], [physical instrument description], [supporting instruments], [Hz], [BPM], [binaural], [register], [production tags], [loop], [emotional metaphor]
```

### Always include
- Raga name + ONE defining characteristic
- Physical instrument description (not just instrument name)
- BPM range
- Hz tuning (432Hz standard)
- Binaural type + level (at -20dB)
- "no vocals, no humming, no human voice"
- Loop spec ("seamless loop" or "loop-friendly")
- One specific emotional metaphor (not generic mood words)

### Never include in Suno prompt (put in production_spec.notes instead)
- Full sargam notation (Sa Re Ga Ma Pa Dha Ni Sa) — team reference only
- Anti-duplication paragraphs ("must sound different from Darbari Kanada...")
- "IMPORTANT:" / "CRITICAL:" directives — Suno ignores these
- Multi-paragraph raga musicology explanations
- EMOTIONAL TAG ROTATION blocks — use one strong metaphor instead
- "do not replicate or reference any existing recording" — team note only

---

## Per-lane binaural rules

| Lane | Wave | Hz | Notes |
|---|---|---|---|
| Sleep / deep rest | Delta | 3 Hz | Drowsy, surrendering quality |
| Anxiety / emotional release | Theta | 5–6 Hz | Deep relaxation, not sleep |
| Morning / breathwork / clarity | Alpha | 10 Hz | Relaxed alertness, present and awake |
| Cortisol reset / nervous system | Alpha | 10 Hz | Parasympathetic activation |
| Focus / cognitive | Alpha/Gamma | 10–40 Hz | Depends on lane |

Standard binaural level: **-20dB** (barely audible underneath)

## BPM by lane

| Lane | BPM range | Notes |
|---|---|---|
| Deep sleep | 45–55 | Very slow, drone-like |
| Evening anxiety / emotional | 50–60 | Slow but present |
| Evening cortisol / nervous system | 65–75 | Has momentum, not sleep-slow |
| Morning breathwork | 60–70 | Unhurried, spacious |
| Morning clarity / cognitive | 70–80 | Forward movement without urgency |
| Morning energy / motivation | 85–95 | Upbeat but calm |

---

## View benchmarks (for reference when evaluating new outputs)

| Views | Prompt quality | Key observation |
|---|---|---|
| 764K | Named raga, BPM, instrument physics, emotional direction | Benchmark — dopamine reset lane |
| 56K | Instrument physics, no-vocal — no raga named | Bansuri sleep: instrument alone signals lane |
| 44K | All markers — most complete prompt in dataset | Best structured prompt |
| 25K | Very vague (267 chars, no raga) | Title/thumbnail drove views, not prompt |
| 8.3K | Complete prompt — but no tabla on Sitar | Tabla absence likely limited quality |

Key insight: **Views are driven by title/thumbnail first, music quality (prompt) second. But prompt quality shows up in AVD — better music = longer watch time.**

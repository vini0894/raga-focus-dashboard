"""Production queue — structured data for the next 7 Raga Focus videos.

Each video has the full production brief:
- Title, length, instrument, Hz, publish date
- Description (YouTube ready)
- Tags (comma-separated, under 500 chars)
- Suno music generation prompt
- Thumbnail image prompt (Midjourney/DALL-E ready)
- Thumbnail text overlay
- Strategic bet + success criteria
"""

VIDEOS = [
    {
        "id": "V1",
        "status": "not_started",  # not_started | in_progress | published
        "title": "Stop Overthinking | Sitar Meditation Music for Anxiety & Mental Stillness",
        "length": "55 min",
        "instrument": "Sitar + subtle tanpura drone",
        "hz": "10Hz Alpha binaural beats",
        "publish_date": "2026-04-19",
        "publish_time": "7 PM IST",
        "strategic_bet": "Shanti-style pattern clone without literal duplication. Tests 'Instrument For Problem' formula.",
        "validated_keywords": ["sitar music (75 HIGH)", "overthinking music (63 HIGH)", "anxiety relief music (74 HIGH)"],
        "description": """Stop Overthinking | Sitar Meditation Music for Anxiety & Mental Stillness

This sitar instrumental is created for overthinkers who can't switch off. Slow, expressive sitar phrases move at a steady, unhurried pace — giving your mind something calm and consistent to follow. The sound stays minimal and spacious, helping racing thoughts gradually lose momentum.

If you're replaying conversations, mentally jumping ahead, or stuck in a thought loop, this music offers a softer rhythm to settle into. Well suited for quiet evenings, meditation, journaling, or focused work that needs a clear head.

🎧 Ideal for:
 • Calming racing thoughts
 • Breaking mental loops
 • Anxiety relief sessions
 • Meditation and mindfulness
 • Gentle, sustained focus
 • Evening wind-down

Let the sitar guide your attention toward stillness and clarity.

💬 When does your overthinking hit hardest — morning, evening, or late at night?

🔔 Subscribe for more healing ragas and Indian classical meditation music.""",
        "tags": "meditation music, indian ragas, classical instrumental, sitar music, overthinking music, anxiety relief music, deep relaxation, calm focus, mindful practice, spiritual ambient, healing soundscape, stress relief, peaceful background, breathwork sessions, evening unwind, mental clarity, inner stillness, racing thoughts music, sitar meditation, indian classical anxiety",
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Slow meditative Indian classical sitar music, 55 BPM, deep resonant sitar lead, subtle tanpura drone undertones, minimal melodic phrases with long sustained notes, sparse and spacious, warm reverb, evening contemplative mood, designed for calming an overthinking mind and anxiety release, no vocals, no drums, no percussion, seamless loop structure [No Vocals]",
        "thumbnail_prompt": "Cinematic painterly illustration of a traditional Indian sitar resting on a soft indigo carpet, viewed from a low angle with a deep evening sky background featuring a prominent crescent moon and scattered stars, muted purple-indigo and soft lavender color palette, subtle haze in the air, shallow depth of field with sitar in sharp focus, warm lamp light glowing softly from bottom-left creating gentle rim light on the sitar, Studio Ghibli meets Lofi Girl aesthetic, peaceful contemplative evening atmosphere, no text overlay, 16:9 aspect ratio --ar 16:9 --style raw",
        "thumbnail_text_main": "STOP OVERTHINKING",
        "thumbnail_text_secondary": "SITAR · 10Hz ALPHA",
        "success_good": "500+ views, 3%+ CTR, 15%+ retention, 2+ subs gained (14 days)",
        "success_breakthrough": "2,000+ views, 5%+ CTR, 20%+ retention, 5+ subs gained",
    },
    {
        "id": "V2",
        "status": "not_started",
        "title": "Raga Yaman for Deep Sleep | Bansuri & Delta Waves | 1 Hour Session",
        "length": "1 hour",
        "instrument": "Bansuri (Indian bamboo flute) + ambient drone pads",
        "hz": "3Hz Delta binaural beats",
        "publish_date": "2026-04-30",
        "publish_time": "7 PM IST",
        "strategic_bet": "Sleep wedge — biggest market we've tested (Volume 94). Raga Yaman = authentic night raga + proper-noun SEO (62 Volume validated).",
        "validated_keywords": ["sleep music (94 HIGH)", "raga yaman (62 HIGH)", "bansuri music (56 HIGH, Very Low competition)", "delta waves (76 HIGH)"],
        "description": """Raga Yaman for Deep Sleep | Bansuri Flute + 3Hz Delta Binaural Beats | 1 Hour Night Session 🌙

In Hindustani classical tradition, Raga Yaman is played in the first watch of night — the raga of stillness, introspection, and surrender to sleep. This session layers Yaman's evening mood with 3Hz Delta binaural beats, the brainwave state of deep restorative sleep.

No mid-roll ads. No sudden shifts. One unbroken hour designed to carry you into the first deep sleep cycle.

🌙 Why this works for sleep:
• Raga Yaman's slow phrases are culturally coded for twilight and rest
• 3Hz Delta = the brainwave of deep slow-wave sleep
• Bansuri's soft breathy tone naturally slows your breath
• Pure instrumental — no lyrics to re-engage the mind

🎧 How to use:
Play at low volume as you lie down. Works with or without headphones. Let it run as you fall asleep — no sudden audio shifts to wake you.

⏱ Best for:
• Falling asleep when the mind won't settle
• Insomnia recovery
• Bedtime meditation before sleep
• Post-anxious nights
• Sleep anxiety

🌙 Subscribe for more deep sleep ragas and healing Indian instrumentals.

#ragayaman #sleepmusic #bansuri #deltawaves #indianclassicalsleep""",
        "tags": "raga yaman, sleep music, bansuri music, delta waves, indian classical sleep, hindustani classical, deep sleep music, insomnia music, sleep meditation, night raga, bansuri sleep, indian flute sleep, 3hz delta binaural, sleep raga, ragatherapy sleep, bansuri delta, classical sleep music, anxiety sleep music, tanpura sleep, 1 hour sleep music",
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Dreamy Indian bamboo flute (bansuri) music for deep sleep, 50 BPM, soft breathy flute tones in a major scale with raised fourth degree, distant ambient drone pads, very slow and unhurried phrases, long pauses between notes, nighttime meditation atmosphere, lush warm reverb, designed for falling asleep and insomnia relief, no vocals, no percussion, peaceful and grounding, smooth loop ending [No Vocals]",
        "thumbnail_prompt": "Cinematic painterly illustration of a traditional Indian bansuri bamboo flute resting on a moonlit windowsill, viewed with deep indigo night sky background dominated by a large luminous full moon and scattered bright stars, rich midnight blue and cool silver color palette, soft moonlight glow illuminating the flute, gentle misty atmosphere outside window, Studio Ghibli meets dreamy oil painting style, peaceful nighttime sleep atmosphere, no text overlay, 16:9 aspect ratio --ar 16:9 --style raw",
        "thumbnail_text_main": "RAGA YAMAN · SLEEP",
        "thumbnail_text_secondary": "BANSURI · DELTA WAVES",
        "success_good": "300+ views, 2%+ CTR, 25%+ retention (sleep = high retention baseline)",
        "success_breakthrough": "1,500+ views, 4%+ CTR, 40%+ retention (big watch time bank)",
    },
    {
        "id": "V3",
        "status": "not_started",
        "title": "Sitar 432Hz for Anxiety Relief | Deep Calm for Overthinking Minds | 1 Hour",
        "length": "1 hr 20 min",
        "instrument": "Sitar + ambient tanpura drone",
        "hz": "432Hz tuning + 10Hz Alpha binaural",
        "publish_date": "2026-04-24",
        "publish_time": "7 PM IST",
        "strategic_bet": "Anxiety hero. Raga Heal's Nervous System Cooldown got 337K views with this framing. Every validated keyword is HIGH.",
        "validated_keywords": ["anxiety relief music (74 HIGH)", "sitar music (75 HIGH)", "432hz music (76 HIGH, Low competition)", "overthinking music (63 HIGH)"],
        "description": """Sitar 432Hz for Anxiety Relief | Deep Calm for Overthinking Minds | 1 Hour

Slow your thoughts. Soften your body. Return to stillness. 🌿

This 432Hz Sitar meditation is designed to gently guide an anxious, overstimulated mind back into calm. The soothing resonance of the sitar, tuned to the calming frequency of 432Hz, creates a serene atmosphere for moments when anxiety and overthinking take over.

When racing thoughts or chronic mental tension take over, this extended soundscape offers your mind something quiet to rest against. The sitar's flowing melodies move slowly, without sudden shifts, creating safety that allows your nervous system to downshift.

✨ This music is designed to support:
• Anxiety relief and emotional balance
• Releasing overthinking and racing thoughts
• Softening chronic mental tension
• Meditation and mindfulness practice
• Gentle yoga and breathwork
• Quiet reflection or journaling
• Peaceful sleep ambience

🎧 How to use:
Find a quiet space. Headphones if you have them. Sit or lie down. Let your breath slow to match the music.

432Hz is often associated with natural resonance and emotional balance — a frequency many find helps soften inner noise.

🌿 Subscribe for more healing raga sessions.""",
        "tags": "anxiety relief music, overthinking music, sitar music, 432hz music, calm anxiety music, somatic healing, racing thoughts music, sitar 432hz, indian classical anxiety, meditation for anxiety, grounding music, healing ragas, sitar meditation, overthinker music, indian meditation music, stress relief music, 432hz healing, deep calm music, anxiety meditation music, sitar for anxiety",
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Soothing Indian classical sitar meditation, 60 BPM, warm resonant sitar with deep reverb, slow sparse melodic phrases, minimal tanpura drone underneath, ambient spacious atmosphere, gentle and contemplative mood, no sudden dynamic changes, designed for anxiety relief and racing thoughts, nervous system calming, no vocals, no drums, seamless infinite loop [No Vocals]",
        "thumbnail_prompt": "Cinematic painterly illustration of an Indian sitar placed on a low wooden table in a sage-green misty evening setting, deep teal-green and soft lavender color palette, small crescent moon visible in upper-left of sky with gentle haze, dewdrops on leaves in foreground, soft diffused light, calming serene atmosphere, Studio Ghibli aesthetic, meditative and grounding mood, no text overlay, 16:9 aspect ratio --ar 16:9 --style raw",
        "thumbnail_text_main": "ANXIETY RELIEF",
        "thumbnail_text_secondary": "SITAR · 432Hz",
        "success_good": "800+ views, 3%+ CTR, 15%+ retention, 3+ subs",
        "success_breakthrough": "3,000+ views, 5%+ CTR, 20%+ retention",
    },
    {
        "id": "V4",
        "status": "not_started",
        "title": "Bansuri for Deep Sleep | Delta Waves | 1 Hour Night Session",
        "length": "1 hour",
        "instrument": "Bansuri (bamboo flute) + ambient drone pads",
        "hz": "3Hz Delta binaural beats",
        "publish_date": "2026-04-26",
        "publish_time": "7 PM IST",
        "strategic_bet": "Second sleep wedge — pure bansuri (Very Low competition) for insomnia audience. Differentiates from V2 via no-raga framing (generic vs. proper-noun).",
        "validated_keywords": ["sleep music (94 HIGH)", "bansuri music (56 HIGH, Very Low competition)", "delta waves (76 HIGH)"],
        "description": """Bansuri for Deep Sleep | Delta Waves | 1 Hour Night Session 🌙

Ultra peaceful bansuri Indian flute music tuned for deep, restorative sleep. Soft breathy flute tones layered with 3Hz Delta binaural beats — the brainwave state of the deepest phase of sleep.

No mid-roll ads. No sudden shifts. One unbroken hour designed to stay with you through a full sleep cycle.

🌙 Why bansuri works for sleep:
• Soft breathy tones naturally slow your breathing
• No melodic surprises to re-engage the mind
• Bamboo flute's warm lower register signals safety to the nervous system
• 3Hz Delta = brainwave of slow-wave sleep

🎧 How to use:
Play at low volume as you lie down. Works with or without headphones. Let it run through the night — no sudden audio shifts to wake you.

⏱ Perfect for:
• Falling asleep when the mind won't settle
• Insomnia relief
• Sleep anxiety
• Staying asleep through the night
• Post-stressful evenings

🌙 Subscribe for more deep sleep ragas and healing Indian instrumentals.""",
        "tags": "sleep music, bansuri music, delta waves, indian classical sleep, deep sleep music, insomnia music, sleep meditation, indian flute sleep, 3hz delta binaural, bansuri sleep, bansuri delta, classical sleep music, sleep anxiety relief, 1 hour sleep music, indian flute music, bedtime meditation, sleep ambience, sleep breathing, nervous system sleep, deep relaxation",
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Ultra peaceful bansuri Indian flute for sleep, 45 BPM, soft airy breathy flute tones with natural vibrato, deep ambient drone pads underneath, extremely slow tempo with long pauses, lush cinematic reverb tail, nighttime dreamy atmosphere, no rhythm, no percussion, no vocals, designed for deep sleep and insomnia relief, gentle and safe feeling, infinite loop structure [No Vocals]",
        "thumbnail_prompt": "Cinematic painterly illustration of a bansuri bamboo flute resting on a soft low cushion beside a single gently flickering candle, deep midnight blue night sky background with large luminous full moon and scattered stars visible through an open window, rich indigo and warm amber candlelight color palette, peaceful serene nighttime atmosphere, soft diffused glow around the candle, Studio Ghibli dreamy style, no text overlay, 16:9 aspect ratio --ar 16:9 --style raw",
        "thumbnail_text_main": "DEEP SLEEP",
        "thumbnail_text_secondary": "BANSURI · DELTA",
        "success_good": "400+ views, 2%+ CTR, 25%+ retention",
        "success_breakthrough": "2,000+ views, 4%+ CTR, 40%+ retention",
    },
    {
        "id": "V5",
        "status": "not_started",
        "title": "ADHD Focus Music | Sitar + 40Hz Gamma | 1 Hour Deep Work Session",
        "length": "1 hour",
        "instrument": "Sitar (minimal, drone-heavy) + continuous tanpura",
        "hz": "40Hz Gamma binaural beats",
        "publish_date": "2026-04-22",
        "publish_time": "7 PM IST",
        "strategic_bet": "Dark horse — ADHD focus music is highest-volume validated keyword (86). Indian + ADHD is an unclaimed niche. Sitar instead of sarangi to avoid overlap with existing Clear Brain Fog video.",
        "validated_keywords": ["ADHD focus music (86 HIGH)", "sitar music (75 HIGH)", "deep work music (75 HIGH)", "40Hz gamma (59 HIGH)"],
        "description": """ADHD Focus Music | Sitar + 40Hz Gamma Binaural Beats | 1 Hour Deep Work Session

If your ADHD brain can't settle into focus, this session is built for you. Research at the Leiden Institute for Brain and Cognition shows 40Hz gamma binaural beats may help restore the reduced gamma coherence found in ADHD minds — supporting sustained attention without stimulant dependence.

No mid-roll ads. No interruptions. One unbroken hour of steady, repetitive sitar designed for minds that need gentle rhythmic anchoring.

🧠 Why this works for ADHD:
• Sitar's continuous drone-like phrases = no sudden melodic changes (less dopaminergic distraction)
• 40Hz gamma layer = neuroscience-backed attention enhancement
• No lyrics, no tempo shifts, no crescendos
• Steady rhythm creates cognitive anchor

🎧 How to use:
1. Headphones required for the binaural beat effect
2. Start with a 25-min work block (ADHD-friendly Pomodoro)
3. Take a 5-min movement break, then continue

⏱ Best for:
• ADHD work sessions
• Coding & technical work
• Writing & documentation
• Studying without stimulants
• WFH focus sessions
• Post-medication crash work

🎵 About the music:
• Instrument: Sitar (Indian classical string)
• Brainwave: 40Hz Gamma binaural beats
• Tempo: Steady 65 BPM

Save this to your focus playlist.

#ADHDfocus #40Hzgamma #sitar #deepwork #binauralbeats""",
        "tags": "ADHD focus music, ADHD study music, 40Hz gamma, adhd work music, neurodivergent focus music, deep work music, sitar music, adhd concentration music, sustained attention music, focus music no lyrics, adhd binaural beats, indian classical adhd, 40hz binaural beats, flow state music, sitar 40hz, pomodoro music, coding focus music, adhd focus, knowledge worker music, WFH focus music",
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Steady minimalist Indian sitar drone for focus, 65 BPM, continuous sustained sitar tones with very little melodic variation, constant tanpura drone bed, zero crescendos or dynamic shifts, ADHD-friendly consistent texture, dry clean mix with minimal reverb, grounding and anchoring mood, designed for sustained attention during deep work and coding, no vocals, no percussion, no surprises, predictable repetitive structure [No Vocals]",
        "thumbnail_prompt": "Cinematic painterly illustration of an Indian sitar placed on a clean minimalist wooden desk with a closed notebook and small warm lamp, soft dusk-blue sky visible through a window with a tiny crescent moon just appearing, muted navy-blue and warm amber lamp-light color palette, clean uncluttered composition, focused workspace atmosphere, Studio Ghibli style, calm yet alert mood, no text overlay, 16:9 aspect ratio --ar 16:9 --style raw",
        "thumbnail_text_main": "ADHD FOCUS",
        "thumbnail_text_secondary": "SITAR · 40Hz GAMMA",
        "success_good": "500+ views, 3%+ CTR, 15%+ retention",
        "success_breakthrough": "5,000+ views, 5%+ CTR (ADHD community shares hard)",
    },
    {
        "id": "V6",
        "status": "not_started",
        "title": "Pomodoro Tabla Music | 25 Min Deep Work Session | 40Hz Gamma",
        "length": "25 min",
        "instrument": "Tabla + subtle tanpura underlay",
        "hz": "40Hz Gamma binaural beats",
        "publish_date": "2026-04-27",
        "publish_time": "7 PM IST",
        "strategic_bet": "Strongest keyword stack of the batch (4 HIGH scores). Pomodoro music is Volume 77 — unclaimed niche. 25-min format matches actual Pomodoro use case = instant utility.",
        "validated_keywords": ["pomodoro music (77 HIGH)", "tabla music (67 HIGH)", "deep work music (75 HIGH)", "40Hz gamma (59 HIGH)"],
        "description": """Pomodoro Tabla Music | 25 Min Deep Work Session | 40Hz Gamma Binaural Beats

A 25-minute Indian tabla session designed for a single Pomodoro work block. Steady percussive rhythm, 40Hz gamma waves, and zero distractions — built for writers, coders, students, and anyone running Pomodoro sprints.

When ambient drone music puts you to sleep and lofi has too much going on, tabla gives your brain a productive pulse: rhythmic, minimal, no lyrics, steady tempo.

🍅 How to use:
1. Set your Pomodoro timer (or just play this track — it ends at 25 min)
2. Work on ONE task the whole session
3. Take a 5-min break when the music ends
4. Repeat for 4 cycles, then longer break

🥁 Best for:
• Pomodoro-style focused work
• Morning deep work blocks
• Writing sessions with momentum
• Coding sprints
• Studying flashcards or active recall
• Post-lunch focus recovery

🎧 Headphones required for full binaural effect.

Subscribe for more Pomodoro-length focus sessions.

#pomodoro #tablamusic #deepwork #40Hzgamma""",
        "tags": "pomodoro music, pomodoro focus music, 25 minute focus music, tabla music, deep work music, 40Hz gamma, morning focus music, coding focus music, study music 25 min, pomodoro timer music, indian classical focus, tabla rhythm focus, active focus music, energizing study music, morning motivation music, ADHD focus music, knowledge worker music, writing music, focus music no lyrics, background music for work",
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Active Indian tabla percussion for productive focus, 75 BPM, steady rhythmic tabla groove, minimal tanpura drone underneath, no melodic sitar or flute layers, consistent percussive pulse with no drops, clean balanced mix, energizing yet controlled mood, designed for 25-minute Pomodoro work blocks and morning productivity, no vocals, no melody lead, just steady rhythm, seamless loop [No Vocals]",
        "thumbnail_prompt": "Cinematic painterly illustration of a pair of traditional Indian tabla drums on a wooden surface with a subtle tomato-red pomodoro timer visible beside them, warm dawn sky background fading from indigo at top to golden amber at horizon, small crescent moon still visible in upper sky, warm honey and soft amber color palette, energetic yet controlled atmosphere, Studio Ghibli meets morning productivity aesthetic, no text overlay, 16:9 aspect ratio --ar 16:9 --style raw",
        "thumbnail_text_main": "POMODORO TABLA",
        "thumbnail_text_secondary": "25 MIN · 40Hz",
        "success_good": "400+ views, 3%+ CTR, 20%+ retention",
        "success_breakthrough": "2,000+ views, 5%+ CTR, 35%+ retention (finishable format)",
    },
    {
        "id": "V7",
        "status": "not_started",
        "title": "Shanti Dhara 🌅 | Morning Raga Instrumental for Calm & Clarity",
        "length": "1 hr 10 min",
        "instrument": "Sitar lead + soft tanpura drone + distant bansuri accents",
        "hz": "None (keep acoustic/pure)",
        "publish_date": "2026-04-20",
        "publish_time": "7 PM IST",
        "strategic_bet": "FLAGSHIP experiment. Raga Heal's Savera Shanti (Sanskrit signature) got 997K views. Tests whether this formula works for us. Zero-tag, poetic description, Sanskrit brand name.",
        "validated_keywords": ["morning focus (67 HIGH)", "intentionally unvalidated Sanskrit brand name"],
        "description": """Welcome to Shanti Dhara — a gentle morning raga instrumental designed to flow through your early hours like a quiet stream of peace. 🌅

This soft Indian-inspired soundscape blends traditional sitar melodies, tanpura drones, and subtle bansuri tones to create a tranquil atmosphere for morning meditation, mindful work, or a calm start to your day.

The flowing tones move without abrupt changes — allowing your mind to settle into stillness, one slow breath at a time.

✨ Perfect for:

Morning meditation & mindfulness
Yoga, pranayama & breathwork
Peaceful journaling rituals
Calm background music for work or study
Stress relief & emotional balance
Spiritual reflection & quiet presence

Let Shanti Dhara accompany your sunrise moments. Breathe slowly. Soften your thoughts. Let the music guide your mind into a gentle, focused calm.

Close your eyes and rest in the stillness — or simply let this play as you begin the day's quiet work.

🌿 Subscribe for more healing ragas and gentle Indian instrumental music.""",
        "tags": "",  # Intentionally empty — mirrors Raga Heal's zero-tag approach
        "suno_prompt": "[Hyper-Realistic] [Instrumental] — Warm morning raga Indian classical instrumental, 55 BPM, layered composition with sitar lead, soft tanpura drone bed, distant bansuri flute accents, gentle harmonic interplay between instruments, spacious cinematic reverb, sunrise contemplative atmosphere, slow unhurried melodic flow, deeply peaceful and grounding, designed for morning meditation and mindful work, no vocals, no percussion, no sudden changes, seamless infinite loop, evokes stillness and quiet presence [No Vocals]",
        "thumbnail_prompt": "Premium cinematic painterly illustration of a traditional Indian sitar alongside a tanpura, viewed at dawn with a sunrise sky transitioning from deep indigo at top-left (with small fading crescent moon and few lingering stars) to warm amber and peach at the horizon (with bright sun just rising), soft clouds, warm golden morning light bathing the instruments, flagship-quality rich amber-honey-gold color palette, dreamy painterly Studio Ghibli meets National Geographic photography, deeply peaceful sunrise atmosphere, no text overlay, 16:9 aspect ratio, high detail --ar 16:9 --style raw",
        "thumbnail_text_main": "SHANTI DHARA",
        "thumbnail_text_secondary": "MORNING RAGA",
        "success_good": "500+ views, 3%+ CTR",
        "success_breakthrough": "Any significant breakout validates the Sanskrit Signature formula → make 20 more (Amrit Kiran, Sahaj Prabhat, Chandra Nidra, Jal Tarang, etc.)",
    },
]


def get_all_videos():
    """Return the production queue as a list."""
    return VIDEOS


def get_video_by_id(video_id: str):
    """Fetch a single video by its ID (e.g. 'V1')."""
    for v in VIDEOS:
        if v["id"] == video_id:
            return v
    return None

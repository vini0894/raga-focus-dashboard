#!/usr/bin/env python3
"""
Raga Focus — The Bridge: proposal → ready-to-ship video folder

Reads today's proposal JSON, picks a candidate, applies any VidIQ scores
the user has logged, runs the full intelligence stack, and produces:

    videos/{slug}/
        config.toml         — for tools/pipeline.py production
        suno_prompt.txt     — copy-pasteable into Suno Pro
        thumbnail_brief.md  — image prompt + text overlay variants
        clips/              — empty, drop your Suno WAVs here
        README.md           — checklist of remaining steps

Plus:

    data/video_briefs/{slug}.json — full structured brief for dashboard

Usage:
    python3 pipeline/proposal_to_video.py                        # candidate #1 from today
    python3 pipeline/proposal_to_video.py --candidate 2          # pick #2
    python3 pipeline/proposal_to_video.py --date 2026-04-25      # specific day
    python3 pipeline/proposal_to_video.py --scores scores.json   # apply VidIQ scores
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from regenerate import regenerate_title, explain
from thumbnail_text import build_thumbnail_text_variants, pick_thumbnail_winner
from thumbnail_image import build_thumbnail_image_prompt
from description_hook import build_description_hook, build_description_body_intro, build_best_for
from suno import build_suno_prompt, build_production_spec
from scoring import build_tags, build_variants

ROOT = Path(__file__).resolve().parent.parent
PROPOSALS_DIR = ROOT / "videos/proposals"
VIDEOS_DIR    = ROOT / "videos"
from paths import DATA_DIR; BRIEFS_DIR = DATA_DIR / "video_briefs"


def slugify(candidate):
    """Build a slug like v_2026-04-26_overthinking_bansuri."""
    comp = candidate["components"]
    # Use existing video count for v-number? simpler: use date
    today_iso = date.today().isoformat()
    problem_slug = re.sub(r"[^a-z]+", "_",
                          comp["problem"]["kw"].lower().replace(" music", "")).strip("_")
    inst = comp["instrument"]["name"].lower()
    return f"v_{today_iso}_{problem_slug}_{inst}"


def write_config_toml(folder, candidate, regen_result, thumbnail_winner, suno_spec):
    """Write videos/{slug}/config.toml in the schema tools/pipeline.py expects."""
    comp = candidate["components"]
    title = regen_result["title"]
    variants = build_variants(comp["problem"], comp["hz"], comp["instrument"], comp["raga"], comp["wave"])
    tags = build_tags(comp["problem"], comp["instrument"], comp["hz"], comp["raga"], comp["wave"])
    core_tags = tags[:8]
    extended_tags = tags[8:]

    binaural_preset = comp["wave"]["wave"].lower()
    if binaural_preset not in {"alpha", "beta", "theta", "delta", "gamma", "morning"}:
        binaural_preset = "alpha"

    description_hook = build_description_hook(comp["problem"]["kw"])
    best_for = build_best_for(comp["problem"]["kw"])

    toml_text = f"""[video]
slug = "{folder.name}"
instrument = "{comp['instrument']['name']}"
raga = "{comp['raga']['name']}"
duration = 60
thumbnail = "thumbnail.png"

[audio]
clips = []   # populated when Suno WAVs are dropped into clips/
crossfade = 8.0
fade_in = 10.0
fade_out = 60.0

[binaural]
enabled = true
preset = "{binaural_preset}"
volume = 0.03
base_hz = {''.join(c for c in comp['hz']['hz'] if c.isdigit())}

[title]
final = {json.dumps(title)}
options = {json.dumps([variants['A_seo'], variants['B_question'], variants['C_outcome']])}

[description]
hook = {json.dumps(description_hook)}
best_for = {json.dumps(best_for)}

[tags]
core = {json.dumps(core_tags)}
extended = {json.dumps(extended_tags)}

[thumbnail]
text_main = {json.dumps(thumbnail_winner)}
text_secondary = "{comp['instrument']['name']} · {comp['hz']['hz']}"
image_prompt = {json.dumps(build_thumbnail_image_prompt(comp['problem']['kw'], comp['instrument']['name'], comp['raga']['name'], comp['wave']['wave']))}

[production_spec]
duration_target_sec = {suno_spec['duration_target_sec']}
master_lufs = {suno_spec['master_lufs']}
"""
    (folder / "config.toml").write_text(toml_text)


def write_suno_prompt_file(folder, suno_spec):
    text = (
        f"# Suno prompt for {folder.name}\n\n"
        f"Copy and paste this into Suno Pro (Custom mode → style: Ambient):\n\n"
        f"{suno_spec['suno_prompt']}\n\n"
        f"\n## Strategy\n{suno_spec['suno_strategy']}\n\n"
        f"## Critical tips\n"
        + "\n".join(f"- {t}" for t in suno_spec['suno_critical_tips'])
        + f"\n\n## Production spec\n"
        f"- Binaural: L={suno_spec['binaural']['left_hz']}Hz, R={suno_spec['binaural']['right_hz']}Hz "
        f"({suno_spec['binaural']['wave_hz']}Hz entrainment, {suno_spec['binaural']['level_db']}dB)\n"
        f"  → {suno_spec['binaural']['command']}\n"
        f"- Drone: {suno_spec['drone']['instrument']} ({suno_spec['drone']['level_db']}dB)\n"
        f"- Mix: Suno {suno_spec['mix_levels_db']['suno_layer']}dB · "
        f"Binaural {suno_spec['mix_levels_db']['binaural_layer']}dB · "
        f"Drone {suno_spec['mix_levels_db']['drone_layer']}dB\n"
        f"- Master: {suno_spec['master_lufs']} LUFS\n"
        f"- Output: {suno_spec['output']}\n"
    )
    (folder / "suno_prompt.txt").write_text(text)


def write_thumbnail_brief(folder, candidate, thumbnail_variants, thumbnail_winner_text):
    comp = candidate["components"]
    image_prompt = build_thumbnail_image_prompt(comp["problem"]["kw"], comp["instrument"]["name"],
                                                comp["raga"]["name"], comp["wave"]["wave"])
    text = (
        f"# Thumbnail Brief — {folder.name}\n\n"
        f"## Base image (Ideogram / Midjourney)\n\n"
        f"```\n{image_prompt}\n```\n\n"
        f"## Text overlay options (3 variants)\n\n"
    )
    for v in thumbnail_variants:
        text += f"- **{v['label']}**: `{v['text']}` — {v['strategy']}\n"
    text += f"\n## ⭐ Recommended overlay text\n\n**{thumbnail_winner_text}**\n\n"
    text += (
        f"## Spec\n"
        f"- Aspect ratio: 16:9\n"
        f"- Style: Pichwai/Kangra miniature (locked aesthetic)\n"
        f"- Overlay text must be readable at 120px width\n"
        f"- Color contrast ≥ 4.5:1 on text\n"
        f"- Subtitle row: `{comp['instrument']['name']} · {comp['hz']['hz']}`\n"
    )
    (folder / "thumbnail_brief.md").write_text(text)


def write_readme(folder, candidate, suno_spec):
    comp = candidate["components"]
    text = (
        f"# {folder.name}\n\n"
        f"_Auto-generated by `pipeline/proposal_to_video.py` on {date.today().isoformat()}_\n\n"
        f"## What this video is\n\n"
        f"- **Problem**: {comp['problem']['kw']}\n"
        f"- **Instrument**: {comp['instrument']['name']}\n"
        f"- **Raga**: {comp['raga']['name']}\n"
        f"- **Hz**: {comp['hz']['hz']}\n"
        f"- **Wave**: {comp['wave']['wave']}\n"
        f"- **Duration target**: 60 minutes\n\n"
        f"## What's already done\n\n"
        f"- ✅ Title locked\n"
        f"- ✅ A/B/C variants generated\n"
        f"- ✅ Tags compiled (4-tier, ≤500 chars)\n"
        f"- ✅ Suno prompt written → see `suno_prompt.txt`\n"
        f"- ✅ Thumbnail brief written → see `thumbnail_brief.md`\n"
        f"- ✅ Description hook written\n"
        f"- ✅ Production spec ready\n\n"
        f"## What you/colleague needs to do\n\n"
        f"1. **Generate Suno music** (`suno_prompt.txt`)\n"
        f"   - Suno Pro → Custom mode → Style: Ambient\n"
        f"   - Generate 4-6 variations, pick best 2-3, drop into `clips/`\n"
        f"2. **Generate thumbnail** (`thumbnail_brief.md`)\n"
        f"   - Use Ideogram/Midjourney with the image prompt\n"
        f"   - Add the recommended text overlay\n"
        f"   - Save as `thumbnail.png` in this folder\n"
        f"3. **Render the video**\n"
        f"   ```bash\n"
        f"   python3 tools/pipeline.py videos/{folder.name}/\n"
        f"   ```\n"
        f"4. **Upload to YouTube**\n"
        f"   - Title (from config.toml)\n"
        f"   - Tags (from config.toml)\n"
        f"   - Description (rendered by templates/description.py)\n"
        f"5. **After A/B test concludes** (~3-7 days):\n"
        f"   ```bash\n"
        f"   python3 pipeline/log_ab_test.py --video_id <YT_ID> --winner A_seo --margin 0.X\n"
        f"   ```\n"
    )
    (folder / "README.md").write_text(text)


def write_dashboard_brief(brief_path, candidate, regen_result, thumbnail_variants,
                         thumbnail_winner_text, suno_spec, slug):
    """Write the JSON brief in the schema production_queue.py understands."""
    comp = candidate["components"]
    variants = build_variants(comp["problem"], comp["hz"], comp["instrument"], comp["raga"], comp["wave"])
    tags = build_tags(comp["problem"], comp["instrument"], comp["hz"], comp["raga"], comp["wave"])

    # FULL paste-ready description (hook + body + chapters + how-to + best-for + CTA + hashtags)
    from description_hook import build_full_description
    # Use top-7 tags for hashtags (high-volume validated)
    hashtag_pool = [t for t in tags[:10]]
    description_text = build_full_description(
        problem_kw=comp["problem"]["kw"],
        instrument_name=comp["instrument"]["name"],
        raga_name=comp["raga"]["name"],
        hz=comp["hz"]["hz"],
        wave_name=comp["wave"]["wave"],
        duration_minutes=60,
        top_tags=hashtag_pool,
    )

    brief = {
        "id":               slug,
        "status":           "DRAFT",
        "created_at":       datetime.now().isoformat(),
        "title":            regen_result["title"],
        "title_variants":   variants,
        "title_history": [
            {"v": 1, "title": candidate.get("title", regen_result["title"]),
             "by": "pipeline.generate_ideas"},
            {"v": 2, "title": regen_result["title"],
             "by": f"regenerate (status={regen_result['status']})",
             "swaps": regen_result.get("swaps", [])},
        ],
        "components": {
            "problem":    comp["problem"]["kw"],
            "instrument": comp["instrument"]["name"],
            "raga":       comp["raga"]["name"],
            "hz":         comp["hz"]["hz"],
            "wave":       comp["wave"]["wave"],
        },
        "instrument":            f"{comp['instrument']['name']} + tanpura drone",
        "hz":                    f"{comp['hz']['hz']} + {suno_spec['binaural']['wave_hz']}Hz {comp['wave']['wave']} binaural",
        "length":                "1 hour",
        "publish_date":          (date.today()).isoformat(),
        "publish_time":          "8:30 PM IST",
        "validated_keywords":    list(regen_result.get("vidiq_scores", {}).keys()) if regen_result.get("vidiq_scores") else [],
        "description":           description_text,
        "tags":                  ", ".join(tags),
        "suno_prompt":           suno_spec["suno_prompt"],
        "thumbnail_prompt":      build_thumbnail_image_prompt(
                                    comp["problem"]["kw"], comp["instrument"]["name"],
                                    comp["raga"]["name"], comp["wave"]["wave"]),
        "thumbnail_text_main":   thumbnail_winner_text,
        "thumbnail_text_secondary": f"{comp['instrument']['name']} · {comp['hz']['hz']}",
        "thumbnail_text_variants": [v["text"] for v in thumbnail_variants],
        "production_spec":       suno_spec,
        "regen_result":          regen_result,
        "success_good":          "500+ views, 3%+ CTR, 15%+ retention, 3+ subs (14 days)",
        "success_breakthrough":  "2,000+ views, 5%+ CTR, 20%+ retention, 5+ subs",
        "strategic_bet":         "; ".join((candidate.get("reasons") or [])[:3]),
        "candidate_score":       candidate.get("score"),
    }
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(json.dumps(brief, indent=2, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="Proposal date (YYYY-MM-DD)")
    ap.add_argument("--candidate", type=int, default=1,
                    help="Which candidate to use (1-indexed)")
    ap.add_argument("--scores", default=None,
                    help="Path to JSON file of VidIQ scores {keyword: score}")
    args = ap.parse_args()

    proposal_json = PROPOSALS_DIR / f"{args.date}.json"
    if not proposal_json.exists():
        print(f"❌ No proposal at {proposal_json}")
        print(f"   Run: python3 pipeline/generate_ideas.py")
        sys.exit(1)

    data = json.loads(proposal_json.read_text())
    candidates = data.get("candidates", [])
    if not candidates:
        print(f"❌ No candidates in proposal")
        sys.exit(1)
    if args.candidate < 1 or args.candidate > len(candidates):
        print(f"❌ --candidate {args.candidate} out of range (1-{len(candidates)})")
        sys.exit(1)
    candidate = candidates[args.candidate - 1]

    # Apply VidIQ scores if provided
    scores = {}
    if args.scores:
        scores = json.loads(Path(args.scores).read_text())
        # ensure component keyword shape matches what regenerate expects
        for c in candidates:
            for k in ("problem", "instrument", "hz", "raga", "wave"):
                comp = c["components"].get(k)
                if isinstance(comp, dict):
                    pass

    # Reify component dicts (json roundtrip strips back to plain dicts already)
    regen = regenerate_title(candidate, scores) if scores else {
        "status":  "locked-no-scores",
        "title":   candidate["title"],
        "components": candidate["components"],
        "swaps":   [],
        "needs_revalidation": [],
        "fatal_failures":     [],
        "original_title":     candidate["title"],
    }
    print(f"\n{explain(regen)}\n")

    # Update candidate with regenerated components (in case of swaps)
    if regen.get("swaps"):
        candidate["components"] = regen["components"]
        candidate["title"]      = regen["title"]

    # Thumbnail variants
    thumb_variants = build_thumbnail_text_variants(candidate["components"]["problem"]["kw"])
    thumb_winner = pick_thumbnail_winner(thumb_variants, scores)
    thumb_winner_text = thumb_winner["winner"]["text"] if thumb_winner.get("winner") else thumb_variants[0]["text"]

    # Suno + production spec
    suno_spec = build_production_spec(candidate)

    # Slugify + create folder
    slug = slugify(candidate)
    folder = VIDEOS_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "clips").mkdir(exist_ok=True)

    # Write all files
    write_config_toml(folder, candidate, regen, thumb_winner_text, suno_spec)
    write_suno_prompt_file(folder, suno_spec)
    write_thumbnail_brief(folder, candidate, thumb_variants, thumb_winner_text)
    write_readme(folder, candidate, suno_spec)
    write_dashboard_brief(BRIEFS_DIR / f"{slug}.json", candidate, regen,
                          thumb_variants, thumb_winner_text, suno_spec, slug)

    # Print summary
    print("━" * 70)
    print(f"✓ Bridge complete — folder created at: videos/{slug}/")
    print("━" * 70)
    print(f"  Title:     {regen['title']}")
    print(f"  Slug:      {slug}")
    print(f"  Instrument:{candidate['components']['instrument']['name']}")
    print(f"  Raga:      {candidate['components']['raga']['name']}")
    print(f"  Hz:        {candidate['components']['hz']['hz']}")
    print(f"  Wave:      {candidate['components']['wave']['wave']}")
    print(f"  Thumbnail: {thumb_winner_text}")
    print()
    print("  Files written:")
    print(f"    videos/{slug}/config.toml")
    print(f"    videos/{slug}/suno_prompt.txt   ← copy into Suno")
    print(f"    videos/{slug}/thumbnail_brief.md ← copy into Ideogram")
    print(f"    videos/{slug}/README.md           ← next-steps checklist")
    print(f"    videos/{slug}/clips/              ← drop Suno WAVs here")
    print(f"    raga-focus-dashboard/data/video_briefs/{slug}.json (for dashboard)")
    print()
    print(f"  Next: cat videos/{slug}/README.md")


if __name__ == "__main__":
    main()

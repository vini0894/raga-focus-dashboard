"""
Title brainstorm pre-flight check.

Reads all 6 playbook data files. Given a slot context (theme + instrument + date),
returns structured constraints + magic phrases + anti-patterns to consider.

Also has --validate mode to check an existing title against all gates.

Usage:
    # Brainstorm mode — show me what I should know before proposing titles
    python3 pipeline/title_preflight.py --theme healing --instrument veena --slot PM

    # Validate mode — check a specific title against the rules
    python3 pipeline/title_preflight.py --validate "Soothing Music | Veena for Tired Mind | 1.5 Hours"

    # Just dump everything (no specific context)
    python3 pipeline/title_preflight.py --dump
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)

DASHBOARD_DIR = Path(__file__).parent.parent
PLAYBOOK_DIR = DASHBOARD_DIR / "data" / "playbook"


def load_playbook():
    """Load all 7 playbook data files."""
    pb = {}
    pb["rules"] = yaml.safe_load((PLAYBOOK_DIR / "playbook_rules.yaml").read_text())
    pb["themes"] = json.loads((PLAYBOOK_DIR / "theme_performance.json").read_text())
    pb["anti_patterns"] = json.loads((PLAYBOOK_DIR / "anti_patterns.json").read_text())
    pb["locks"] = json.loads((PLAYBOOK_DIR / "phrase_locks.json").read_text())
    pb["thumb"] = json.loads((PLAYBOOK_DIR / "thumbnail_format_rules.json").read_text())
    pb["instrument_fit"] = json.loads((PLAYBOOK_DIR / "instrument_lane_fit.json").read_text())
    pb["ab_patterns"] = json.loads((PLAYBOOK_DIR / "ab_pattern_rules.json").read_text())
    return pb


# ─────────────────────────────────────────────────────────
# Brainstorm mode — what should I know before proposing?
# ─────────────────────────────────────────────────────────
def brainstorm(theme: str, instrument: str, slot: str = None, date_str: str = None):
    pb = load_playbook()
    out = {
        "context": {
            "theme": theme,
            "instrument": instrument,
            "slot": slot or "unspecified",
            "date": date_str or date.today().isoformat(),
        }
    }

    # Theme info
    theme_data = pb["themes"]["themes"].get(theme.lower())
    if not theme_data:
        out["theme"] = {"error": f"Unknown theme '{theme}'. Valid: {list(pb['themes']['themes'].keys())}"}
    else:
        out["theme"] = {
            "tier": theme_data["tier"],
            "ctr_avg": theme_data["ctr_avg"],
            "avd_avg": theme_data["avd_avg"],
            "format_tolerance": theme_data["format_tolerance"],
            "winning_formula": theme_data["winning_formula"],
            "magic_phrases": theme_data["magic_phrases"],
            "thumb_format": theme_data["thumb_format"],
            "thumb_winners": theme_data["thumb_winners"],
            "anti_patterns_for_this_theme": theme_data.get("anti_patterns", []),
            "top_performers": theme_data.get("top_performers", []),
            "note": theme_data.get("note"),
        }

    # Instrument info
    inst_key = instrument.lower().replace(" ", "_")
    inst_summary = pb["instrument_fit"]["instrument_summary"].get(inst_key)
    if inst_summary:
        out["instrument"] = {
            "role": inst_summary["role"],
            "ctr_avg": inst_summary["ctr_avg"],
            "avd_avg": inst_summary["avd_avg"],
            "ship_count": inst_summary["n"],
        }
    else:
        out["instrument"] = {"role": "UNKNOWN", "note": f"No data for '{instrument}'"}

    # Instrument × Theme cell
    cell_key = f"{inst_key}__{theme.lower()}"
    cell = pb["instrument_fit"]["matrix"].get(cell_key)
    if cell:
        out["instrument_x_theme"] = {
            "n": cell["n"],
            "ctr_avg": cell["ctr_avg"],
            "avd_avg": cell["avd_avg"],
            "top_title": cell["top_title"],
            "fit_quality": classify_fit(cell["ctr_avg"], cell["avd_avg"]),
        }
    else:
        out["instrument_x_theme"] = {
            "n": 0,
            "fit_quality": "UNTESTED",
            "note": f"No ships combine {instrument} × {theme} — moonshot territory",
        }

    # Phrase locks (active)
    out["phrase_locks_active"] = [
        {"phrase": l["phrase"], "free_again": l["free_again"], "days_remaining": l["days_remaining"]}
        for l in pb["locks"]["locks"][:25]  # top 25 most-recent locks
    ]

    # Thumbnail format for this lane
    thumb_rule = pb["thumb"]["lane_rules"].get(map_theme_to_thumb_lane(theme))
    if thumb_rule:
        out["thumbnail"] = {
            "winning_format": thumb_rule["winning_format"],
            "confidence": thumb_rule["confidence"],
            "winners": thumb_rule["winners"],
            "losers": thumb_rule.get("losers", []),
            "evidence": thumb_rule["evidence"],
        }

    # A/B pattern rules for this lane
    ab_lane_key = map_theme_to_ab_lane(theme)
    ab_lane = pb["ab_patterns"]["lanes"].get(ab_lane_key) if ab_lane_key else None
    if ab_lane:
        out["ab_patterns"] = {
            "lane": ab_lane_key,
            "n_tests": pb["ab_patterns"]["n_tests"],
            "confidence": ab_lane["confidence"],
            "winning_title_type": ab_lane["winning_title_type"],
            "winning_title_examples": ab_lane.get("winning_title_examples", []),
            "avoid_title_type": ab_lane.get("avoid_title_type"),
            "winning_thumb_type": ab_lane["winning_thumb_type"],
            "winning_thumb_examples": ab_lane.get("winning_thumb_examples", []),
            "avoid_thumb_type": ab_lane.get("avoid_thumb_type"),
            "avoid_thumb_examples": ab_lane.get("avoid_thumb_examples", []),
            "evidence": ab_lane["evidence"],
            "note": ab_lane.get("note"),
        }
        out["ab_universal_rules"] = [
            {"rule": r["rule"], "action": r["action"], "confidence": r["confidence"]}
            for r in pb["ab_patterns"]["universal_rules"]
        ]
    else:
        out["ab_patterns"] = {"lane": None, "note": f"No A/B data for theme '{theme}' yet — moonshot territory"}

    # Structural rules
    out["structural_rules"] = {
        "char_target": pb["rules"]["structural"]["char_band"]["target"],
        "char_acceptable": pb["rules"]["structural"]["char_band"]["acceptable"],
        "char_hard_max": pb["rules"]["structural"]["char_band"]["hard_max"],
        "slot_count_default": pb["rules"]["structural"]["slot_count"]["default"],
        "slot_count_avoid": pb["rules"]["structural"]["slot_count"]["avoid"],
    }

    # Channel truths (always relevant)
    out["channel_truths"] = [
        {"rule": t["rule"], "severity": t["severity"]}
        for t in pb["rules"]["channel_truths"]
    ]

    # Anti-patterns to keep in mind
    out["anti_patterns_to_avoid"] = [
        {"id": p["id"], "name": p["name"], "severity": p["severity"], "description": p["description"]}
        for p in pb["anti_patterns"]["patterns"]
        if p["severity"] in ("hard", "experimental_only")
    ]

    return out


def _extract_title_lead(title: str) -> str:
    """Mirror of playbook_generators._extract_lead_phrase for validation use."""
    if not title:
        return ""
    first_split = re.split(r"[|·]", title, maxsplit=1)
    lead = first_split[0].strip().lower() if first_split else ""
    lead = re.sub(r"^[\d\-\s]+(min|minute|hour)s?\s*", "", lead, flags=re.IGNORECASE)
    lead = lead.strip(" .,:;-—")
    if len(lead) < 4 or "#" in lead:
        return ""
    return lead


def classify_fit(ctr: float, avd: float) -> str:
    if ctr >= 3.63 and avd >= 25:
        return "DUAL_WINNER"
    if ctr >= 3.63:
        return "CTR_STRONG"
    if avd >= 25:
        return "RETENTION_STRONG"
    if ctr < 3.0 and avd < 18:
        return "WEAK_BOTH"
    return "MIXED"


def map_theme_to_thumb_lane(theme: str) -> str:
    """Map theme name to thumbnail_format_rules.json lane key."""
    mapping = {
        "healing": "healing", "calm": "calm", "sleep": "sleep", "focus": "focus",
        "anxiety_stress": "anxiety_overthinking", "anxiety": "anxiety_overthinking",
        "overthinking": "anxiety_overthinking",
        "reset": "stress_burnout", "stress_burnout": "stress_burnout", "burnout": "stress_burnout",
        "stress": "stress_burnout",
        "morning": "morning_practice", "morning_practice": "morning_practice",
        "nostalgia": "nostalgia", "uplifting": "uplifting",
    }
    return mapping.get(theme.lower(), theme.lower())


def map_theme_to_ab_lane(theme: str) -> str:
    """Map theme name to ab_pattern_rules.json lane key."""
    mapping = {
        "focus": "focus",
        "morning": "morning", "morning_practice": "morning", "uplifting": "morning",
        "cognitive": "cognitive_clarity", "brain_detox": "cognitive_clarity", "cognitive_clarity": "cognitive_clarity",
        "sleep": "sleep",
        "anxiety": "relaxation_anxiety", "anxiety_stress": "relaxation_anxiety",
        "relaxation": "relaxation_anxiety", "evening": "relaxation_anxiety",
        "overthinking": "overthinking",
        "calm": "calm_healing", "healing": "calm_healing",
        "burnout": "burnout", "stress_burnout": "burnout", "stress": "burnout", "reset": "burnout",
        "deep_rest": "deep_rest",
        "stillness": "calm_stillness",
        "nostalgia": "nostalgia",
        "comfort": "comfort_emotional", "emotional": "comfort_emotional",
    }
    return mapping.get(theme.lower(), None)


# ─────────────────────────────────────────────────────────
# Validate mode — check a specific title against all gates
# ─────────────────────────────────────────────────────────
def validate(title: str) -> dict:
    pb = load_playbook()
    out = {"title": title, "char_count": len(title), "slot_count": title.count("|") + 1, "checks": []}

    # ─── Char length ───
    char_target = pb["rules"]["structural"]["char_band"]["target"]
    char_acceptable = pb["rules"]["structural"]["char_band"]["acceptable"]
    char_max = pb["rules"]["structural"]["char_band"]["hard_max"]
    n = len(title)
    if n > char_max:
        out["checks"].append({
            "rule": "char_band", "status": "FAIL", "severity": "hard",
            "reason": f"{n} chars > hard max {char_max} (CTR drops to 2.93%)"
        })
    elif n < 45:
        out["checks"].append({
            "rule": "char_band", "status": "WARN", "severity": "soft",
            "reason": f"{n} chars < 45 (only 1 ship in this band, unproven)"
        })
    elif char_target[0] <= n <= char_target[1]:
        out["checks"].append({
            "rule": "char_band", "status": "PASS", "reason": f"{n} chars in target {char_target}"
        })
    else:
        out["checks"].append({
            "rule": "char_band", "status": "PASS_ACCEPTABLE",
            "reason": f"{n} chars in acceptable {char_acceptable}"
        })

    # ─── Slot count ───
    slot_count = title.count("|") + 1
    slot_default = pb["rules"]["structural"]["slot_count"]["default"]
    slot_avoid = pb["rules"]["structural"]["slot_count"]["avoid"]
    if slot_count in slot_avoid:
        out["checks"].append({
            "rule": "slot_count", "status": "FAIL", "severity": "hard",
            "reason": f"{slot_count} slots in avoid list {slot_avoid}"
        })
    elif slot_count == slot_default:
        out["checks"].append({"rule": "slot_count", "status": "PASS", "reason": f"{slot_count} slots (default)"})
    else:
        out["checks"].append({"rule": "slot_count", "status": "PASS_ACCEPTABLE", "reason": f"{slot_count} slots"})

    # ─── Anti-pattern detection ───
    for pattern in pb["anti_patterns"]["patterns"]:
        violation = check_anti_pattern(title, pattern)
        if violation:
            out["checks"].append({
                "rule": f"anti_pattern.{pattern['id']}", "status": "FAIL",
                "severity": pattern["severity"],
                "reason": f"{pattern['name']}: {pattern['description']}",
            })

    # ─── Phrase locks (distinctive bigrams) — position-aware ───
    # Bigram in LEAD slot = HARD (channel-template risk).
    # Bigram in non-lead slot = SOFT warn (concept reuse is normal).
    title_lower = title.lower()
    lead_slot = re.split(r"[|·]", title_lower, maxsplit=1)[0]
    rest_of_title = title_lower[len(lead_slot):] if len(title_lower) > len(lead_slot) else ""
    for lock in pb["locks"].get("locks", []):
        phrase = lock["phrase"]
        if phrase in lead_slot:
            out["checks"].append({
                "rule": "phrase_lock_lead", "status": "FAIL", "severity": "hard",
                "reason": f"Phrase '{phrase}' in LEAD slot, locked till {lock['free_again']} (used in: {lock['from_title'][:60]})",
            })
        elif phrase in rest_of_title:
            out["checks"].append({
                "rule": "phrase_lock_nonlead", "status": "WARN", "severity": "soft",
                "reason": f"Phrase '{phrase}' appears in non-lead slot (used in: {lock['from_title'][:60]} — last {lock['last_used']}, free {lock['free_again']}). Allowed but concept-reuse — be intentional.",
            })

    # ─── Lead-slot phrase locks (whole first-slot phrase) ───
    title_lead = _extract_title_lead(title)
    for lead_lock in pb["locks"].get("lead_locks", []):
        if title_lead == lead_lock["lead_phrase"]:
            out["checks"].append({
                "rule": "lead_phrase_lock", "status": "FAIL", "severity": "hard",
                "reason": f"Lead phrase '{lead_lock['lead_phrase']}' locked till {lead_lock['free_again']} (used in: {lead_lock['from_title'][:60]})",
            })

    # Summary
    fails = sum(1 for c in out["checks"] if c["status"] == "FAIL" and c["severity"] == "hard")
    warns = sum(1 for c in out["checks"] if c["status"] == "WARN" or (c["status"] == "FAIL" and c["severity"] != "hard"))
    passes = sum(1 for c in out["checks"] if c["status"].startswith("PASS"))
    out["summary"] = {
        "hard_fails": fails, "warns": warns, "passes": passes,
        "verdict": "REJECT" if fails > 0 else ("REVIEW" if warns > 0 else "PASS"),
    }
    return out


def check_anti_pattern(title: str, pattern: dict) -> bool:
    """Return True if title violates pattern."""
    detector_regex = pattern.get("detector_regex")
    if detector_regex:
        try:
            if re.search(detector_regex, title, re.IGNORECASE):
                return True
        except re.error:
            pass

    detector_kw = pattern.get("detector_kw", [])
    title_lower = title.lower()
    for kw in detector_kw:
        if kw.lower() in title_lower:
            return True

    detector_kw_lead = pattern.get("detector_kw_lead", [])
    lead = title.split("|")[0].lower().strip()
    for kw in detector_kw_lead:
        if lead.startswith(kw.lower()):
            return True

    detector_kw_starts_with = pattern.get("detector_kw_starts_with", [])
    for kw in detector_kw_starts_with:
        if title_lower.startswith(kw.lower()):
            return True

    if "detector_length_gt" in pattern:
        if len(title) > pattern["detector_length_gt"]:
            return True
    if "detector_length_lt" in pattern:
        if len(title) < pattern["detector_length_lt"]:
            return True
    if "detector_slot_count" in pattern:
        if title.count("|") + 1 == pattern["detector_slot_count"]:
            return True
    if "detector_slot_count_gt" in pattern:
        if title.count("|") + 1 > pattern["detector_slot_count_gt"]:
            return True

    return False


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Title brainstorm pre-flight check")
    parser.add_argument("--theme", help="Theme/lane (e.g., healing, sleep, focus, calm)")
    parser.add_argument("--instrument", help="Instrument (e.g., veena, bansuri, sitar)")
    parser.add_argument("--slot", help="AM or PM", default=None)
    parser.add_argument("--date", help="YYYY-MM-DD", default=None)
    parser.add_argument("--validate", help="Validate a specific title against rules")
    parser.add_argument("--dump", action="store_true", help="Dump all playbook data")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    if args.validate:
        result = validate(args.validate)
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print_validate(result)
        sys.exit(0 if result["summary"]["verdict"] == "PASS" else 1)

    if args.dump:
        pb = load_playbook()
        print(json.dumps(pb, indent=2))
        return

    if not args.theme or not args.instrument:
        parser.error("--theme and --instrument required for brainstorm mode")

    result = brainstorm(args.theme, args.instrument, args.slot, args.date)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print_brainstorm(result)


def print_brainstorm(result: dict):
    print("\n" + "=" * 80)
    print(f"BRAINSTORM PRE-FLIGHT — {result['context']['theme'].upper()} × "
          f"{result['context']['instrument'].upper()}")
    print(f"Slot: {result['context']['slot']} · Date: {result['context']['date']}")
    print("=" * 80)

    t = result.get("theme", {})
    if t.get("error"):
        print(f"\n⚠️  {t['error']}")
        return

    print(f"\n📊 THEME — {result['context']['theme']}")
    print(f"  Tier: {t['tier']}  ·  CTR avg: {t['ctr_avg']}%  ·  AVD avg: {t['avd_avg']}%")
    print(f"  Format tolerance: {t['format_tolerance']}")
    if t.get("note"):
        print(f"  Note: {t['note']}")

    print(f"\n🎯 WINNING FORMULA:")
    print(f"  {t['winning_formula']}")

    print(f"\n🪄 MAGIC PHRASES (proven openers for this theme):")
    for mp in t.get("magic_phrases", [])[:8]:
        phrase = mp.get("phrase", "")
        avd = mp.get("best_avd", "—")
        ctr = mp.get("best_ctr", "")
        inst = mp.get("best_instrument", "")
        note = mp.get("note", "")
        line = f"  • {phrase:<35} AVD {avd}"
        if ctr:
            line += f"  CTR {ctr}%"
        if inst:
            line += f"  ({inst})"
        if note:
            line += f"  — {note}"
        print(line)

    i = result.get("instrument", {})
    print(f"\n🎵 INSTRUMENT — {result['context']['instrument']}")
    print(f"  Role: {i.get('role', '?')}  ·  CTR avg: {i.get('ctr_avg', '?')}%  ·  AVD avg: {i.get('avd_avg', '?')}%")

    fit = result.get("instrument_x_theme", {})
    print(f"\n🎯 INSTRUMENT × THEME FIT:")
    if fit.get("n", 0) > 0:
        print(f"  n={fit['n']}  ·  CTR {fit['ctr_avg']}%  ·  AVD {fit['avd_avg']}%  ·  Fit: {fit['fit_quality']}")
        print(f"  Top: {fit['top_title']}")
    else:
        print(f"  ⚠️  UNTESTED combination — moonshot territory")

    th = result.get("thumbnail", {})
    if th:
        print(f"\n🖼️  THUMBNAIL FORMAT:")
        print(f"  Winning: {th['winning_format']}  ·  Confidence: {th['confidence']}")
        print(f"  Winners: {', '.join(th['winners'][:5])}")
        if th.get("losers"):
            print(f"  Losers:  {', '.join(th['losers'][:3])}")

    ab = result.get("ab_patterns", {})
    if ab.get("lane"):
        print(f"\n🧪 A/B PATTERN RULES (N={result.get('ab_patterns', {}).get('n_tests', '?')} tests · lane: {ab['lane']} · confidence: {ab['confidence']}):")
        print(f"  Title → USE:   {ab['winning_title_type']}")
        if ab.get("winning_title_examples"):
            print(f"                 e.g. \"{ab['winning_title_examples'][0]}\"")
        if ab.get("avoid_title_type"):
            print(f"  Title → AVOID: {ab['avoid_title_type']}")
        print(f"  Thumb → USE:   {ab['winning_thumb_type']}")
        if ab.get("winning_thumb_examples"):
            print(f"                 e.g. {' · '.join(ab['winning_thumb_examples'][:3])}")
        if ab.get("avoid_thumb_type"):
            print(f"  Thumb → AVOID: {ab['avoid_thumb_type']}", end="")
            if ab.get("avoid_thumb_examples"):
                print(f"  (e.g. {', '.join(ab['avoid_thumb_examples'][:2])})", end="")
            print()
        if ab.get("note"):
            print(f"  ⚠️  {ab['note']}")
        print(f"  Evidence: {', '.join(ab['evidence'])}")

        universal = result.get("ab_universal_rules", [])
        if universal:
            print(f"\n  Universal rules (all lanes):")
            for r in universal[:3]:
                print(f"    • {r['rule']}  [{r['confidence']}]")
    elif ab.get("note"):
        print(f"\n🧪 A/B PATTERNS: {ab['note']}")

    s = result.get("structural_rules", {})
    print(f"\n📏 STRUCTURAL RULES:")
    print(f"  Char target: {s.get('char_target')}  ·  Slot count: {s.get('slot_count_default')}")

    locks = result.get("phrase_locks_active", [])
    if locks:
        print(f"\n🔒 PHRASE LOCKS ACTIVE ({len(locks)} shown, top {min(10,len(locks))} by days remaining):")
        for l in sorted(locks, key=lambda x: x["days_remaining"])[:10]:
            print(f"  • {l['phrase']:<32} free {l['free_again']} (in {l['days_remaining']}d)")

    aps = result.get("anti_patterns_to_avoid", [])
    if aps:
        print(f"\n🚫 KEY ANTI-PATTERNS TO AVOID:")
        for ap in aps[:5]:
            print(f"  • {ap['name']}  [{ap['severity']}]")

    print(f"\n💡 TOP PERFORMERS (exemplars):")
    for tp in t.get("top_performers", [])[:3]:
        print(f"  • {tp}")

    print()


def print_validate(result: dict):
    print(f"\nVALIDATE: {result['title']}")
    print(f"  Chars: {result['char_count']}  ·  Slots: {result['slot_count']}")
    print()
    for c in result["checks"]:
        status = c["status"]
        icon = {"PASS": "✅", "PASS_ACCEPTABLE": "🟢", "WARN": "⚠️ ", "FAIL": "❌"}.get(status, "•")
        sev = c.get("severity", "")
        sev_str = f"[{sev}]" if sev else ""
        print(f"  {icon} {c['rule']:<30} {status:<18} {sev_str}")
        print(f"      {c['reason']}")
    print()
    s = result["summary"]
    print(f"VERDICT: {s['verdict']}  ·  ✅ {s['passes']}  ⚠️  {s['warns']}  ❌ {s['hard_fails']}")
    print()


if __name__ == "__main__":
    main()

"""
Raga Focus — Title Regeneration after VidIQ Validation

Given a candidate + a dict of {keyword: vidiq_score} pasted from VidIQ,
walk each title slot. Pass = keep. Fail = swap with first valid alternative
from config bank. Re-render title.

If no alternative for a slot validates: returns status="needs_revalidation"
with the alternatives that should be tested next, OR "escalate" if no
slot-level fix works (caller should pivot to candidate #2).
"""

from typing import Dict, Any, List, Tuple

from config import (
    PROBLEM_HOOKS, RAGAS, FREQUENCIES, WAVE_FRAMES,
    WAVE_OUTCOME_ALTS, RAGA_BY_MOOD, HZ_BY_INTENT,
    PROBLEM_KEYWORD_ALTS, PROBLEM_TO_RAGA_MOOD, PROBLEM_TO_HZ_INTENT,
    RULES,
)
from scoring import build_title
from keyword_bank import get_alternatives as bank_get_alternatives


MIN_SCORE = RULES["min_vidiq_score"]  # 60


def _score_passes(score):
    """A score passes if it's an int >= MIN_SCORE. None or low score = fail."""
    if score is None:
        return False
    try:
        return int(score) >= MIN_SCORE
    except (TypeError, ValueError):
        return False


def _slot_keyword(component, slot):
    """Extract the lookup keyword for a given slot of the candidate."""
    if slot == "problem":
        return component["problem"]["kw"]
    if slot == "instrument":
        return component["instrument"]["name"].lower() + " music"
    if slot == "hz":
        return component["hz"]["hz"].lower()
    if slot == "raga":
        return f"raga {component['raga']['name'].lower()}"
    if slot == "wave":
        return f"{component['wave']['wave']} wave {component['wave']['outcome']}".lower()
    return None


def _problem_mood_bucket(problem_kw):
    """Find which mood bucket a problem belongs to."""
    p = problem_kw.lower()
    for key, bucket in PROBLEM_TO_RAGA_MOOD.items():
        if key in p:
            return bucket
    return "all_purpose_calm"


def _problem_hz_intent(problem_kw):
    p = problem_kw.lower()
    for key, intent in PROBLEM_TO_HZ_INTENT.items():
        if key in p:
            return intent
    return "anxiety_default"


def _try_problem_alt(component, scores):
    """If primary problem keyword failed, try fallback problem keywords."""
    primary_kw = component["problem"]["kw"]
    alts = PROBLEM_KEYWORD_ALTS.get(primary_kw, [])
    for alt_kw in alts:
        alt_score = scores.get(alt_kw)
        if _score_passes(alt_score):
            # Find the problem-hook record for this alternative
            for hook in PROBLEM_HOOKS:
                if hook["kw"] == alt_kw:
                    return hook, alt_kw
    return None, None


def _try_raga_alt(component, scores, used_recently):
    """Pick a substitute raga from same mood bucket. Skip recently-used ones."""
    bucket = _problem_mood_bucket(component["problem"]["kw"])
    candidates = RAGA_BY_MOOD.get(bucket, [])
    current_name = component["raga"]["name"]

    for raga_name in candidates:
        if raga_name == current_name:
            continue
        if raga_name in used_recently:
            continue
        # Find raga record
        for r in RAGAS:
            if r["name"] == raga_name:
                # If user supplied a score for this raga and it passes, use it
                lookup = f"raga {raga_name.lower()}"
                if lookup in scores and not _score_passes(scores[lookup]):
                    continue  # explicitly failed VidIQ
                return r, lookup
    return None, None


def _try_hz_alt(component, scores, used_recently):
    """Pick substitute Hz from same intent bucket."""
    intent = _problem_hz_intent(component["problem"]["kw"])
    candidates = HZ_BY_INTENT.get(intent, [])
    current = component["hz"]["hz"]

    for hz_str in candidates:
        if hz_str == current:
            continue
        if hz_str in used_recently:
            continue
        for f in FREQUENCIES:
            if f["hz"] == hz_str:
                return f, hz_str.lower()
    return None, None


def _try_wave_alt(component, scores):
    """Try alternate wave-outcome phrasings (e.g., 'Alpha Wave Calm Session' → 'Alpha Wave Meditation')."""
    current_phrase = f"{component['wave']['wave']} Wave {component['wave']['outcome']}"
    alts = WAVE_OUTCOME_ALTS.get(current_phrase, [])

    for alt in alts:
        alt_lower = alt.lower()
        # If the user gave us an explicit score for this alternate phrasing, use it
        if alt_lower in scores:
            if _score_passes(scores[alt_lower]):
                # Build a synthetic wave dict matching the alternative
                # (keeps the wave name same, but changes "outcome")
                # We crudely parse: take wave name from current, outcome from alternative
                return {
                    "wave":    component["wave"]["wave"],
                    "outcome": alt.replace(f"{component['wave']['wave']} Wave ", "").strip(),
                    "matches": component["wave"].get("matches", []),
                }, alt_lower
        else:
            # No score given — return as "needs_revalidation"
            return {
                "wave":    component["wave"]["wave"],
                "outcome": alt.replace(f"{component['wave']['wave']} Wave ", "").strip(),
                "matches": component["wave"].get("matches", []),
                "_needs_revalidation": True,
            }, alt_lower
    return None, None


def regenerate_title(candidate: Dict[str, Any],
                     scores: Dict[str, int],
                     recently_used_ragas: List[str] = None,
                     recently_used_hz: List[str] = None,
                     custom_alternatives: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Apply VidIQ scores to a candidate. Swap any failing slots from alternatives.

    `scores`: {keyword_lower: int_score} pasted from VidIQ.
    `custom_alternatives`: optional [{phrase, slot, score, mood?, intent?}] —
        user-supplied new candidates (e.g. from competitor analysis) that
        aren't in the static config bank. If they pass VidIQ ≥ MIN_SCORE,
        they're eligible for slot-filling.
    """
    recently_used_ragas = recently_used_ragas or []
    recently_used_hz = recently_used_hz or []
    custom_alternatives = custom_alternatives or []

    # Merge: user custom alts that pass min score get added to local pools per slot
    custom_by_slot = {"problem": [], "wave": [], "raga": [], "hz": [], "instrument": []}
    for alt in custom_alternatives:
        if _score_passes(alt.get("score")):
            slot = alt.get("slot", "")
            if slot in custom_by_slot:
                custom_by_slot[slot].append(alt)

    # Also pull from the persistent bank (data/keyword_bank.csv)
    bank_alts_by_slot = {
        "problem": bank_get_alternatives("problem"),
        "wave":    bank_get_alternatives("wave"),
        "raga":    bank_get_alternatives("raga"),
        "hz":      bank_get_alternatives("hz"),
    }

    component = dict(candidate["components"])  # shallow copy
    swaps = []
    needs_revalidation = []
    fatal_failures = []

    # Slot order: problem (most critical) → wave → raga → hz → instrument
    # Instrument is rarely swapped (it drives the whole production)

    # ── 1. Problem ──────────────────────────────────────
    p_kw = component["problem"]["kw"]
    p_score = scores.get(p_kw)
    if p_kw in scores and not _score_passes(p_score):
        # First try config-bank alternatives
        new_hook, new_kw = _try_problem_alt(component, scores)
        # Then try user custom + persistent-bank alternatives
        if not new_hook:
            for alt in custom_by_slot["problem"] + bank_alts_by_slot["problem"]:
                phrase = alt.get("phrase", "")
                if _score_passes(alt.get("score") or alt.get("vidiq_score")):
                    new_hook = {
                        "seo_phrase": phrase,
                        "kw":         phrase.lower(),
                        "vidiq_score":alt.get("score") or alt.get("vidiq_score"),
                    }
                    new_kw = phrase.lower()
                    break
        if new_hook:
            component["problem"] = new_hook
            swaps.append(("problem", p_kw, new_kw))
        else:
            fatal_failures.append(("problem", p_kw, p_score, "no validated alt (bank + custom checked)"))

    # ── 2. Wave-outcome ────────────────────────────────
    w_kw = _slot_keyword(component, "wave")
    if w_kw in scores and not _score_passes(scores[w_kw]):
        new_wave, new_w_kw = _try_wave_alt(component, scores)
        if new_wave:
            if new_wave.get("_needs_revalidation"):
                needs_revalidation.append(("wave", new_w_kw))
                # don't apply swap yet — caller must validate
            else:
                component["wave"] = {k: v for k, v in new_wave.items() if not k.startswith("_")}
                swaps.append(("wave", w_kw, new_w_kw))
        else:
            fatal_failures.append(("wave", w_kw, scores[w_kw], "no alt available"))

    # ── 3. Raga ────────────────────────────────────────
    r_kw = _slot_keyword(component, "raga")
    if r_kw in scores and not _score_passes(scores[r_kw]):
        new_raga, new_r_kw = _try_raga_alt(component, scores, recently_used_ragas)
        if new_raga:
            component["raga"] = new_raga
            swaps.append(("raga", r_kw, new_r_kw))
        else:
            fatal_failures.append(("raga", r_kw, scores[r_kw], "no validated mood-bucket alt"))

    # ── 4. Hz ─────────────────────────────────────────
    h_kw = _slot_keyword(component, "hz")
    if h_kw in scores and not _score_passes(scores[h_kw]):
        new_hz, new_h_kw = _try_hz_alt(component, scores, recently_used_hz)
        if new_hz:
            component["hz"] = new_hz
            swaps.append(("hz", h_kw, new_h_kw))
        else:
            fatal_failures.append(("hz", h_kw, scores[h_kw], "no alt"))

    # ── Render new title ────────────────────────────────
    new_title = build_title(
        component["problem"], component["hz"], component["instrument"],
        component["raga"], component["wave"],
    )

    # ── Decide overall status ───────────────────────────
    if fatal_failures and not swaps:
        status = "escalate"  # no fix possible — caller should try candidate #2
    elif needs_revalidation:
        status = "needs_revalidation"
    elif fatal_failures and swaps:
        status = "partial"   # some swaps worked, some slots couldn't be fixed
    elif swaps:
        status = "regenerated"
    else:
        status = "locked"    # all slots passed — title is final

    return {
        "status":              status,
        "title":               new_title,
        "components":          component,
        "swaps":               swaps,
        "needs_revalidation":  needs_revalidation,
        "fatal_failures":      fatal_failures,
        "original_title":      candidate.get("title"),
    }


def explain(result):
    """Pretty-print the regeneration result for CLI/dashboard."""
    lines = [f"Status: {result['status']}"]
    if result["original_title"] != result["title"]:
        lines.append(f"  Was:  {result['original_title']}")
        lines.append(f"  Now:  {result['title']}")
    else:
        lines.append(f"  Title: {result['title']}")
    if result["swaps"]:
        lines.append("\n  Swaps applied:")
        for slot, old, new in result["swaps"]:
            lines.append(f"    [{slot}] {old}  →  {new}")
    if result["needs_revalidation"]:
        lines.append("\n  Need VidIQ validation on:")
        for slot, kw in result["needs_revalidation"]:
            lines.append(f"    [{slot}] {kw}")
    if result["fatal_failures"]:
        lines.append("\n  ⚠️ Could not fix:")
        for slot, kw, score, reason in result["fatal_failures"]:
            lines.append(f"    [{slot}] {kw} (score={score}) — {reason}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Quick CLI test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Synthesize a candidate to test
    sample_candidate = {
        "title": "Overthinking Music | 432Hz Bansuri Raga Bhupali | Alpha Wave Calm Session | 1 Hour",
        "components": {
            "problem":    PROBLEM_HOOKS[2],   # overthinking
            "instrument": {"name": "Bansuri", "vidiq_score": 66, "vidiq_comp": "Very Low"},
            "hz":         FREQUENCIES[1],     # 432Hz
            "raga":       {"name": "Bhupali", "time": "evening", "mood": "serenity"},
            "wave":       WAVE_FRAMES[0],     # Alpha
        },
    }

    # Simulate VidIQ scores from user
    test_scores = {
        "overthinking music":           67,    # ✅ passes
        "raga bhupali":                 38,    # ❌ fails
        "alpha wave calm session":      45,    # ❌ fails — but we have alts
        "alpha wave meditation":        62,    # ✅ alt that user pre-validated
        "432hz":                        74,    # ✅ passes
    }

    result = regenerate_title(sample_candidate, test_scores)
    print(explain(result))

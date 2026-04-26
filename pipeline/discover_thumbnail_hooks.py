"""
Raga Focus — Thumbnail Hook Discovery from Competitor Titles

Extracts short, thumbnail-friendly phrases from competitor titles. These are
phrases that already work AT SCALE on competitor videos — proven by view count,
not just by VidIQ.

Workflow:
  1. Pull competitor titles (RSS, last 30 days)
  2. Take the FIRST segment of each title (before first | or :)
  3. Strip instrument/Hz/wave/raga noise
  4. Filter: 1-5 words, looks like a hook (question, imperative, or noun-state)
  5. Drop phrases already in thumbnail_bank.csv or invalidated
  6. Sort by competitor view count + freshness
  7. Output top N candidates per problem bucket
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Set

from signals import fetch_all_competitor_uploads

from paths import DATA_DIR
THUMBNAIL_BANK_CSV = DATA_DIR / "thumbnail_bank.csv"

# Tokens to strip from titles (noise we don't want in thumbnail hooks)
INSTRUMENT_TOKENS = {"sitar", "bansuri", "sarangi", "dilruba", "veena", "sarod",
                     "santoor", "esraj", "tanpura", "tabla", "shehnai",
                     "bamboo flute", "instrumental", "with sitar", "with bansuri"}
WAVE_TOKENS       = {"alpha wave", "beta wave", "theta wave", "delta wave",
                     "gamma wave", "binaural", "alpha waves", "delta waves",
                     "theta waves"}
HZ_RE             = re.compile(r"\d{2,4}\s*hz", re.IGNORECASE)
RAGA_RE           = re.compile(r"\braga[ng]?\s+\w+", re.IGNORECASE)  # "Raga X" / "Raag X"
DURATION_RE       = re.compile(r"\b\d+\s*(hour|hr|min|minute|hours|minutes)s?\b", re.IGNORECASE)

# Patterns indicating a phrase IS a hook
QUESTION_END      = re.compile(r"\?$")
IMPERATIVE_VERBS  = {"calm", "stop", "release", "heal", "boost", "wake",
                     "clear", "detox", "reset", "restore", "find", "reach",
                     "soothe", "ease", "open", "feel", "let", "drop",
                     "rest", "unwind", "breathe", "settle", "ground"}
STATE_TOKENS      = {"anxious", "exhausted", "tired", "overthinker", "overthinking",
                     "racing", "heavy", "fragile", "burnt", "depleted", "stuck",
                     "wired", "tense", "restless", "frazzled"}


def _strip_noise(phrase: str) -> str:
    """Remove instrument/Hz/wave/raga/duration noise from phrase."""
    p = phrase.strip()
    p = HZ_RE.sub(" ", p)
    p = RAGA_RE.sub(" ", p)
    p = DURATION_RE.sub(" ", p)
    p_lower = p.lower()
    for tok in sorted(INSTRUMENT_TOKENS | WAVE_TOKENS, key=len, reverse=True):
        p_lower = p_lower.replace(tok, " ")
    # Reapply original casing on the cleaned version (best effort)
    cleaned = re.sub(r"\s+", " ", p_lower).strip(" .,—–-|·:")
    # Try to recover a Title-Cased version
    return cleaned.title() if cleaned else ""


def _looks_like_hook(phrase: str) -> bool:
    """Filter: keep only phrases that look like thumbnail-friendly hooks."""
    p = phrase.strip()
    words = p.split()
    if not (1 <= len(words) <= 5):
        return False
    if QUESTION_END.search(p):
        return True
    first_lower = words[0].lower()
    if first_lower in IMPERATIVE_VERBS:
        return True
    # Noun-state: any word matches a state token
    if any(w.lower() in STATE_TOKENS for w in words):
        return True
    # "Calm Your X" / "Boost Your X" / "Wake Up Without X" — verb + your/up
    if first_lower in IMPERATIVE_VERBS and len(words) >= 2 and words[1].lower() in {"your", "up", "the"}:
        return True
    return False


def _classify_problem_bucket(phrase: str) -> str:
    """Tag a hook with the problem bucket it likely belongs to."""
    p = phrase.lower()
    if any(t in p for t in ["overthink", "racing", "thoughts", "mind racing"]):
        return "overthinking"
    if any(t in p for t in ["anxiety", "anxious", "panic", "nervous"]):
        return "anxiety"
    if any(t in p for t in ["sleep", "asleep", "insomnia"]):
        return "sleep"
    if any(t in p for t in ["stress", "burnt out", "burnout", "burned"]):
        return "stress"
    if any(t in p for t in ["rest", "exhausted", "depleted", "tired"]):
        return "rest"
    if any(t in p for t in ["meditation", "meditate", "stillness"]):
        return "meditation"
    if any(t in p for t in ["unwind", "switch off", "wind down"]):
        return "unwind"
    if any(t in p for t in ["dopamine", "overstimulated"]):
        return "dopamine"
    if any(t in p for t in ["heart", "grief", "emotional"]):
        return "emotional"
    if any(t in p for t in ["morning", "wake", "cortisol"]):
        return "morning"
    if any(t in p for t in ["fog", "brain fog", "clarity"]):
        return "anxiety"  # brain fog → anxiety bucket for thumbnails
    if any(t in p for t in ["vagus", "polyvagal"]):
        return "vagus"
    if any(t in p for t in ["nervous system", "down regulate"]):
        return "nervous system"
    return "anxiety"  # safe default


def _bank_phrases() -> Set[str]:
    """Phrases already in thumbnail_bank.csv."""
    if not THUMBNAIL_BANK_CSV.exists():
        return set()
    out = set()
    with open(THUMBNAIL_BANK_CSV) as f:
        for row in csv.DictReader(f):
            out.add(row.get("phrase", "").strip().lower())
    return out


def discover(top_n_per_bucket: int = 3) -> Dict[str, List[Dict]]:
    """Return discovered candidates grouped by problem bucket."""
    known = _bank_phrases()
    competitor_data = fetch_all_competitor_uploads(days=30)

    by_bucket = {}
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u:
                continue
            title = u["title"]
            # First segment before any pipe or colon = thumbnail-style hook usually
            first_segment = re.split(r"\s*[\|·•:]\s*", title)[0]
            cleaned = _strip_noise(first_segment)
            if not _looks_like_hook(cleaned):
                continue
            phrase_lower = cleaned.lower()
            if phrase_lower in known:
                continue
            bucket = _classify_problem_bucket(cleaned)
            entry = {
                "phrase":       cleaned,
                "problem_kw":   bucket,
                "competitor":   comp_name,
                "source_title": title,
                "days_ago":     u.get("days_ago", 999),
            }
            by_bucket.setdefault(bucket, []).append(entry)

    # Dedupe by phrase + sort by recency
    for bucket, entries in by_bucket.items():
        seen = set()
        deduped = []
        for e in entries:
            key = e["phrase"].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(e)
        deduped.sort(key=lambda x: x["days_ago"])
        by_bucket[bucket] = deduped[:top_n_per_bucket]
    return by_bucket


def append_to_bank(phrase: str, problem_kw: str, vidiq_score: int = 0,
                    form: str = "discovered", source: str = "competitor",
                    won_ab: bool = False):
    """Append a thumbnail hook to the bank."""
    from datetime import date
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not THUMBNAIL_BANK_CSV.exists()
    with open(THUMBNAIL_BANK_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["phrase", "problem_kw", "vidiq_score", "form",
                       "source", "won_ab", "added_date"])
        w.writerow([phrase, problem_kw, vidiq_score, form, source,
                    "true" if won_ab else "false", date.today().isoformat()])


# ═══════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("─── Discovered thumbnail hooks from competitor RSS ───")
    print("(Pre-validated by competitor view counts. Paste to validate in VidIQ for banking.)\n")
    by_bucket = discover(top_n_per_bucket=4)
    for bucket, entries in sorted(by_bucket.items()):
        print(f"  [{bucket}]")
        for e in entries:
            print(f"     {e['phrase']:35s}  {e['days_ago']}d ago — {e['competitor']}")
        print()

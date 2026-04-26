"""
Raga Focus — Historical title-performance analyzer.

Classifies past titles (own catalog + competitor RSS) as:
  - SEO-led:      starts with a noun-phrase keyword (e.g., "Stress Relief Music")
  - Question-led: starts with question word OR ends with ?
  - Outcome-led:  starts with imperative verb ("Calm…", "Reset…", "Stop…")
  - Mixed:        falls through to default

Computes avg CTR / view-velocity per category so the daily proposal
can recommend which template to lead with based on actual data.
"""

import re
from statistics import mean


QUESTION_STARTERS = ("can't", "cant", "why", "how", "when", "what", "are you", "is your", "do you")
OUTCOME_STARTERS = (
    "calm", "reset", "stop", "release", "heal", "unwind", "boost",
    "find", "reach", "enter", "overcome", "let go", "clear", "wake up",
)


def classify_title(title: str) -> str:
    """Return one of: 'question', 'outcome', 'seo', 'mixed'."""
    if not title:
        return "mixed"
    head = title.split("|")[0].strip().lower()

    if head.endswith("?") or any(head.startswith(q) for q in QUESTION_STARTERS):
        return "question"

    if any(head.startswith(o + " ") for o in OUTCOME_STARTERS):
        return "outcome"

    # SEO-led if starts with a "Music" / capitalized noun-phrase pattern
    if "music" in head or "ragas" in head or re.match(r"^[a-z\s]+(music|meditation|raga|reset|relief)", head):
        return "seo"

    return "mixed"


def analyze_own_catalog(catalog):
    """Group catalog by hook type, compute avg CTR + impressions."""
    buckets = {"seo": [], "question": [], "outcome": [], "mixed": []}
    for v in catalog:
        cls = classify_title(v["title"])
        buckets[cls].append(v)

    summary = {}
    for cls, vids in buckets.items():
        if not vids:
            summary[cls] = {"n": 0, "avg_ctr": None, "avg_impr": None, "avg_views": None, "examples": []}
            continue
        avg_ctr = mean([v["ctr_pct"] for v in vids if v["ctr_pct"] > 0]) if any(v["ctr_pct"] > 0 for v in vids) else 0
        avg_impr = mean([v["impressions"] for v in vids])
        avg_views = mean([v["views"] for v in vids])
        examples = sorted(vids, key=lambda x: -x["ctr_pct"])[:3]
        summary[cls] = {
            "n": len(vids),
            "avg_ctr": round(avg_ctr, 2),
            "avg_impr": round(avg_impr),
            "avg_views": round(avg_views),
            "examples": [{"title": e["title"], "ctr": e["ctr_pct"], "views": e["views"]} for e in examples],
        }
    return summary


def analyze_competitor_titles(competitor_data, days=30):
    """Group competitor uploads by hook type. (No CTR available from RSS — uses upload count + recency.)"""
    buckets = {"seo": [], "question": [], "outcome": [], "mixed": []}
    for comp_name, uploads in competitor_data.items():
        for u in uploads:
            if "error" in u or u.get("days_ago", 99) > days:
                continue
            cls = classify_title(u["title"])
            buckets[cls].append({"competitor": comp_name, **u})

    summary = {}
    for cls, vids in buckets.items():
        summary[cls] = {
            "n": len(vids),
            "examples": [
                {"title": v["title"], "competitor": v["competitor"], "days_ago": v["days_ago"]}
                for v in sorted(vids, key=lambda x: x["days_ago"])[:3]
            ],
        }
    return summary


def recommend_lead_template(own_summary, competitor_summary):
    """Return ('A_seo' | 'B_question' | 'C_outcome', rationale_str).

    Priority:
    1. KNOWN_AB_RESULTS (concluded A/B tests on our channel — highest signal)
    2. Own catalog CTR by hook type (n≥2 per type required)
    3. Competitor frequency in last 30d
    4. Fallback: A_seo (search-rank default)
    """
    # 1. KNOWN A/B RESULTS — concluded YouTube title tests
    # Combine config (legacy seed) + ab_results.csv (live, appended via log_ab_test.py)
    ab_records = []
    try:
        from config import KNOWN_AB_RESULTS
        ab_records.extend(KNOWN_AB_RESULTS)
    except ImportError:
        pass

    import csv as _csv
    from pathlib import Path as _Path
    from paths import DATA_DIR; ab_csv = DATA_DIR / "ab_results.csv"
    if ab_csv.exists():
        with open(ab_csv) as f:
            for row in _csv.DictReader(f):
                ab_records.append({
                    "winner":        row["winner"],
                    "concluded_on":  row["concluded_on"],
                    "win_margin":    float(row.get("win_margin") or 0),
                })

    if ab_records:
        seo_wins = sum(1 for r in ab_records if r["winner"] == "A_seo")
        q_wins   = sum(1 for r in ab_records if r["winner"] == "B_question")
        out_wins = sum(1 for r in ab_records if r["winner"] == "C_outcome")
        if seo_wins > q_wins + out_wins:
            latest = max(ab_records, key=lambda r: r["concluded_on"])
            return "A_seo", f"⭐ Concluded A/B: SEO won {seo_wins}/{len(ab_records)} tests (latest {latest['concluded_on']}, +{int(latest['win_margin']*100)}% margin)."
        elif q_wins > seo_wins + out_wins:
            return "B_question", f"⭐ Concluded A/B: Question won {q_wins}/{len(ab_records)} tests."

    own_seo_ctr = own_summary.get("seo", {}).get("avg_ctr") or 0
    own_q_ctr   = own_summary.get("question", {}).get("avg_ctr") or 0
    own_seo_n   = own_summary.get("seo", {}).get("n") or 0
    own_q_n     = own_summary.get("question", {}).get("n") or 0

    # 2. Own CTR-by-hook
    if own_q_n >= 2 and own_q_ctr > own_seo_ctr + 1.0:
        return "B_question", f"Own data: question-led {own_q_ctr}% CTR (n={own_q_n}) > SEO-led {own_seo_ctr}% (n={own_seo_n})"
    if own_seo_n >= 2 and own_seo_ctr > own_q_ctr + 1.0:
        return "A_seo", f"Own data: SEO-led {own_seo_ctr}% CTR (n={own_seo_n}) > question-led {own_q_ctr}% (n={own_q_n})"

    # 3. Competitor preference
    comp_seo_n = competitor_summary.get("seo", {}).get("n") or 0
    comp_q_n   = competitor_summary.get("question", {}).get("n") or 0
    if comp_seo_n > comp_q_n * 1.5:
        return "A_seo", f"Competitors prefer SEO-led ({comp_seo_n} vs {comp_q_n} question-led in last 30d)."
    elif comp_q_n > comp_seo_n * 1.5:
        return "B_question", f"Competitors prefer question-led ({comp_q_n} vs {comp_seo_n} SEO-led in last 30d)."

    # 4. Fallback
    return "A_seo", "No clear signal — defaulting to SEO-led (search-rank advantage)."

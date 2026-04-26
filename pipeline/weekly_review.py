#!/usr/bin/env python3
"""
Raga Focus — Weekly Intelligence Review

Run once a week. Audits every layer of the intelligent system, surfaces patterns,
and recommends improvements. Output: weekly_reviews/YYYY-MM-DD.md

Layers audited:
  1. Keyword bank growth + slot distribution
  2. Invalidated keywords (re-test candidates)
  3. Thumbnail bank
  4. A/B test winners (hook recommendations)
  5. Suno outcomes (which prompts work)
  6. Approval log (rejection patterns)
  7. Channel analytics trend (CTR/AVD/views over time)
  8. Discovery hit rate (how many discovered keywords got validated)

Usage:
    python3 pipeline/weekly_review.py
    python3 pipeline/weekly_review.py --since 2026-04-18  # custom window
"""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from paths import DATA_DIR
REVIEW_DIR = ROOT / "weekly_reviews"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv(path):
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def audit_keyword_bank(since):
    rows = _read_csv(DATA_DIR / "keyword_bank.csv")
    total = len(rows)
    by_slot = Counter(r.get("slot", "?") for r in rows)
    new_this_week = sum(1 for r in rows
                       if (r.get("first_added") or r.get("added_date") or "1900-01-01") >= since)
    untested_alts = sum(1 for r in rows if int(r.get("vidiq_score", 0) or 0) == 0)
    high_value = sum(1 for r in rows if int(r.get("vidiq_score", 0) or 0) >= 70)
    return {
        "total":          total,
        "by_slot":        dict(by_slot),
        "new_this_week":  new_this_week,
        "untested":       untested_alts,
        "high_value":     high_value,
    }


def audit_invalidated(since):
    rows = _read_csv(DATA_DIR / "invalidated_keywords.csv")
    older_than_30d = sum(1 for r in rows
                         if (r.get("tested_on") or "9999") < (date.today() - timedelta(days=30)).isoformat())
    return {
        "total":          len(rows),
        "stale_30d":      older_than_30d,
        "retest_recommended": [r["phrase"] for r in rows
                                if (r.get("tested_on") or "9999") < (date.today() - timedelta(days=60)).isoformat()][:5],
    }


def audit_thumbnail_bank(since):
    rows = _read_csv(DATA_DIR / "thumbnail_bank.csv")
    by_form = Counter(r.get("form", "?") for r in rows)
    ab_winners = sum(1 for r in rows if r.get("won_ab") == "true")
    return {
        "total":      len(rows),
        "by_form":    dict(by_form),
        "ab_winners": ab_winners,
    }


def audit_ab_results(since):
    rows = _read_csv(DATA_DIR / "ab_results.csv")
    if not rows:
        return {"total": 0, "by_winner": {}, "avg_margin": 0, "trend": "no data"}
    by_winner = Counter(r.get("winner", "?") for r in rows)
    margins = [float(r.get("win_margin", 0) or 0) for r in rows if r.get("win_margin")]
    avg = sum(margins) / len(margins) if margins else 0
    recent = [r for r in rows if (r.get("concluded_on") or "1900") >= since]
    return {
        "total":         len(rows),
        "by_winner":     dict(by_winner),
        "avg_margin":    round(avg, 2),
        "this_week":     len(recent),
    }


def audit_suno(since):
    rows = _read_csv(DATA_DIR / "suno_results.csv")
    if not rows:
        return {"total": 0, "avg_quality": 0, "by_instrument": {}}
    quals = [int(r.get("quality_rating", 0) or 0) for r in rows]
    avg = sum(quals) / len(quals) if quals else 0
    by_instrument = defaultdict(list)
    for r in rows:
        by_instrument[r.get("instrument", "?")].append(int(r.get("quality_rating", 0) or 0))
    inst_avg = {i: round(sum(qs)/len(qs), 2) for i, qs in by_instrument.items()}
    return {
        "total":         len(rows),
        "avg_quality":   round(avg, 2),
        "by_instrument": inst_avg,
    }


def audit_approvals(since):
    rows = _read_csv(DATA_DIR / "approval_log.csv")
    if not rows:
        return {"total": 0, "approved": 0, "rejected": 0, "rejection_reasons": []}
    decisions = Counter(r.get("decision", "?") for r in rows)
    reasons = [r.get("reason", "") for r in rows
              if r.get("decision") == "rejected" and r.get("reason")]
    return {
        "total":            len(rows),
        "approved":         decisions.get("approved", 0),
        "rejected":         decisions.get("rejected", 0),
        "rejection_reasons":reasons[:5],
    }


def audit_channel_growth(since):
    """Read REACH_HISTORY.csv for video performance trend."""
    rows = _read_csv(DATA_DIR / "REACH_HISTORY.csv")
    if not rows:
        return {"videos": 0, "avg_ctr": 0, "avg_avd": 0}
    # latest snapshot per video
    latest = {}
    for r in rows:
        vid = r.get("video_id")
        if not vid:
            continue
        latest[vid] = r
    ctrs = [float(r.get("ctr_pct", 0) or 0) for r in latest.values()]
    avds = [float(r.get("avg_view_pct", 0) or 0) for r in latest.values()]
    return {
        "videos":   len(latest),
        "avg_ctr":  round(sum(ctrs)/len(ctrs), 2) if ctrs else 0,
        "avg_avd":  round(sum(avds)/len(avds), 2) if avds else 0,
        "best_ctr": round(max(ctrs), 2) if ctrs else 0,
        "best_avd": round(max(avds), 2) if avds else 0,
    }


def render_review(since):
    today = date.today().isoformat()
    out = [f"# Weekly Intelligence Review — {today}\n",
           f"_Window: since {since}. Auto-audit of every learning layer._\n"]

    # ── Keyword bank ──
    kw = audit_keyword_bank(since)
    out.append("## 🧠 Keyword Bank")
    out.append(f"- **Total**: {kw['total']} validated keywords")
    out.append(f"- **By slot**: {kw['by_slot']}")
    out.append(f"- **New this week**: {kw['new_this_week']}")
    out.append(f"- **High-value (≥70)**: {kw['high_value']}")
    if kw['new_this_week'] < 3:
        out.append(f"- ⚠️ Slow growth this week. Push on competitor discovery + manual research.")
    out.append("")

    # ── Invalidated ──
    inv = audit_invalidated(since)
    out.append("## 🚫 Invalidated Keywords")
    out.append(f"- **Total**: {inv['total']} (so we don't suggest them again)")
    if inv['retest_recommended']:
        out.append("- **Re-test candidates** (last tested 60+ days ago — markets change):")
        for p in inv['retest_recommended']:
            out.append(f"  - {p}")
    out.append("")

    # ── Thumbnail bank ──
    tb = audit_thumbnail_bank(since)
    out.append("## 🎨 Thumbnail Hook Bank")
    out.append(f"- **Total**: {tb['total']} hooks")
    out.append(f"- **By form**: {tb['by_form']}")
    out.append(f"- **A/B winners**: {tb['ab_winners']}")
    out.append("")

    # ── A/B results ──
    ab = audit_ab_results(since)
    out.append("## 🏆 A/B Test Outcomes")
    out.append(f"- **Total tests concluded**: {ab.get('total', 0)}")
    out.append(f"- **By winner**: {ab.get('by_winner', {})}")
    out.append(f"- **Avg win margin**: {ab.get('avg_margin', 0):.0%}")
    out.append(f"- **This week**: {ab.get('this_week', 0)} tests")
    if ab.get('total', 0) >= 3:
        winner_dist = ab.get('by_winner', {})
        seo = winner_dist.get('A_seo', 0)
        q   = winner_dist.get('B_question', 0)
        if seo > q * 2:
            out.append(f"- ✅ **Pattern: SEO-led wins {seo}/{seo+q}** — keep defaulting to SEO titles")
        elif q > seo * 2:
            out.append(f"- 🔄 **Pattern shift: Question-led winning {q}/{seo+q}** — consider switching default")
    out.append("")

    # ── Suno ──
    su = audit_suno(since)
    out.append("## 🎵 Suno Prompt Outcomes")
    out.append(f"- **Total logged**: {su['total']}")
    if su['total'] > 0:
        out.append(f"- **Avg quality (1-5)**: {su['avg_quality']}")
        out.append(f"- **By instrument**: {su['by_instrument']}")
        # Recommend recalibration for low-quality instruments
        weak = [i for i, q in su['by_instrument'].items() if q < 3]
        if weak:
            out.append(f"- ⚠️ **Instruments producing weak audio**: {weak} → recalibrate INSTRUMENT_MELODIC in suno.py")
    else:
        out.append(f"- _No Suno results logged yet. Use `pipeline/log_suno_result.py` (todo) after each shipped video._")
    out.append("")

    # ── Approvals ──
    ap = audit_approvals(since)
    out.append("## ✓ Approval Log")
    out.append(f"- **Approved**: {ap.get('approved', 0)}")
    out.append(f"- **Rejected**: {ap.get('rejected', 0)}")
    if ap.get('rejection_reasons'):
        out.append(f"- **Recent rejection reasons**:")
        for r in ap['rejection_reasons']:
            out.append(f"  - \"{r}\"")
    out.append("")

    # ── Channel growth ──
    ch = audit_channel_growth(since)
    out.append("## 📈 Channel Performance")
    out.append(f"- **Videos in dataset**: {ch['videos']}")
    out.append(f"- **Avg CTR**: {ch['avg_ctr']}% (best: {ch['best_ctr']}%)")
    out.append(f"- **Avg AVD%**: {ch['avg_avd']}% (best: {ch['best_avd']}%)")
    if ch['avg_ctr'] < 3:
        out.append("- ⚠️ Channel CTR avg below 3% — focus on thumbnail + title hook quality")
    if ch['best_ctr'] >= 5:
        out.append(f"- ✅ At least one breakout proven (CTR {ch['best_ctr']}%). Bank that formula.")
    out.append("")

    # ── Recommendations ──
    out.append("## 🎯 This Week's Recommended Actions")
    actions = []
    if kw['new_this_week'] < 5:
        actions.append("Run `pipeline/discover_problem_hooks.py` + paste top 5 in VidIQ → bank them")
    if su['total'] == 0:
        actions.append("After next published video, log Suno outcome via CLI (need to build) so we calibrate")
    if ab.get('total', 0) < 3:
        actions.append("Once 3 A/B tests concluded, recommend_lead_template() will become statistically grounded")
    if inv['retest_recommended']:
        actions.append(f"Re-test {len(inv['retest_recommended'])} stale invalidations (markets shift over 60+ days)")
    if not actions:
        actions.append("Banks are growing healthily — keep current cadence")
    for a in actions:
        out.append(f"- {a}")
    out.append("")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=(date.today() - timedelta(days=7)).isoformat(),
                    help="Window start date (YYYY-MM-DD)")
    args = ap.parse_args()

    body = render_review(args.since)
    out_path = REVIEW_DIR / f"{date.today().isoformat()}.md"
    out_path.write_text(body)
    print(f"✓ {out_path}")
    print()
    print(body)


if __name__ == "__main__":
    main()

"""
Rebuild data/performance_weights.json from the latest REACH_HISTORY.csv snapshot.

For each video_id, uses the most recent capture_date row.
Run: python3 pipeline/build_performance_weights.py
"""
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
REACH_CSV = DATA_DIR / "REACH_HISTORY.csv"
OUTPUT = DATA_DIR / "performance_weights.json"

INSTRUMENT_ALIASES = {
    "Bansuri":  ["bansuri", "bamboo flute"],
    "Sarangi":  ["sarangi"],
    "Dilruba":  ["dilruba"],
    "Veena":    ["veena"],
    "Sarod":    ["sarod"],
    "Santoor":  ["santoor", "santur"],
    "Esraj":    ["esraj"],
    "Tanpura":  ["tanpura"],
    "Sitar":    ["sitar"],
    "Surbahar": ["surbahar"],
    "Tabla":    ["tabla"],
    "Violin":   ["violin"],
    "Cello":    ["cello"],
    "Guitar":   ["guitar"],
    "Piano":    ["piano"],
}

PROBLEM_KEYWORDS = [
    "stress relief music", "sleep music", "deep relaxation music",
    "overthinking music", "meditation for anxiety", "unwind music",
    "deep rest music", "nervous system reset", "adhd focus music",
    "anxiety relief music", "calm your mind", "dopamine reset",
    "emotional healing music", "digital detox", "think clearly",
    "focus music", "concentration music", "healing music",
    "relaxation music", "insomnia relief", "burnout music",
]


def _detect_instrument(title: str) -> str:
    t = title.lower()
    for inst, aliases in INSTRUMENT_ALIASES.items():
        if any(a in t for a in aliases):
            return inst
    return ""


def _detect_problem_kw(title: str) -> str:
    t = title.lower()
    best = ""
    for kw in PROBLEM_KEYWORDS:
        tokens = [tok for tok in kw.split() if len(tok) >= 3]
        if tokens and all(tok in t for tok in tokens):
            if len(kw) > len(best):
                best = kw
    return best


def _latest_snapshots():
    if not REACH_CSV.exists():
        return []
    by_id: dict[str, dict] = {}
    with open(REACH_CSV) as f:
        for row in csv.DictReader(f):
            vid = row.get("video_id", "")
            if not vid:
                continue
            if vid not in by_id or row["capture_date"] > by_id[vid]["capture_date"]:
                by_id[vid] = row
    return list(by_id.values())


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if val not in ("", None) else default
    except (ValueError, TypeError):
        return default


def build():
    rows = _latest_snapshots()
    if not rows:
        return

    all_views = [_safe_float(r["views"]) for r in rows]
    all_ctr   = [_safe_float(r["ctr_pct"]) for r in rows]
    all_avd   = [_safe_float(r["avg_view_pct"]) for r in rows]

    ch_avg_views = sum(all_views) / len(all_views)
    ch_avg_ctr   = sum(all_ctr)   / len(all_ctr)
    ch_avg_avd   = sum(all_avd)   / len(all_avd)

    inst_buckets: dict[str, list] = defaultdict(list)
    kw_buckets:   dict[str, list] = defaultdict(list)

    for r in rows:
        title = r.get("title", "")
        v = _safe_float(r["views"])
        c = _safe_float(r["ctr_pct"])
        a = _safe_float(r["avg_view_pct"])
        wh = _safe_float(r.get("watch_hours", 0))

        inst = _detect_instrument(title)
        if inst:
            inst_buckets[inst].append((v, c, a, wh))

        kw = _detect_problem_kw(title)
        if kw:
            kw_buckets[kw].append((v, c, a, wh))

    def _summarise(buckets):
        out = {}
        for key, items in buckets.items():
            n = len(items)
            avg_v  = sum(i[0] for i in items) / n
            avg_c  = sum(i[1] for i in items) / n
            avg_a  = sum(i[2] for i in items) / n
            tot_wh = sum(i[3] for i in items)
            ps = (
                (avg_v / ch_avg_views if ch_avg_views else 1) * 0.4 +
                (avg_c / ch_avg_ctr   if ch_avg_ctr   else 1) * 0.3 +
                (avg_a / ch_avg_avd   if ch_avg_avd   else 1) * 0.3
            )
            out[key] = {
                "video_count":      n,
                "avg_views":        round(avg_v, 1),
                "avg_ctr_pct":      round(avg_c, 2),
                "avg_view_pct":     round(avg_a, 2),
                "total_watch_hours": round(tot_wh, 2),
                "performance_score": round(ps, 3),
            }
        return dict(sorted(out.items(), key=lambda x: -x[1]["performance_score"]))

    payload = {
        "generated_on": date.today().isoformat(),
        "channel_averages": {
            "avg_views":    round(ch_avg_views, 2),
            "avg_ctr_pct":  round(ch_avg_ctr, 2),
            "avg_view_pct": round(ch_avg_avd, 2),
        },
        "instruments":       _summarise(inst_buckets),
        "problem_keywords":  _summarise(kw_buckets),
    }

    OUTPUT.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    build()
    import sys
    data = json.loads(OUTPUT.read_text())
    print(f"Generated {OUTPUT.name} — {len(data['instruments'])} instruments, {len(data['problem_keywords'])} keywords")
    print(f"Channel avgs: {data['channel_averages']}")
    print("Top 5 instruments:")
    for k, v in list(data["instruments"].items())[:5]:
        print(f"  {k:<12} score={v['performance_score']:.2f}  views={v['avg_views']:.0f}  ctr={v['avg_ctr_pct']:.2f}%  avd={v['avg_view_pct']:.1f}%")
    print("Top 5 keywords:")
    for k, v in list(data["problem_keywords"].items())[:5]:
        print(f"  {k:<30} score={v['performance_score']:.2f}  views={v['avg_views']:.0f}")

"""Instrument cooldown check — run BEFORE recommending an instrument for any slot.

Enforces weekly_planning_rules.yaml §3 (4-day cooldown) by cross-checking:
1. Live channel ships (REACH_HISTORY.csv latest capture)
2. Queued briefs (data/video_briefs/*.json with status=DRAFT, planned_date >= target)

Usage:
    python3 pipeline/cooldown_check.py 2026-05-18
"""
import csv, json, glob, sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INSTRUMENTS = ['Sitar','Bansuri','Sarangi','Veena','Surbahar','Sarod','Santoor','Dilruba','Tanpura','Esraj','Violin','Oud']
MIN_GAP_DAYS = 4


def last_live_ship_per_instrument(target_date_str):
    """Most recent published ship per instrument from latest REACH_HISTORY capture."""
    history = DATA_DIR / "REACH_HISTORY.csv"
    rows = list(csv.DictReader(open(history)))
    # Use latest capture only
    latest_capture = max(r['capture_date'] for r in rows)
    rows = [r for r in rows if r['capture_date'] == latest_capture]
    last = {}
    for r in rows:
        title = r['title'].lower()
        pd = r.get('publish_date', '')
        if not pd:
            continue
        for inst in INSTRUMENTS:
            if inst.lower() in title:
                if inst not in last or pd > last[inst][0]:
                    last[inst] = (pd, r['title'])
    return last, latest_capture


def queued_ships_per_instrument(target_date_str):
    """All DRAFT briefs with planned_date >= target. Returns dict[instrument] -> list of (date, title)."""
    queued = {inst: [] for inst in INSTRUMENTS}
    for f in glob.glob(str(DATA_DIR / "video_briefs" / "*.json")):
        try:
            b = json.load(open(f))
            if b.get('status') != 'DRAFT':
                continue
            pd = b.get('planned_date', '')
            if not pd or pd < target_date_str:
                continue
            inst_field = (b.get('components', {}).get('instrument') or '').split()[0]
            if inst_field in INSTRUMENTS:
                queued[inst_field].append((pd, b.get('title', '')[:55]))
        except Exception:
            pass
    return queued


def main(target_date_str):
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    last, capture = last_live_ship_per_instrument(target_date_str)
    queued = queued_ships_per_instrument(target_date_str)

    print(f"\n=== INSTRUMENT COOLDOWN CHECK for {target_date_str} ===")
    print(f"(Data: REACH_HISTORY capture {capture} + queued briefs ≥ target date)")
    print(f"(Rule: ≥{MIN_GAP_DAYS}-day gap from last ship AND from queued ships, per weekly_planning_rules.yaml §3)\n")

    viable, blocked = [], []
    for inst in INSTRUMENTS:
        ls = last.get(inst)
        qs = queued.get(inst, [])
        flags, gap_back = [], None

        if ls:
            d = datetime.strptime(ls[0], '%Y-%m-%d').date()
            gap_back = (target_date - d).days
            if gap_back < MIN_GAP_DAYS:
                flags.append(f'❌ BACKWARD {gap_back}d')

        for qd_str, qt in qs:
            qd = datetime.strptime(qd_str, '%Y-%m-%d').date()
            forward = (qd - target_date).days
            if 0 < forward < MIN_GAP_DAYS:
                flags.append(f'⚠️ FORWARD +{forward}d')
            elif forward == 0:
                flags.append(f'⚠️ SAME DAY')

        last_str = f'last:{ls[0]}({gap_back}d)' if ls else 'last:none'
        queued_str = f' queued:{",".join(q[0] for q in qs)}' if qs else ''

        if flags:
            blocked.append(f'  {inst:10}  {last_str}{queued_str}  →  {", ".join(flags)}')
        else:
            viable.append(f'  {inst:10}  {last_str}{queued_str}  →  ✅ VIABLE')

    print('VIABLE:')
    for v in viable:
        print(v)
    print('\nBLOCKED:')
    for b in blocked:
        print(b)
    print(f'\nViable count: {len(viable)}/{len(INSTRUMENTS)}\n')


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else datetime.today().strftime('%Y-%m-%d')
    main(target)

"""Instrument cooldown check — run BEFORE recommending an instrument for any slot.

Enforces weekly_planning_rules.yaml §3 (5-day cooldown, upgraded from 4) by cross-checking:
1. Live channel ships (REACH_HISTORY.csv latest capture)
2. Queued briefs (data/video_briefs/*.json with status=DRAFT, planned_date >= target)

Cooldown evidence (Sitar, May 2026):
  3-day gap →  39K impressions
  5-day gap → 139K impressions  (3.6× better)
  6-day gap → 151K impressions  (3.9× better)

Lane-diversity override (manual judgment only — NOT enforced here):
  Same instrument + different audience lane = 3-day minimum acceptable.
  Example: Bansuri morning productivity → Bansuri deep sleep = different pool.
  This script enforces the 5-day hard rule. Override requires explicit human sign-off.

Usage:
    python3 pipeline/cooldown_check.py 2026-05-18
"""
import csv, json, glob, sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INSTRUMENTS = ['Sitar','Bansuri','Sarangi','Veena','Surbahar','Sarod','Santoor','Dilruba','Tanpura','Esraj','Violin','Oud']
MIN_GAP_DAYS = 5   # upgraded from 4 — data shows 3-day gap = 39K vs 5-day = 139K (3.6× penalty)

# Tier labels for display — from weekly_planning_rules.yaml §4 (data-backed May 2026)
INSTRUMENT_TIER = {
    'Sitar':    '🔥 HERO   (avg 247K impr)',
    'Bansuri':  '🔥 HERO   (avg 247K impr)',
    'Sarangi':  '⚡ STRONG (avg  75K impr)',
    'Surbahar': '⚡ STRONG (avg  75K impr)',
    'Dilruba':  '⚡ STRONG (avg  75K impr)',
    'Sarod':    '⚡ STRONG (avg  75K impr)',
    'Santoor':  '   FILLER (avg  32K impr)',
    'Veena':    '   FILLER (avg  32K impr)',
    'Tanpura':  '   FILLER (avg  32K impr)',
    'Esraj':    '   EXPERIMENTAL',
    'Violin':   '   EXPERIMENTAL',
    'Oud':      '   EXPERIMENTAL',
}


def last_live_ship_per_instrument(target_date_str):
    """Most recent published ship per instrument — merges REACH_HISTORY + shipped_titles.csv."""
    # Source 1: REACH_HISTORY (live channel snapshot)
    history = DATA_DIR / "REACH_HISTORY.csv"
    rows = list(csv.DictReader(open(history)))
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

    # Source 2: shipped_titles.csv (keeps up to date as we log new ships)
    shipped = DATA_DIR / "shipped_titles.csv"
    if shipped.exists():
        for r in csv.DictReader(open(shipped)):
            pd = r.get('shipped_on', '')
            title = r.get('title', '').lower()
            if not pd or not title:
                continue
            for inst in INSTRUMENTS:
                if inst.lower() in title:
                    if inst not in last or pd > last[inst][0]:
                        last[inst] = (pd, r['title'])

    return last, latest_capture


def queued_ships_per_instrument(target_date_str):
    """All committed (not-yet-shipped) briefs (before AND after target).
    Returns dict[instrument] -> list of (date, title).
    Briefs before target act as backward constraints (ship hasn't landed in shipped_titles yet).
    Briefs after target act as forward constraints.
    Status source of truth = brief_status.json override (a LOCKED brief is APPROVED+, not DRAFT);
    filtering on DRAFT-only would make cooldown blind to locked ships. Instrument lives at the
    brief top level ('instrument'), NOT under 'components' (which is null) — the old code read
    components and silently matched nothing."""
    committed = ("DRAFT", "PENDING_REVIEW", "APPROVED", "IN_PRODUCTION", "RENDERED")
    status_override = {}
    sfile = DATA_DIR / "brief_status.json"
    if sfile.exists():
        try:
            status_override = json.load(open(sfile))
        except Exception:
            status_override = {}
    queued = {inst: [] for inst in INSTRUMENTS}
    for f in glob.glob(str(DATA_DIR / "video_briefs" / "*.json")):
        try:
            b = json.load(open(f))
            bid = b.get('id') or Path(f).stem
            status = status_override.get(bid, b.get('status', ''))
            if status not in committed:
                continue
            pd = b.get('planned_date', '')
            if not pd:
                continue
            inst_raw = (b.get('instrument') or (b.get('components') or {}).get('instrument') or '').split()
            inst_field = inst_raw[0] if inst_raw else ''
            if inst_field in INSTRUMENTS:
                queued[inst_field].append((pd, b.get('title', '')[:55]))
        except Exception:
            pass
    return queued


def main(target_date_str):
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    last, capture = last_live_ship_per_instrument(target_date_str)
    queued = queued_ships_per_instrument(target_date_str)

    dow = target_date.strftime('%A')
    dow_note = ''
    if dow == 'Monday':
        dow_note = ' ← HERO SLOT. Prioritise Sitar or Bansuri if viable (§4b).'
    elif dow in ('Saturday', 'Sunday'):
        dow_note = f' ← WEEKEND ({dow}). 22% impression dip vs weekday avg. Use Strong/Filler. Avoid Hero unless 6+ days rested AND no Monday within 2 days.'

    print(f"\n=== INSTRUMENT COOLDOWN CHECK for {target_date_str} ({dow}){dow_note} ===")
    print(f"(Data: REACH_HISTORY capture {capture} + queued briefs ≥ target date)")
    print(f"(Rule: ≥{MIN_GAP_DAYS}-day gap same lane | ≥3-day if lane-switch — see §3. Lane override = human judgment only.)\n")

    viable, blocked = [], []
    for inst in INSTRUMENTS:
        ls = last.get(inst)
        qs = queued.get(inst, [])
        flags, gap_back = [], None

        if ls:
            d = datetime.strptime(ls[0], '%Y-%m-%d').date()
            gap_back = (target_date - d).days
            if gap_back < MIN_GAP_DAYS:
                flags.append(f'❌ BACKWARD {gap_back}d (shipped)')

        for qd_str, qt in qs:
            qd = datetime.strptime(qd_str, '%Y-%m-%d').date()
            delta = (qd - target_date).days
            if delta < 0:
                # Planned BEFORE target — treat as backward constraint
                gap_back_queued = -delta
                if gap_back_queued < MIN_GAP_DAYS:
                    if gap_back is None or gap_back_queued < gap_back:
                        flags.append(f'❌ BACKWARD {gap_back_queued}d (queued)')
            elif delta == 0:
                flags.append(f'⚠️ SAME DAY (queued)')
            elif 0 < delta < MIN_GAP_DAYS:
                flags.append(f'⚠️ FORWARD +{delta}d (queued)')

        last_str = f'last:{ls[0]}({gap_back}d)' if ls else 'last:none'
        queued_str = f' queued:{",".join(q[0] for q in qs)}' if qs else ''

        tier = INSTRUMENT_TIER.get(inst, '')
        if flags:
            blocked.append(f'  {inst:10}  {tier:<32}  {last_str}{queued_str}  →  {", ".join(flags)}')
        else:
            viable.append(f'  {inst:10}  {tier:<32}  {last_str}{queued_str}  →  ✅ VIABLE')

    print('VIABLE:')
    for v in viable:
        print(v)
    print('\nBLOCKED:')
    for b in blocked:
        print(b)
    print(f'\nViable count: {len(viable)}/{len(INSTRUMENTS)}')
    print(f'\n📌 REMINDER §4b: Monday PM → Hero first. Weekend → Strong/Filler only.\n')


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else datetime.today().strftime('%Y-%m-%d')
    main(target)

#!/usr/bin/env python3
"""
CLI helper to bank a newly-validated keyword (e.g., from competitor analysis).

Usage:
    python3 add_keyword.py --phrase "Healing Ragas For Overthinkers" --slot problem --score 65 --comp "Low" --from "Shanti Apr 17"

    python3 add_keyword.py --phrase "Theta Wave Healing Session" --slot wave --score 62

    python3 add_keyword.py --phrase "Raga Hamir" --slot raga --score 58 --mood evening_serene

    python3 add_keyword.py  (interactive — asks each field)
"""

import argparse
import sys
from keyword_bank import append_keyword


VALID_SLOTS = {"problem", "wave", "raga", "hz", "instrument"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrase", help="The keyword phrase as you'd write it in a title")
    ap.add_argument("--slot", choices=sorted(VALID_SLOTS),
                    help="Which title slot this fills")
    ap.add_argument("--score", type=int, help="VidIQ score 0-100")
    ap.add_argument("--comp", default="", help="VidIQ competition (Low/Med/High/Very Low)")
    ap.add_argument("--from", dest="source", default="",
                    help="Where you found this (e.g., 'Shanti Apr 17', 'Raga Heal RSS')")
    args = ap.parse_args()

    phrase = args.phrase or input("phrase: ").strip()
    slot   = args.slot   or input(f"slot ({'/'.join(sorted(VALID_SLOTS))}): ").strip()
    score  = args.score  if args.score is not None else int(input("vidiq score (0-100): ").strip())
    comp   = args.comp   or input("vidiq comp (Low/Med/High/Very Low) [optional]: ").strip()
    src    = args.source or input("source [optional]: ").strip() or "manual"

    if slot not in VALID_SLOTS:
        sys.exit(f"❌ slot must be one of {VALID_SLOTS}")
    if score < 0 or score > 100:
        sys.exit(f"❌ score out of range")

    append_keyword(phrase, slot, vidiq_score=score, vidiq_comp=comp, source=src)
    print(f"✓ Banked: {phrase} ({slot}, score {score})")


if __name__ == "__main__":
    main()

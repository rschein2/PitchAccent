#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Differential accent comparison: our engine vs pyopenjtalk (OpenJTalk).

pyopenjtalk is an independent accent estimator — NOT gold data. Use this as
a triage signal: where pyopenjtalk agrees with OJAD but we differ, look for
a bug on our side; where we agree with OJAD and pyopenjtalk differs, it's
their weakness. For words outside the OJAD corpus, a 2-way disagreement
just means "worth a human look".

Requires: pip install pyopenjtalk-plus  (graceful skip if missing)

Usage:
    python scripts/compare_pyopenjtalk.py            # over OJAD gold corpus
    python scripts/compare_pyopenjtalk.py --words 食べます 安全保障 ...
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pyopenjtalk
except ImportError:
    print("pyopenjtalk not installed (pip install pyopenjtalk-plus) — skipping.")
    sys.exit(0)

from pitch_accent.engine import FugashiAccentEngine

GOLD_FILE = Path(__file__).parent.parent / "tests" / "gold" / "ojad_verbs.json"


def ojt_accent(text: str):
    """
    Accent of the first accent phrase per OpenJTalk full-context labels.

    Returns (accent, mora_count, n_phrases) or None. accent 0 = heiban.
    """
    labels = pyopenjtalk.extract_fullcontext(text)
    first = None
    phrases = set()
    for label in labels:
        m = re.search(r"/F:(\d+)_(\d+)#", label)
        if m and first is None:
            first = (int(m.group(2)), int(m.group(1)))
        i = re.search(r"/I:(\d+)-", label)
        if i:
            phrases.add(i.group(1))
    if first is None:
        return None
    return first[0], first[1], max(len(phrases), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", nargs="*", help="explicit words to compare")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap number of comparisons (0 = all)")
    args = ap.parse_args()

    engine = FugashiAccentEngine()

    if args.words:
        cases = [(w, None) for w in args.words]
    else:
        with open(GOLD_FILE, encoding="utf-8") as f:
            gold = json.load(f)
        cases = []
        for word, record in gold.items():
            entries = record.get("entries") or [record]
            jisho = entries[0]["forms"].get("jisho")
            cases.append((word, set(jisho["accents"]) if jisho else None))

    if args.limit:
        cases = cases[:args.limit]

    agree = differ = split = 0
    disagreements = []
    for word, ojad_accents in cases:
        ours = engine.analyze(word)
        theirs = ojt_accent(word)
        if theirs is None:
            continue
        ojt_acc, _, n_phrases = theirs
        if n_phrases > 1:
            split += 1
            continue

        our_set = {ours.accent_type, *ours.accent_variants}
        if ojt_acc in our_set:
            agree += 1
        else:
            differ += 1
            # 3-way verdict when OJAD data is available
            verdict = ""
            if ojad_accents is not None:
                we_match = bool(our_set & ojad_accents)
                they_match = ojt_acc in ojad_accents
                if they_match and not we_match:
                    verdict = "CHECK-US"     # they agree with OJAD, we don't
                elif we_match and not they_match:
                    verdict = "their-miss"
                else:
                    verdict = "both-differ-from-OJAD"
            disagreements.append((word, ours.reading, sorted(our_set),
                                  ojt_acc, verdict))

    total = agree + differ
    print(f"\npyopenjtalk comparison: {agree}/{total} agree, "
          f"{differ} differ, {split} skipped (multi-phrase)")
    if disagreements:
        print("\nDisagreements (ours vs pyopenjtalk):")
        for word, reading, our_set, ojt_acc, verdict in disagreements:
            flag = f"  [{verdict}]" if verdict else ""
            print(f"  {word} [{reading}] ours={our_set} ojt=[{ojt_acc}]{flag}")


if __name__ == "__main__":
    main()

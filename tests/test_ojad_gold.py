# -*- coding: utf-8 -*-
"""
Compare the accent engine against the OJAD-mined gold corpus.

Gold data: tests/gold/ojad_verbs.json (built by scripts/build_ojad_gold.py).
For every verb and conjugation form, this constructs the written surface,
runs FugashiAccentEngine.analyze, and checks the result against OJAD's
accent(s). A case passes if the engine's accent matches ANY OJAD variant.

Cases where our constructed reading differs from OJAD's kana are counted
as SKIP (form-construction mismatch, not an accent bug).

KNOWN_DISAGREEMENTS documents triaged cases where we deliberately differ
from OJAD; everything else must match.

Run:  python tests/test_ojad_gold.py [-v]   or   pytest tests/test_ojad_gold.py
"""
import json
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pitch_accent.engine import FugashiAccentEngine
from pitch_accent.verb_conjugator import VerbConjugator, GODAN_CONJUGATIONS

GOLD_FILE = Path(__file__).parent / "gold" / "ojad_verbs.json"

# (verb, form) -> reason. Deliberate, triaged divergences from OJAD only.
_NAKUSU = ("MeCab segments the isolated fragment as 無く(ない)+し(する), not "
           "無くす — tokenization artifact, not an accent-rule bug; the "
           "dictionary form itself resolves correctly")
KNOWN_DISAGREEMENTS: dict[tuple[str, str], str] = {
    ("無くす", "te"): _NAKUSU,
    ("無くす", "ta"): _NAKUSU,
    ("無くす", "nai"): _NAKUSU,
    ("無くす", "nakatta"): _NAKUSU,
    ("無くす", "shieki"): _NAKUSU,
    ("無くす", "ukemi"): _NAKUSU,
    ("無くす", "meirei"): _NAKUSU,
    ("無くす", "kano"): _NAKUSU,
    ("無くす", "ishi"): _NAKUSU,
    ("通る", "meirei"): (
        "MeCab parses the isolated fragment 通れ as the potential verb 通れる's "
        "renyokei [2], while OJAD's row is the imperative of 通る [1]; both are "
        "valid readings of the bare fragment"),
}

# Suffixes per OJAD form for ichidan verbs (attach to kanji stem)
ICHIDAN_FORMS = {
    "jisho": "る", "masu": "ます", "te": "て", "ta": "た",
    "nai": "ない", "nakatta": "なかった", "ba": "れば",
    "shieki": "させる", "ukemi": "られる", "meirei": "ろ",
    "kano": "られる", "ishi": "よう",
}

SURU_FORMS = {
    "jisho": "する", "masu": "します", "te": "して", "ta": "した",
    "nai": "しない", "nakatta": "しなかった", "ba": "すれば",
    "shieki": "させる", "ukemi": "される", "meirei": "しろ",
    "kano": "できる", "ishi": "しよう",
}

KURU_FORMS = {
    "jisho": "来る", "masu": "来ます", "te": "来て", "ta": "来た",
    "nai": "来ない", "nakatta": "来なかった", "ba": "来れば",
    "shieki": "来させる", "ukemi": "来られる", "meirei": "来い",
    "kano": "来られる", "ishi": "来よう",
}

# Godan: per-row kana pieces. GODAN_CONJUGATIONS provides te/ta/nai/masu/ba/
# you/potential pieces; derive the rest from the same row characters.
def godan_surface(kanji_stem: str, row: str, form: str, lemma: str) -> str | None:
    table = GODAN_CONJUGATIONS.get(row)
    if not table:
        return None

    # 行く irregular te/ta
    if lemma == "行く" and form in ("te", "ta"):
        return {"te": "行って", "ta": "行った"}[form]

    a_char = table["nai"][0]      # e.g. か
    i_char = table["masu"][0]     # e.g. き
    e_char = table["ba"][0]       # e.g. け
    o_char = table["you"][0]      # e.g. こ

    if form == "jisho":
        return lemma
    if form == "masu":
        return kanji_stem + i_char + "ます"
    if form == "te":
        return kanji_stem + table["te"][0] + table["te"][1]
    if form == "ta":
        return kanji_stem + table["ta"][0] + table["ta"][1]
    if form == "nai":
        return kanji_stem + a_char + "ない"
    if form == "nakatta":
        return kanji_stem + a_char + "なかった"
    if form == "ba":
        return kanji_stem + e_char + "ば"
    if form == "shieki":
        return kanji_stem + a_char + "せる"
    if form == "ukemi":
        return kanji_stem + a_char + "れる"
    if form == "meirei":
        return kanji_stem + e_char
    if form == "kano":
        return kanji_stem + e_char + "る"
    if form == "ishi":
        return kanji_stem + o_char + "う"
    return None


def build_surface(verb_info: dict, verb: str, form: str) -> str | None:
    vtype = verb_info["verb_type"]
    stem = verb_info.get("kanji_stem", "")
    if vtype == "godan":
        return godan_surface(stem, verb_info["row"], form, verb)
    if vtype == "ichidan":
        return verb if form == "jisho" else stem + ICHIDAN_FORMS[form]
    if vtype == "suru":
        return SURU_FORMS.get(form)
    if vtype == "kuru":
        return KURU_FORMS.get(form)
    return None


def run(verbose: bool = False):
    with open(GOLD_FILE, encoding="utf-8") as f:
        gold = json.load(f)

    engine = FugashiAccentEngine()
    conjugator = VerbConjugator()

    passed = failed = skipped = known = 0
    failures = []

    for verb, entry in gold.items():
        verb_info = conjugator.detect_verb_type(verb)
        if not verb_info:
            skipped += len(entry["forms"])
            continue

        for form, gdata in entry["forms"].items():
            surface = build_surface(verb_info, verb, form)
            if not surface:
                skipped += 1
                continue

            result = engine.analyze(surface)
            if result.reading != gdata["kana"]:
                # We built a different form than OJAD shows (rare orthography
                # or parse differences) — not an accent comparison.
                skipped += 1
                if verbose:
                    print(f"SKIP {verb}/{form}: reading {result.reading} != {gdata['kana']}")
                continue

            if result.accent_type in set(gdata["accents"]):
                passed += 1
            elif (verb, form) in KNOWN_DISAGREEMENTS:
                known += 1
            else:
                failed += 1
                failures.append((verb, form, surface, result.accent_type, gdata["accents"]))
                if verbose:
                    print(f"FAIL {verb}/{form} {surface} [{result.reading}] "
                          f"got=[{result.accent_type}] ojad={gdata['accents']}")

    total = passed + failed + known
    print(f"\nOJAD gold: {passed}/{total} matched, {known} known disagreements, "
          f"{skipped} skipped (form mismatch)")
    if failures:
        print("\nFailures by form:")
        by_form: dict[str, int] = {}
        for _, form, *_ in failures:
            by_form[form] = by_form.get(form, 0) + 1
        for form, n in sorted(by_form.items(), key=lambda kv: -kv[1]):
            print(f"  {form}: {n}")
    return failures


def test_ojad_gold():
    """pytest entry point."""
    failures = run()
    assert not failures, f"{len(failures)} OJAD gold mismatches, e.g. {failures[:5]}"


if __name__ == "__main__":
    verbose = "-v" in sys.argv
    sys.exit(1 if run(verbose) else 0)

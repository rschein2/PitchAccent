# -*- coding: utf-8 -*-
"""
Regression tests for the pitch accent engine.

Gold values are standard Tokyo accent (NHK accent dictionary / OJAD).
Every case here was verified during the July 2026 rule audit; if a code
change makes one of these fail, the change is wrong (or the gold value
needs a documented correction — don't silently edit it).

Run:  python tests/test_accent.py        (plain script, exit code 0/1)
  or: pytest tests/test_accent.py
"""
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pitch_accent.engine import FugashiAccentEngine

# (surface, expected_accent_type, note)
GOLD = [
    # ---------- dictionary forms ----------
    ("食べる", 2, "taberu, accented ichidan"),
    ("見る", 1, "miru"),
    ("書く", 1, "kaku"),
    ("行く", 0, "iku, heiban"),

    # ---------- masu family: ます always accents on ま ----------
    ("食べます", 3, "tabema'su"),
    ("食べました", 3, "tabema'shita"),
    ("食べません", 4, "tabemase'n"),
    ("食べましょう", 4, "tabemasho'o (ましょう aModType M1@1)"),
    ("行きます", 3, "ikima'su — heiban verb still gets accent from masu"),
    ("行きました", 3, "ikima'shita"),
    ("行きません", 4, "ikimase'n"),
    ("行きましょう", 4, "ikimasho'o"),
    ("書きます", 3, "kakima'su"),
    ("見ます", 2, "mima'su"),
    ("見ました", 2, "mima'shita"),
    ("します", 2, "shima'su"),
    ("しました", 2, "shima'shita"),
    ("来ます", 2, "kima'su"),
    ("読みます", 3, "yomima'su"),
    ("分かります", 4, "wakarima'su"),
    ("食べられます", 5, "taberarema'su"),

    # ---------- past tense: heiban stays heiban (ta override -> F1) ----------
    ("行った", 0, "itta — heiban past stays flat"),
    ("買った", 0, "katta"),
    ("言った", 0, "itta"),
    ("聞いた", 0, "kiita"),
    ("使った", 0, "tsukatta"),
    ("食べた", 1, "ta'beta — accented preserves stem accent"),
    ("書いた", 1, "ka'ita"),
    ("読んだ", 1, "yo'nda"),
    ("見た", 1, "mi'ta"),

    # ---------- te-form ----------
    ("食べて", 1, "ta'bete"),
    ("書いて", 1, "ka'ite"),
    ("行って", 0, "itte, heiban stays flat"),

    # ---------- negative ----------
    ("食べない", 2, "tabe'nai"),
    ("行かない", 0, "ikanai, heiban stays flat"),
    ("書かない", 2, "kaka'nai"),
    ("食べなかった", 2, "tabe'nakatta — keeps the accent of 食べない[2] "
                        "(OJAD; was wrongly [3] before the 形容詞-タ override)"),
    ("行かなかった", 3, "ikana'katta — past negative gains accent "
                        "(parallel to 高かった[2]; UniDic なかっ M2@2)"),

    # ---------- conditional ----------
    ("食べれば", 2, "tabe'reba"),
    ("行けば", 2, "ike'ba — heiban gains accent before ba"),
    ("食べたら", 1, "ta'betara"),
    ("行ったら", 3, "itta'ra — heiban gains accent before ra "
                     "(UniDic たら M2@1, parallel to 行けば)"),

    # ---------- volitional: always accented on penult ----------
    ("食べよう", 3, "tabeyo'o"),
    ("行こう", 2, "iko'o — heiban volitional is still accented"),
    ("書こう", 2, "kako'o"),

    # ---------- desiderative ----------
    ("飲みたい", 3, "nomita'i"),
    ("食べたかった", 3, "tabeta'katta"),

    # ---------- passive / potential / causative ----------
    ("食べられる", 4, "tabera'reru"),
    ("食べられて", 3, "tabera'rete (られ aModType M4@1)"),
    ("食べられた", 3, "tabera'reta"),
    ("行かれる", 0, "ikareru, heiban stays flat (F3)"),
    ("書かれる", 3, "kakare'ru"),

    # ---------- te + auxiliary verb (not a noun compound!) ----------
    ("食べている", 1, "ta'beteiru — unaccented aux keeps te-form accent"),
    ("行っている", 0, "itteiru — flat stays flat"),
    ("食べています", 5, "tabeteima'su"),
    ("食べていた", 1, "ta'beteita"),
    ("書いてある", 4, "kaitea'ru — aru is accented [1], unlike iru [0]"),
    ("食べてみる", 4, "tabetemi'ru — accented aux takes N1+M2"),
    ("行ってくる", 4, "itteku'ru"),

    # ---------- renyokei compound verbs: accent on V2 penult ----------
    ("食べ始める", 5, "tabehajime'ru"),
    ("書き直す", 4, "kakinao'su"),

    # ---------- contracted forms (colloquial) ----------
    ("食べてる", 1, "ta'beteru — ~てる like ~ている"),
    ("行ってる", 0, "itteru, heiban stays flat"),
    ("見てる", 1, "mi'teru"),
    ("食べてた", 1, "ta'beteta"),
    ("食べちゃう", 1, "ta'bechau — ~ちゃう preserves like ~てしまう"),
    ("食べちゃった", 1, "ta'bechatta"),
    ("行っちゃった", 0, "itchatta, heiban stays flat"),
    ("飲んじゃう", 1, "no'njau"),
    ("飲んじゃった", 1, "no'njatta"),
    ("買っとく", 0, "kattoku — ~とく like ~ておく"),
    ("食べときます", 5, "tabetokima'su"),

    # ---------- nouns (single-word sanity) ----------
    ("箸", 1, "ha'shi chopsticks"),
    ("橋", 2, "hashi' bridge (odaka)"),
    ("端", 0, "hashi edge (heiban)"),
]


def run():
    engine = FugashiAccentEngine()
    failures = []

    for surface, expected, note in GOLD:
        result = engine.analyze(surface)
        ok = result.accent_type == expected
        mark = "OK  " if ok else "FAIL"
        print(f"{mark} {surface} [{result.reading}] got=[{result.accent_type}] "
              f"want=[{expected}]  {note}")
        if not ok:
            for step in result.breakdown:
                print(f"       {step}")
            failures.append((surface, expected, result.accent_type))

    print(f"\n{len(GOLD) - len(failures)}/{len(GOLD)} passed")
    return failures


def test_gold_accents():
    """pytest entry point."""
    failures = run()
    assert not failures, f"{len(failures)} gold cases failed: {failures}"


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

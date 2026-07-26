# -*- coding: utf-8 -*-
"""
Tests for the table-driven numeral + counter accent system.

The 1-10 core values come from data/numeral_accent.json (extracted from
the 日本語教育用アクセント辞典, accent.u-biq.org). Cells marked "drafted"
in the data file are pending NHK verification but still asserted here so
regressions are caught.

Run:  python tests/test_numeral.py   or   pytest tests/test_numeral.py
"""
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pitch_accent.numeral import (
    compute_numeral_phrase_accent,
    parse_numeral_value,
)


def test_parse_numeral_value():
    assert parse_numeral_value("3") == 3
    assert parse_numeral_value("３") == 3          # full-width
    assert parse_numeral_value("三") == 3
    assert parse_numeral_value("二十四") == 24
    assert parse_numeral_value("1952") == 1952
    assert parse_numeral_value("三千") == 3000
    assert parse_numeral_value("一万二千") == 12000
    assert parse_numeral_value("六万") == 60000
    assert parse_numeral_value("本") is None


def test_table_core():
    # (numeral, counter, reading, accent) — verified u-biq values
    cases = [
        (1, "本", "いっぽん", 1),
        (2, "本", "にほん", 1),
        (3, "本", "さんぼん", 1),
        (10, "本", "じゅっぽん", 1),
        (1, "人", "ひとり", 2),
        (2, "人", "ふたり", 3),
        (3, "人", "さんにん", 3),
        (4, "人", "よにん", 2),
        (1, "回", "いっかい", 3),
        (1, "階", "いっかい", 0),   # homophone of 一回, different accent
        (2, "階", "にかい", 0),
        (1, "年", "いちねん", 2),
        (3, "年", "さんねん", 0),
        (1, "分", "いっぷん", 1),
        (7, "分", "ななふん", 2),
        (4, "時", "よじ", 1),
        (9, "時", "くじ", 1),
        (1, "日", "ついたち", 4),
        (3, "日", "みっか", 0),
        (1, "個", "いっこ", 1),
        (3, "枚", "さんまい", 1),
        (1, "歳", "いっさい", 1),
        (3, "匹", "さんびき", 1),
    ]
    for numeral, counter, reading, accent in cases:
        got = compute_numeral_phrase_accent(numeral, counter)
        assert got is not None, f"{numeral}{counter}: no result"
        g_accent, g_reading, rule, conf = got
        assert (g_reading, g_accent) == (reading, accent), (
            f"{numeral}{counter}: got {g_reading}[{g_accent}], "
            f"want {reading}[{accent}] ({rule})")


def test_confidence_passthrough():
    got = compute_numeral_phrase_accent(3, "冊")
    assert got is not None
    accent, reading, rule, conf = got
    assert (reading, accent) == ("さんさつ", 1)
    assert conf == "verified"
    # odaka cells from the site (my analogy draft had these wrong — data wins)
    assert compute_numeral_phrase_accent(8, "冊")[0] == 4


def test_compositional():
    cases = [
        (30, "分", "さんじゅっぷん", 3),
        (37, "分", "さんじゅうななふん", 6),
        (21, "分", "にじゅういっぷん", 4),
        (24, "日", "にじゅうよっか", 0),
        (2024, "年", "にせんにじゅうよねん", 0),
        (18, "歳", "じゅうはっさい", 3),
        (11, "人", "じゅういちにん", None),  # suppletive ひとり must NOT compose
        (12, "日", None, None),              # じゅうふつか would be wrong
    ]
    for numeral, counter, reading, accent in cases:
        got = compute_numeral_phrase_accent(numeral, counter)
        if reading is None:
            assert got is None, f"{numeral}{counter}: expected fallback, got {got}"
        elif accent is None:
            # Suppletive final: must either fall back or NOT use the
            # suppletive reading
            assert got is None or "ひとり" not in got[1], f"{numeral}{counter}: {got}"
        else:
            assert got is not None, f"{numeral}{counter}: no result"
            g_accent, g_reading, rule, conf = got
            assert (g_reading, g_accent) == (reading, accent), (
                f"{numeral}{counter}: got {g_reading}[{g_accent}], "
                f"want {reading}[{accent}]")
            assert conf == "extrapolated"


def test_unknown_counter_falls_back():
    assert compute_numeral_phrase_accent(100, "円") is None  # not in table


def test_parser_routing():
    """Counters with awkward UniDic tags (冊: 接尾辞/名詞的/一般) must reach
    the numeral engine, and the table reading (with sandhi) must win."""
    from pitch_accent.parser import SentenceParser
    p = SentenceParser()

    words = {w.surface: w for w in
             p.parse_sentence("3冊の本と五人の客。").content_words()}
    assert words["3冊"].source == "numeral"
    assert words["3冊"].reading == "さんさつ"
    assert words["3冊"].aType == "1"
    assert words["五人"].source in ("numeral", "dictionary")
    assert words["五人"].reading == "ごにん"

    words = {w.surface: w for w in
             p.parse_sentence("三十分かかる。").content_words()}
    assert words["三十分"].reading == "さんじゅっぷん"
    assert words["三十分"].aType == "3"


def run():
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"OK   {name}")
            except AssertionError as exc:
                print(f"FAIL {name}: {exc}")
                failures.append(name)
    print(f"\n{'PASS' if not failures else 'FAIL'}")
    return failures


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

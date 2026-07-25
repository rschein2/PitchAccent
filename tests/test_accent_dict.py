# -*- coding: utf-8 -*-
"""
Tests for the Kanjium accent dictionary layer.

Run:  python tests/test_accent_dict.py   or   pytest tests/test_accent_dict.py
"""
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pitch_accent.accent_dict import get_accent_dictionary


def test_dictionary_loads():
    d = get_accent_dictionary()
    assert d is not None, "data/kanjium/accents.txt.gz missing?"
    assert len(d) > 100_000


def test_basic_lookup():
    d = get_accent_dictionary()
    assert d.lookup("食べる", "たべる") == [2]
    assert d.lookup("行く", "いく") == [0]
    assert d.lookup("図書館", "としょかん") == [2]


def test_homograph_disambiguation():
    d = get_accent_dictionary()
    # あめ: rain [1] vs candy [0]
    assert d.lookup("雨", "あめ") == [1]
    assert d.lookup("飴", "あめ") == [0]
    # 端 has many readings; はし is heiban
    assert d.lookup("端", "はし") == [0]
    assert d.lookup("端", "たん") == [1]
    # Ambiguous surface without reading -> None
    assert d.lookup("端") is None
    # Unambiguous surface without reading -> works
    assert d.lookup("食べる") == [2]


def test_katakana_reading_normalized():
    d = get_accent_dictionary()
    # UniDic returns katakana readings; lookup must accept them
    assert d.lookup("食べる", "タベル") == [2]


def test_variants():
    d = get_accent_dictionary()
    assert d.lookup("持ち込む", "もちこむ") == [0, 3]


def test_missing_word():
    d = get_accent_dictionary()
    assert d.lookup("食べました") is None  # conjugated forms not in dict


def test_engine_whole_word_priority():
    from pitch_accent.engine import FugashiAccentEngine
    e = FugashiAccentEngine()
    # Lexicalized compound: dictionary [5] beats computed sandhi
    r = e.analyze("安全保障")
    assert r.accent_type == 5
    assert "dictionary" in r.breakdown[0]
    # Variants exposed
    r = e.analyze("持ち込む")
    assert r.accent_type == 0
    assert r.accent_variants == [0, 3]
    # Conjugated forms still go through rules
    r = e.analyze("食べました")
    assert r.accent_type == 3


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

#!/usr/bin/env python3
"""
Numeral + Counter Accent for Tokyo Japanese — table-driven.

The 1-10 core comes from a curated table (data/numeral_accent.json,
extracted from the 日本語教育用アクセント辞典, accent.u-biq.org): there is
no phonological rule that predicts 三人[3] vs 三年[0], so the core is
lexical. Beyond 10 the accent is compositional: a compound numeral takes
the accent behavior of its final element (37分 sounds like …ななふん[2]
shifted right; 2024年 ends in よねん[0] so the whole stays flat).

Readings for the 1-10 core also come from the table (they encode the
gemination/voicing sandhi: いっぷん, さんぼん, ついたち); larger numbers
are assembled from numeral_reading.number_to_reading plus the table
reading of the final element.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .numeral_reading import number_to_reading
from .utils import count_mora

TABLE_FILE = Path(__file__).parent.parent / "data" / "numeral_accent.json"

_table: Optional[dict] = None


def _load_table() -> dict:
    global _table
    if _table is None:
        if TABLE_FILE.exists():
            with open(TABLE_FILE, encoding="utf-8") as f:
                _table = json.load(f)["counters"]
        else:
            _table = {}
    return _table


# Readings a table cell may start with for the compositional rule to apply.
# Productive sandhi variants (いっ, ろっ, じゅっ, よ...) compose into larger
# numbers (21分=にじゅういっぷん, 24日=にじゅうよっか); suppletive readings
# (ひとり, ふつか, ついたち, とおか) do NOT (12日 is じゅうににち, never
# じゅうふつか) — those cells are rejected and the caller falls back.
COMPOSABLE_PREFIXES = {
    1: ("いっ", "いち"), 2: ("に",), 3: ("さん",), 4: ("よん", "よ"),
    5: ("ご",), 6: ("ろく", "ろっ"), 7: ("なな", "しち"),
    8: ("はち", "はっ"), 9: ("きゅう", "く"),
    10: ("じゅう", "じゅっ", "じっ"),
}

# Kanji numeral values (for surfaces like 三人, 二十日)
KANJI_DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4,
                "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
KANJI_PLACES = {"十": 10, "百": 100, "千": 1000, "万": 10000, "億": 100000000}
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def parse_numeral_value(surface: str) -> Optional[int]:
    """
    Parse a numeral surface — arabic (half/full width) or kanji — to int.
    Returns None if it can't be parsed.
    """
    s = surface.translate(FULLWIDTH_DIGITS)
    if s.isdigit():
        return int(s)

    # Kanji numerals: 二十四 = 24, 三千 = 3000, 一万二千 = 12000
    total = 0
    section = 0   # value below the current big place (万/億)
    digit = 0
    seen_any = False
    for ch in s:
        if ch in KANJI_DIGITS:
            digit = KANJI_DIGITS[ch]
            seen_any = True
        elif ch in ("十", "百", "千"):
            section += (digit or 1) * KANJI_PLACES[ch]
            digit = 0
            seen_any = True
        elif ch in ("万", "億"):
            section += digit
            total += (section or 1) * KANJI_PLACES[ch]
            section = 0
            digit = 0
            seen_any = True
        else:
            return None
    if not seen_any:
        return None
    return total + section + digit


def compute_numeral_phrase_accent(
    numeral: int,
    counter: str,
    counter_accent: int = 0,
) -> Optional[tuple[int, str, str, str]]:
    """
    Compute accent for numeral + counter.

    Returns (accent_type, reading, rule, confidence), or None when the
    counter isn't in the table (caller should fall back to compound rules).
    """
    table = _load_table()
    entry = table.get(counter)
    if not entry:
        return None
    numerals = entry["numerals"]
    confidence = entry.get("confidence", "verified")

    # Direct hit for the lexical 1-10 core
    cell = numerals.get(str(numeral))
    if cell:
        return (cell["accent"], cell["reading"],
                f"table:{counter}/{numeral}", confidence)

    if numeral <= 10 or numeral > 10**16:
        return None

    # Compositional: prefix reading + the table cell of the final element.
    # 37分 = さんじゅう + ななふん;  30分 = さん + じゅっぷん (final element 10)
    full = number_to_reading(numeral)
    if numeral % 10 != 0:
        final = numeral % 10
    else:
        final = 10
        if not full.endswith("じゅう"):
            return None  # 100分 etc. — no table anchor, let caller fall back
    cell = numerals.get(str(final))
    if not cell:
        return None
    if not cell["reading"].startswith(COMPOSABLE_PREFIXES.get(final, ())):
        return None  # suppletive reading (ひとり, ふつか) — not composable

    final_reading = number_to_reading(final)
    if not full.endswith(final_reading):
        return None
    prefix = full[: len(full) - len(final_reading)]

    reading = prefix + cell["reading"]
    if cell["accent"] == 0:
        accent = 0
    else:
        accent = count_mora(prefix) + cell["accent"]
    return (accent, reading,
            f"compositional:{counter}/{final}", "extrapolated")


@dataclass
class NumeralPhraseResult:
    """Result of numeral phrase processing."""
    surface: str
    reading: str
    accent_type: int
    mora_count: int
    numeral: int
    counter: str
    rule: str


class NumeralAccentEngine:
    """
    Engine for computing numeral phrase accent.
    """

    def process_numeral_phrase(
        self,
        numeral_morphemes: list[dict],
        counter_morpheme: dict,
    ) -> Optional[dict]:
        """
        Process a numeral + counter combination.

        Returns a merged morpheme dict with computed accent, or None when
        the counter isn't covered by the table (the caller should fall back
        to compound-noun rules).
        """
        numeral_surface = "".join(m.get("surface", "") for m in numeral_morphemes)
        numeral = parse_numeral_value(numeral_surface)
        if numeral is None:
            return None

        counter = counter_morpheme.get("surface", "")
        result = compute_numeral_phrase_accent(numeral, counter)
        if result is None:
            return None
        accent, reading, rule, confidence = result

        merged_surface = numeral_surface + counter
        return {
            "surface": merged_surface,
            "reading": reading,
            "pos1": "名詞",
            "pos2": "数詞句",
            "aType": str(accent),
            "aConType": "*",
            "aModType": "*",
            "cType": "*",
            "cForm": "*",
            "lemma": merged_surface,
            "_numeral_rule": rule,
            "_numeral_confidence": confidence,
            "_numeral": numeral,
            "_counter": counter,
        }


def main():
    """Quick demo."""
    tests = [(1, "本"), (3, "本"), (10, "本"), (3, "人"), (5, "人"),
             (1, "回"), (2, "階"), (7, "分"), (30, "分"), (37, "分"),
             (4, "時"), (24, "日"), (2024, "年"), (3, "冊"), (100, "円")]
    for n, c in tests:
        r = compute_numeral_phrase_accent(n, c)
        if r:
            accent, reading, rule, conf = r
            print(f"{n}{c}: {reading} [{accent}] ({rule}, {conf})")
        else:
            print(f"{n}{c}: no table entry (falls back to compound rules)")


if __name__ == "__main__":
    main()

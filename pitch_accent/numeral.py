#!/usr/bin/env python3
"""
Numeral Phrase Accent for Tokyo Japanese

Implements the Miyazaki-style numeral × counter rule system.
Counters are classified into categories (α-ν), and a lookup table
determines whether to use normal sandhi (0), force heiban (1),
accent counter-initial (2), or accent counter-final (3).

References:
- Miyazaki et al. (2012) ASJ paper on numeral accent
- https://www.gavo.t.u-tokyo.ac.jp/~mine/paper/PDF/2012/ASJ_1-11-11_p319-322_t2012-3.pdf
"""
from dataclasses import dataclass
from typing import Optional


# Counter categories (α-ν) based on Miyazaki classification
# Each counter is assigned to a category that determines its accent behavior
COUNTER_CATEGORIES = {
    # Category α - common counters
    "つ": "α",      # generic counter
    "個": "α",      # pieces
    "枚": "α",      # flat objects

    # Category β - 本 group
    "本": "β",      # long objects
    "杯": "β",      # cups/glasses

    # Category γ
    "階": "γ",      # floors
    "軒": "γ",      # buildings

    # Category δ - 年 group (very common)
    "年": "δ",      # years
    "月": "δ",      # months
    "週": "δ",      # weeks

    # Category ε - 回 group
    "回": "ε",      # times/occurrences
    "度": "ε",      # degrees/times

    # Category ζ
    "分": "ζ",      # minutes
    "秒": "ζ",      # seconds

    # Category η - 円 group
    "円": "η",      # yen

    # Category θ
    "歳": "θ",      # age
    "才": "θ",      # age (alt)

    # Category ι
    "時": "ι",      # hours/o'clock
    "時間": "ι",    # hours (duration)

    # Category κ
    "日": "κ",      # days
    "日間": "κ",    # days (duration)

    # Category λ - 人 group
    "人": "λ",      # people
    "名": "λ",      # people (formal)

    # Category μ
    "台": "μ",      # vehicles/machines
    "匹": "μ",      # small animals
    "頭": "μ",      # large animals

    # Category ν
    "番": "ν",      # numbers/order
    "号": "ν",      # issue numbers
}


# Numeral readings (basic forms before counter-conditioned changes)
NUMERAL_READINGS = {
    0: "ゼロ",  # or れい
    1: "いち",
    2: "に",
    3: "さん",
    4: "よん",  # or し
    5: "ご",
    6: "ろく",
    7: "なな",  # or しち
    8: "はち",
    9: "きゅう",  # or く
    10: "じゅう",
    100: "ひゃく",
    1000: "せん",
    10000: "まん",
}

# Accent types for numerals in isolation (before counter)
NUMERAL_ACCENT = {
    1: 2,   # いち [2] LHL
    2: 1,   # に [1] HL
    3: 1,   # さん [1] HL
    4: 1,   # よん [1] HL
    5: 1,   # ご [1] HL
    6: 2,   # ろく [2] LHL
    7: 1,   # なな [1] HLL (or しち [2])
    8: 2,   # はち [2] LHL
    9: 1,   # きゅう [1] HLL
    10: 1,  # じゅう [1] HLL
}


# Override table: (numeral, category) → rule code
# 0 = normal sandhi, 1 = heiban, 2 = counter-initial accent, 3 = counter-final
# This is a simplified version; full table has all 13 categories × numerals 1-10+
NUMERAL_COUNTER_OVERRIDES = {
    # 年 (δ category) - very regular, mostly heiban
    (1, "δ"): 1,   # いちねん → heiban
    (2, "δ"): 1,
    (3, "δ"): 1,
    (4, "δ"): 1,
    (5, "δ"): 1,
    (6, "δ"): 1,
    (7, "δ"): 1,
    (8, "δ"): 1,
    (9, "δ"): 1,
    (10, "δ"): 1,

    # 人 (λ category) - irregular
    (1, "λ"): 0,   # ひとり - special reading
    (2, "λ"): 0,   # ふたり - special reading
    (3, "λ"): 1,   # さんにん heiban
    (4, "λ"): 1,   # よにん heiban
    (5, "λ"): 2,   # ごにん accent on に
    (6, "λ"): 2,
    (7, "λ"): 2,
    (8, "λ"): 2,
    (9, "λ"): 2,
    (10, "λ"): 2,

    # 本 (β category)
    (1, "β"): 2,   # いっぽん accent on ぽ
    (2, "β"): 2,
    (3, "β"): 0,   # さんぼん normal
    (4, "β"): 2,
    (5, "β"): 2,
    (6, "β"): 0,   # ろっぽん
    (7, "β"): 2,
    (8, "β"): 0,
    (9, "β"): 2,
    (10, "β"): 0,

    # 円 (η category) - mostly heiban
    (1, "η"): 1,
    (2, "η"): 1,
    (3, "η"): 1,
    (4, "η"): 1,
    (5, "η"): 1,
    (6, "η"): 1,
    (7, "η"): 1,
    (8, "η"): 1,
    (9, "η"): 1,
    (10, "η"): 1,

    # 回 (ε category)
    (1, "ε"): 2,   # いっかい
    (2, "ε"): 1,
    (3, "ε"): 1,
    (4, "ε"): 1,
    (5, "ε"): 1,
    (6, "ε"): 0,   # ろっかい
    (7, "ε"): 1,
    (8, "ε"): 0,
    (9, "ε"): 1,
    (10, "ε"): 0,

    # 時 (ι category)
    (1, "ι"): 2,
    (2, "ι"): 2,
    (3, "ι"): 2,
    (4, "ι"): 2,   # よじ
    (5, "ι"): 2,
    (6, "ι"): 2,
    (7, "ι"): 2,   # しちじ
    (8, "ι"): 2,
    (9, "ι"): 2,   # くじ
    (10, "ι"): 2,

    # 日 (κ category) - very irregular readings
    (1, "κ"): 0,   # ついたち - special
    (2, "κ"): 0,   # ふつか
    (3, "κ"): 0,   # みっか
    (4, "κ"): 0,   # よっか
    (5, "κ"): 0,   # いつか
    (6, "κ"): 0,   # むいか
    (7, "κ"): 0,   # なのか
    (8, "κ"): 0,   # ようか
    (9, "κ"): 0,   # ここのか
    (10, "κ"): 0,  # とおか
}


# Phonological alternations at numeral-counter boundary
# (numeral, counter_initial) → (numeral_final_change, counter_initial_change)
READING_ALTERNATIONS = {
    # っ insertion (促音化)
    (1, "本"): ("いっ", "ぽん"),
    (1, "杯"): ("いっ", "ぱい"),
    (1, "回"): ("いっ", "かい"),
    (1, "階"): ("いっ", "かい"),
    (6, "本"): ("ろっ", "ぽん"),
    (6, "杯"): ("ろっ", "ぱい"),
    (6, "回"): ("ろっ", "かい"),
    (8, "本"): ("はっ", "ぽん"),
    (8, "杯"): ("はっ", "ぱい"),
    (8, "回"): ("はっ", "かい"),
    (10, "本"): ("じゅっ", "ぽん"),  # or じっぽん
    (10, "杯"): ("じゅっ", "ぱい"),
    (10, "回"): ("じっ", "かい"),

    # 濁音化 for 本
    (3, "本"): ("さん", "ぼん"),

    # Special readings for 人
    (1, "人"): ("ひと", "り"),
    (2, "人"): ("ふた", "り"),
    (4, "人"): ("よ", "にん"),

    # Special readings for 日 (dates)
    (1, "日"): ("つい", "たち"),
    (2, "日"): ("ふつ", "か"),
    (3, "日"): ("みっ", "か"),
    (4, "日"): ("よっ", "か"),
    (5, "日"): ("いつ", "か"),
    (6, "日"): ("むい", "か"),
    (7, "日"): ("なの", "か"),
    (8, "日"): ("よう", "か"),
    (9, "日"): ("ここの", "か"),
    (10, "日"): ("とお", "か"),
    (14, "日"): ("じゅうよっ", "か"),
    (20, "日"): ("はつ", "か"),
    (24, "日"): ("にじゅうよっ", "か"),

    # Special readings for 時
    (4, "時"): ("よ", "じ"),
    (7, "時"): ("しち", "じ"),
    (9, "時"): ("く", "じ"),
}


def count_mora(reading: str) -> int:
    """Count mora in a reading."""
    SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")
    count = 0
    for char in reading:
        if char not in SMALL_KANA:
            count += 1
    return count


def get_counter_category(counter: str) -> Optional[str]:
    """Get the category for a counter."""
    return COUNTER_CATEGORIES.get(counter)


def get_numeral_counter_reading(numeral: int, counter: str) -> tuple[str, str]:
    """
    Get the reading for a numeral+counter combination,
    applying phonological alternations.

    Returns (numeral_reading, counter_reading)
    """
    # Check for special reading
    if (numeral, counter) in READING_ALTERNATIONS:
        return READING_ALTERNATIONS[(numeral, counter)]

    # Default readings
    num_reading = NUMERAL_READINGS.get(numeral, str(numeral))

    # Counter reading (simplified - would need dictionary lookup for accuracy)
    counter_readings = {
        "年": "ねん",
        "月": "がつ",
        "日": "にち",
        "時": "じ",
        "分": "ふん",
        "秒": "びょう",
        "人": "にん",
        "本": "ほん",
        "回": "かい",
        "円": "えん",
        "歳": "さい",
        "個": "こ",
        "枚": "まい",
        "台": "だい",
        "階": "かい",
        "番": "ばん",
    }
    counter_reading = counter_readings.get(counter, counter)

    return (num_reading, counter_reading)


def compute_numeral_phrase_accent(
    numeral: int,
    counter: str,
    counter_accent: int = 0,
) -> tuple[int, str, str]:
    """
    Compute accent for a numeral+counter phrase.

    Args:
        numeral: The number (1-10, etc.)
        counter: The counter surface form
        counter_accent: Accent type of counter in isolation

    Returns:
        (accent_type, reading, rule_description)
    """
    category = get_counter_category(counter)
    num_reading, counter_reading = get_numeral_counter_reading(numeral, counter)

    full_reading = num_reading + counter_reading
    total_mora = count_mora(full_reading)
    num_mora = count_mora(num_reading)
    counter_mora = count_mora(counter_reading)

    # Look up override rule
    override = NUMERAL_COUNTER_OVERRIDES.get((numeral, category))

    if override is None:
        # No override - use default (often heiban for large numbers)
        if numeral > 10:
            return (0, full_reading, "large_number_default_heiban")
        override = 0  # Fall back to normal

    if override == 0:
        # Normal sandhi - treat like compound noun
        # Simplified: accent on numeral's position or boundary
        if counter_mora <= 2:
            accent = num_mora
        else:
            accent = num_mora + 1
        return (accent, full_reading, f"normal_sandhi_cat_{category}")

    elif override == 1:
        # Force heiban
        return (0, full_reading, f"heiban_cat_{category}")

    elif override == 2:
        # Accent on first mora of counter
        accent = num_mora + 1
        return (accent, full_reading, f"counter_initial_cat_{category}")

    elif override == 3:
        # Accent on last mora of counter
        accent = total_mora
        return (accent, full_reading, f"counter_final_cat_{category}")

    return (0, full_reading, "unknown")


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
    ) -> dict:
        """
        Process a numeral + counter combination.

        Args:
            numeral_morphemes: List of morphemes making up the number
            counter_morpheme: The counter morpheme

        Returns:
            Merged morpheme dict with computed accent
        """
        # Extract numeral value (simplified - assumes single digit or small number)
        # A full implementation would parse complex numbers like 1952
        numeral_surface = "".join(m.get("surface", "") for m in numeral_morphemes)

        # Try to extract numeric value
        try:
            # Handle Arabic numerals
            numeral = int("".join(c for c in numeral_surface if c.isdigit()))
        except ValueError:
            numeral = 0

        counter = counter_morpheme.get("surface", "")
        counter_accent_str = counter_morpheme.get("aType", "0")
        counter_accent = int(counter_accent_str.split(",")[0]) if counter_accent_str and counter_accent_str != "*" else 0

        accent, reading, rule = compute_numeral_phrase_accent(numeral, counter, counter_accent)

        # Build merged morpheme
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
            "_numeral": numeral,
            "_counter": counter,
        }


def main():
    """Test numeral accent computation."""
    print("=" * 70)
    print("NUMERAL PHRASE ACCENT TEST")
    print("=" * 70)

    test_cases = [
        (1, "年"),
        (2024, "年"),
        (1952, "年"),
        (1, "人"),
        (2, "人"),
        (3, "人"),
        (6, "万"),  # For 6万人
        (1, "本"),
        (3, "本"),
        (6, "本"),
        (10, "本"),
        (1, "回"),
        (5, "時"),
        (1, "日"),
        (10, "日"),
        (20, "日"),
        (100, "円"),
    ]

    for numeral, counter in test_cases:
        accent, reading, rule = compute_numeral_phrase_accent(numeral, counter)
        mora = count_mora(reading)

        print(f"\n{numeral}{counter}:")
        print(f"  Reading: {reading}")
        print(f"  Accent: [{accent}] / {mora}拍")
        print(f"  Rule: {rule}")


if __name__ == "__main__":
    main()

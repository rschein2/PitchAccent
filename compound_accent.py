#!/usr/bin/env python3
"""
Compound Noun Accent Sandhi for Tokyo Japanese

Implements the length-driven compound accent rules from TUFS/Kubozono tradition.
When two nouns form a tight compound, the result has ONE accent nucleus,
determined by the mora length of N2 and its accent type.

References:
- TUFS: https://www.coelang.tufs.ac.jp/mt/ja/pmod/practical/02-07-01.php
- Kubozono compound accent research
"""
from dataclasses import dataclass
from typing import Optional


# Special mora (特殊拍) - don't place accent nucleus on these
SPECIAL_MORA = set("んっー")

# Long vowel pairs - second element counts as special
LONG_VOWEL_PAIRS = {
    "aa": "ああ", "ii": "いい", "uu": "うう", "ee": "ええ", "oo": "おお",
    "ou": "おう", "ei": "えい",
}


@dataclass
class CompoundResult:
    """Result of compound accent computation."""
    surface: str
    reading: str
    accent_type: int
    mora_count: int
    components: list[str]  # Original component words
    rule_applied: str      # Which rule was used


def count_mora(reading: str) -> int:
    """Count mora in a reading, treating small kana as part of previous mora."""
    SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")
    count = 0
    for char in reading:
        if char not in SMALL_KANA:
            count += 1
    return count


def ends_with_special_mora(reading: str) -> bool:
    """Check if reading ends with a special mora (ん, っ, ー, or long vowel)."""
    if not reading:
        return False

    last_char = reading[-1]
    if last_char in SPECIAL_MORA:
        return True

    # Check for long vowel (e.g., おう, えい at end)
    if len(reading) >= 2:
        last_two = reading[-2:]
        # Common long vowel patterns
        if last_two in ("おう", "うう", "おお", "えい", "いい", "ああ"):
            return True

    return False


def get_special_mora_at_end_count(reading: str) -> int:
    """Count how many special mora are at the end (for shifting accent left)."""
    count = 0
    for char in reversed(reading):
        if char in SPECIAL_MORA:
            count += 1
        else:
            break
    return count


# Suffixes that tend to make compounds heiban (平板化接尾辞)
HEIBAN_SUFFIXES = {
    "語",    # ～語 (language)
    "色",    # ～色 (color)
    "的",    # ～的 (adjectival)
    "性",    # ～性 (nature/quality)
    "化",    # ～化 (transformation)
    "家",    # ～家 (expert/house)
    "者",    # ～者 (person)
    "員",    # ～員 (member)
    "式",    # ～式 (style/ceremony)
    "用",    # ～用 (for use)
    "中",    # ～中 (during/in)
    "内",    # ～内 (within)
    "外",    # ～外 (outside)
    "上",    # ～上 (on/above, abstract)
    "下",    # ～下 (under, abstract)
    "間",    # ～間 (between/during)
    "前",    # ～前 (before)
    "後",    # ～後 (after)
    "代",    # ～代 (generation/cost)
    "感",    # ～感 (feeling)
}


def compute_compound_accent(
    n1_reading: str,
    n1_accent: int,
    n2_reading: str,
    n2_accent: int,
    n2_surface: str = "",
) -> tuple[int, str]:
    """
    Compute accent type for a 2-noun compound using Tokyo length-driven rules.

    Args:
        n1_reading: Hiragana reading of N1
        n1_accent: Accent type of N1 in isolation
        n2_reading: Hiragana reading of N2
        n2_accent: Accent type of N2 in isolation
        n2_surface: Surface form of N2 (for checking heiban suffixes)

    Returns:
        (accent_type, rule_name) tuple
    """
    n1_len = count_mora(n1_reading)
    n2_len = count_mora(n2_reading)
    total_len = n1_len + n2_len

    # Check for heiban-inducing suffixes
    if n2_surface in HEIBAN_SUFFIXES:
        return (0, "heiban_suffix")

    # Case A: N2 is 1-2 mora
    if n2_len <= 2:
        # Accent on last mora of N1
        accent_pos = n1_len

        # If N1 ends with special mora, shift left
        if ends_with_special_mora(n1_reading):
            shift = get_special_mora_at_end_count(n1_reading)
            accent_pos = max(1, n1_len - shift)
            return (accent_pos, f"N2≤2_special_shift_{shift}")

        return (accent_pos, "N2≤2_boundary")

    # Case B: N2 is 3-4 mora
    if 3 <= n2_len <= 4:
        # If N2 is heiban (0) or odaka (accent on last mora)
        is_heiban = (n2_accent == 0)
        is_odaka = (n2_accent == n2_len)

        if is_heiban or is_odaka:
            # Accent on first mora of N2
            return (n1_len + 1, "N2=3-4_heiban/odaka→N2_initial")
        else:
            # Preserve N2's accent position
            return (n1_len + n2_accent, "N2=3-4_preserve_N2")

    # Case C: N2 is 5+ mora
    if n2_accent == 0:
        # N2 heiban → compound heiban
        return (0, "N2≥5_heiban→compound_heiban")
    else:
        # Preserve N2's accent
        return (n1_len + n2_accent, "N2≥5_preserve_N2")


def compute_multi_noun_compound(
    components: list[tuple[str, str, int]]  # [(surface, reading, accent), ...]
) -> tuple[int, str, list[str]]:
    """
    Compute accent for 3+ noun compound using binary left-branching.
    ((N1 + N2) + N3) + N4 ...

    Args:
        components: List of (surface, reading, accent_type) tuples

    Returns:
        (final_accent, final_reading, rules_applied)
    """
    if not components:
        return (0, "", [])

    if len(components) == 1:
        return (components[0][2], components[0][1], ["single_noun"])

    rules = []

    # Start with first two
    surface1, reading1, accent1 = components[0]
    surface2, reading2, accent2 = components[1]

    current_accent, rule = compute_compound_accent(
        reading1, accent1, reading2, accent2, surface2
    )
    current_reading = reading1 + reading2
    rules.append(f"{surface1}+{surface2}: {rule}")

    # Add remaining components one by one
    for i in range(2, len(components)):
        surface_n, reading_n, accent_n = components[i]

        current_accent, rule = compute_compound_accent(
            current_reading, current_accent, reading_n, accent_n, surface_n
        )
        current_reading = current_reading + reading_n
        rules.append(f"+{surface_n}: {rule}")

    return (current_accent, current_reading, rules)


class CompoundAccentEngine:
    """
    Engine for computing compound noun accent.

    Integrates with the existing accent engine by providing a pre-processing
    step that merges noun sequences and computes their combined accent.
    """

    def __init__(self):
        pass

    def process_noun_sequence(
        self,
        nouns: list[dict]  # Morpheme dicts with surface, reading, aType, etc.
    ) -> dict:
        """
        Process a sequence of noun morphemes and return a merged morpheme
        with computed compound accent.

        Args:
            nouns: List of morpheme dicts from the parser

        Returns:
            Single morpheme dict representing the compound
        """
        if not nouns:
            return {}

        if len(nouns) == 1:
            return nouns[0]

        # Extract components
        components = []
        for m in nouns:
            surface = m.get("surface", "")
            reading = m.get("reading", surface)
            # Convert katakana to hiragana
            reading = self._kata_to_hira(reading)

            # Parse aType (may be "1,0" format)
            atype_str = m.get("aType", "0")
            if atype_str and atype_str != "*":
                atype = int(atype_str.split(",")[0])
            else:
                atype = 0

            components.append((surface, reading, atype))

        # Compute compound accent
        final_accent, final_reading, rules = compute_multi_noun_compound(components)

        # Build merged morpheme
        merged_surface = "".join(m.get("surface", "") for m in nouns)
        merged_reading_kata = "".join(m.get("reading", m.get("surface", "")) for m in nouns)

        return {
            "surface": merged_surface,
            "reading": merged_reading_kata,
            "pos1": "名詞",
            "pos2": "複合",
            "aType": str(final_accent),
            "aConType": "*",
            "aModType": "*",
            "cType": "*",
            "cForm": "*",
            "lemma": merged_surface,
            "_compound_rules": rules,
            "_components": [m.get("surface", "") for m in nouns],
        }

    def _kata_to_hira(self, text: str) -> str:
        """Convert katakana to hiragana."""
        result = []
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)


def main():
    """Test compound accent computation."""
    print("=" * 70)
    print("COMPOUND NOUN ACCENT TEST")
    print("=" * 70)

    # Test cases: (n1_surface, n1_reading, n1_accent, n2_surface, n2_reading, n2_accent)
    test_cases = [
        # N2 ≤ 2 mora
        ("安全", "あんぜん", 0, "面", "めん", 0),  # 安全面
        ("保障", "ほしょう", 0, "面", "めん", 0),  # 保障面
        ("日本", "にほん", 2, "語", "ご", 1),      # 日本語 (heiban suffix)
        ("経済", "けいざい", 1, "学", "がく", 0),  # 経済学

        # N2 = 3-4 mora
        ("安全", "あんぜん", 0, "保障", "ほしょう", 0),  # 安全保障
        ("日米", "にちべい", 1, "関係", "かんけい", 0),  # 日米関係
        ("太平", "たいへい", 0, "洋", "よう", 0),        # 太平洋

        # N2 ≥ 5 mora
        ("日米", "にちべい", 1, "安全保障", "あんぜんほしょう", 0),
    ]

    for n1_surf, n1_read, n1_acc, n2_surf, n2_read, n2_acc in test_cases:
        accent, rule = compute_compound_accent(n1_read, n1_acc, n2_read, n2_acc, n2_surf)
        combined = n1_read + n2_read
        total_mora = count_mora(combined)

        print(f"\n{n1_surf}+{n2_surf} ({n1_read}+{n2_read})")
        print(f"  N1: {count_mora(n1_read)}拍 [{n1_acc}], N2: {count_mora(n2_read)}拍 [{n2_acc}]")
        print(f"  → Compound: {total_mora}拍 [{accent}]")
        print(f"  Rule: {rule}")

    # Test multi-noun
    print("\n" + "=" * 70)
    print("MULTI-NOUN COMPOUND TEST")
    print("=" * 70)

    # 安全保障面
    components = [
        ("安全", "あんぜん", 0),
        ("保障", "ほしょう", 0),
        ("面", "めん", 0),
    ]
    accent, reading, rules = compute_multi_noun_compound(components)
    print(f"\n安全保障面:")
    print(f"  Final accent: [{accent}] on {count_mora(reading)} mora")
    for r in rules:
        print(f"  {r}")

    # 日本国内
    components = [
        ("日本", "にほん", 2),
        ("国内", "こくない", 1),
    ]
    accent, reading, rules = compute_multi_noun_compound(components)
    print(f"\n日本国内:")
    print(f"  Final accent: [{accent}] on {count_mora(reading)} mora")
    for r in rules:
        print(f"  {r}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Lightweight pitch accent utilities.

These functions don't require UniDic or any heavy dependencies.
Used by the minimal pairs view and other places that just need
pattern computation without full text parsing.
"""

# Small kana that don't count as separate mora (except っ/ッ which do count)
SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")
SOKUON = set("っッ")


def count_mora(reading: str) -> int:
    """Count mora in a reading."""
    count = 0
    for char in reading:
        if char in SMALL_KANA and char not in SOKUON:
            continue
        count += 1
    return count


def accent_to_pattern(accent_type: int, mora_count: int,
                      include_particle: bool = True) -> str:
    """
    Convert accent type to L/H pattern.

    Args:
        accent_type: 0=heiban, k=drop after k-th mora
        mora_count: number of mora in the word
        include_particle: if True, add extra mora to show pitch on particle

    Rules:
    - First mora is L (low) except for 頭高 (type 1)
    - After accent position, pitch drops to L and stays L
    - Type 0 (heiban): LHHH...H (stays high, including particle)
    """
    if mora_count == 0:
        return ""

    total = mora_count + (1 if include_particle else 0)

    if mora_count == 1 and not include_particle:
        return "H" if accent_type == 1 else "L"

    if accent_type == 0:
        # Heiban: LHHH...H (stays high through particle)
        return "L" + "H" * (total - 1)
    elif accent_type == 1:
        # Atamadaka: HLLL...L (drops after first)
        return "H" + "L" * (total - 1)
    else:
        # Nakadaka/Odaka: LHHH...HL...L
        if accent_type > total:
            return "L" + "H" * (total - 1)
        else:
            high_count = accent_type - 1
            low_count = total - accent_type
            return "L" + "H" * high_count + "L" * low_count


def pattern_to_contour(reading: str, pattern: str) -> str:
    """
    Convert reading + L/H pattern to pitch contour notation.

    Uses / for rising pitch and \\ for falling pitch between morae.

    Examples:
        たべる + LHLL → た/べ\\る
        みる + HLL → み\\る
        いく + LHH → い/く (heiban - no fall within word)
    """
    if not reading or not pattern:
        return reading

    # Split reading into morae
    morae = []
    i = 0
    small_kana = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")

    while i < len(reading):
        mora = reading[i]
        if i + 1 < len(reading) and reading[i + 1] in small_kana:
            mora += reading[i + 1]
            i += 1
        morae.append(mora)
        i += 1

    # Build contour string
    result = []
    use_len = min(len(morae), len(pattern))

    for i in range(use_len):
        result.append(morae[i])

        if i < use_len - 1 and i + 1 < len(pattern):
            curr = pattern[i]
            next_p = pattern[i + 1]
            if curr == "L" and next_p == "H":
                result.append("/")
            elif curr == "H" and next_p == "L":
                result.append("\\")

    return "".join(result)

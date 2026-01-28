#!/usr/bin/env python3
"""
Arabic Numeral to Japanese Reading Converter

Simplified version - handles standard readings without rendaku complexity.
For study purposes, close enough is good enough.
"""

# Basic digit readings
DIGITS = {
    0: "",      # zero usually omitted in compounds
    1: "いち",
    2: "に",
    3: "さん",
    4: "よん",
    5: "ご",
    6: "ろく",
    7: "なな",
    8: "はち",
    9: "きゅう",
}

# Place value readings
PLACES = {
    1: "",           # ones - no suffix
    10: "じゅう",
    100: "ひゃく",
    1000: "せん",
    10000: "まん",
    100000000: "おく",  # 億
    1000000000000: "ちょう",  # 兆
}


def number_to_reading(n: int) -> str:
    """
    Convert an integer to Japanese reading.

    Simplified: ignores most rendaku (さんびゃく → さんひゃく).
    Good enough for study materials.

    Examples:
        1952 → せんきゅうひゃくごじゅうに
        2024 → にせんにじゅうよん
        6 → ろく
        60000 → ろくまん
    """
    if n == 0:
        return "ゼロ"

    if n < 0:
        return "マイナス" + number_to_reading(-n)

    result = []

    # Handle 兆 (trillion)
    if n >= 1000000000000:
        cho = n // 1000000000000
        if cho > 1:
            result.append(number_to_reading(cho))
        result.append("ちょう")
        n %= 1000000000000

    # Handle 億 (hundred million)
    if n >= 100000000:
        oku = n // 100000000
        if oku > 1:
            result.append(number_to_reading(oku))
        result.append("おく")
        n %= 100000000

    # Handle 万 (ten thousand)
    if n >= 10000:
        man = n // 10000
        if man > 1:
            result.append(number_to_reading(man))
        result.append("まん")
        n %= 10000

    # Handle 千 (thousand)
    if n >= 1000:
        sen = n // 1000
        if sen > 1:
            result.append(DIGITS[sen])
        result.append("せん")
        n %= 1000

    # Handle 百 (hundred)
    if n >= 100:
        hyaku = n // 100
        if hyaku > 1:
            result.append(DIGITS[hyaku])
        result.append("ひゃく")
        n %= 100

    # Handle 十 (ten)
    if n >= 10:
        juu = n // 10
        if juu > 1:
            result.append(DIGITS[juu])
        result.append("じゅう")
        n %= 10

    # Handle ones
    if n > 0:
        result.append(DIGITS[n])

    return "".join(result)


def extract_number(text: str) -> tuple[int | None, str]:
    """
    Extract leading number from text.

    Returns (number, remainder) or (None, text) if no number found.
    """
    digits = []
    i = 0
    for char in text:
        if char.isdigit():
            digits.append(char)
            i += 1
        else:
            break

    if digits:
        return int("".join(digits)), text[i:]
    return None, text


def convert_numerals_in_text(text: str) -> str:
    """
    Convert all Arabic numerals in text to hiragana readings.

    "1952年" → "せんきゅうひゃくごじゅうにねん"
    """
    result = []
    i = 0

    while i < len(text):
        if text[i].isdigit():
            # Extract the full number
            num, remainder = extract_number(text[i:])
            if num is not None:
                result.append(number_to_reading(num))
                i += len(str(num))
            else:
                result.append(text[i])
                i += 1
        else:
            result.append(text[i])
            i += 1

    return "".join(result)


def main():
    """Test numeral conversion."""
    test_numbers = [
        0, 1, 5, 10, 11, 15, 20, 21, 99,
        100, 101, 110, 111, 200, 300, 456,
        1000, 1001, 1952, 2024, 9999,
        10000, 12345, 60000,
        100000, 1000000,
        100000000,  # 1億
    ]

    print("=" * 50)
    print("NUMERAL CONVERSION TEST")
    print("=" * 50)

    for n in test_numbers:
        reading = number_to_reading(n)
        print(f"{n:>12} → {reading}")

    print("\n" + "=" * 50)
    print("TEXT CONVERSION TEST")
    print("=" * 50)

    test_texts = [
        "1952年",
        "2024年",
        "約6万人",
        "100円",
        "3本",
    ]

    for text in test_texts:
        converted = convert_numerals_in_text(text)
        print(f"{text} → {converted}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Build a minimal pairs database from UniDic.

Finds words with identical readings but different pitch accent patterns.
This is original derived work - we're computing pairs from the dictionary data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fugashi
import unidic
from collections import defaultdict
import json

def build_minimal_pairs():
    """
    Scan UniDic dictionary and find minimal pairs.

    A minimal pair is two words with:
    - Same reading (pronunciation)
    - Different accent type
    - Different meaning (different kanji/lemma)
    """
    tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

    # We'll build pairs by analyzing common words
    # UniDic doesn't expose full dictionary, so we use a word list approach

    # Common words to check - expand this list as needed
    test_words = []

    # Generate test words from common kanji
    common_kanji = "日月火水木金土人口目手足心体頭顔声音色形名前後上下中外内大小高低長短新古"
    for k in common_kanji:
        test_words.append(k)

    # Add common words that are known to have homophone pairs
    known_homophones = [
        # あめ
        "雨", "飴",
        # はし
        "橋", "箸", "端",
        # かき
        "柿", "牡蠣", "垣",
        # さけ
        "酒", "鮭",
        # かみ
        "神", "紙", "髪",
        # はな
        "花", "鼻",
        # あさ
        "朝", "麻",
        # いし
        "石", "医師", "意志",
        # かわ
        "川", "皮", "革",
        # くも
        "雲", "蜘蛛",
        # にわ
        "庭", "二羽",
        # せき
        "席", "咳", "石",
        # しろ
        "白", "城",
        # あき
        "秋", "空き",
        # かた
        "肩", "型", "方",
        # ひ
        "日", "火", "陽",
        # め
        "目", "芽",
        # き
        "木", "気", "黄",
        # は
        "歯", "葉", "刃",
    ]
    test_words.extend(known_homophones)

    # Parse each word and collect by reading
    reading_to_words = defaultdict(list)

    for word in test_words:
        try:
            nodes = list(tagger(word))
            if not nodes:
                continue

            node = nodes[0]
            f = node.feature

            reading = getattr(f, 'kana', None)
            atype = getattr(f, 'aType', '*')
            lemma = getattr(f, 'lemma', word)

            if reading and atype and atype != '*':
                # Handle multiple accent options (take first)
                accent = atype.split(',')[0]

                reading_to_words[reading].append({
                    'surface': word,
                    'lemma': lemma,
                    'accent': int(accent) if accent.lstrip('-').isdigit() else 0,
                    'reading': reading,
                })
        except Exception as e:
            continue

    # Find pairs with same reading but different accent
    minimal_pairs = []

    for reading, words in reading_to_words.items():
        if len(words) < 2:
            continue

        # Group by accent type
        by_accent = defaultdict(list)
        for w in words:
            by_accent[w['accent']].append(w)

        # If there are multiple accent types, we have minimal pairs
        if len(by_accent) >= 2:
            accents = sorted(by_accent.keys())

            # Create pairs between different accent groups
            for i, acc1 in enumerate(accents):
                for acc2 in accents[i+1:]:
                    for w1 in by_accent[acc1]:
                        for w2 in by_accent[acc2]:
                            # Skip if same lemma
                            if w1['lemma'] == w2['lemma']:
                                continue

                            minimal_pairs.append({
                                'reading': reading,
                                'word1': {
                                    'surface': w1['surface'],
                                    'accent': w1['accent'],
                                },
                                'word2': {
                                    'surface': w2['surface'],
                                    'accent': w2['accent'],
                                },
                            })

    return minimal_pairs


def accent_to_pattern(accent: int, mora_count: int) -> str:
    """Convert accent type to L/H pattern."""
    if mora_count == 0:
        return ""

    total = mora_count + 1  # Include particle position

    if accent == 0:
        return "L" + "H" * (total - 1)
    elif accent == 1:
        return "H" + "L" * (total - 1)
    else:
        if accent > total:
            return "L" + "H" * (total - 1)
        else:
            return "L" + "H" * (accent - 1) + "L" * (total - accent)


def count_mora(reading: str) -> int:
    """Count mora in reading."""
    SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")
    return sum(1 for c in reading if c not in SMALL_KANA)


def main():
    print("Building minimal pairs from UniDic...")
    pairs = build_minimal_pairs()

    print(f"\nFound {len(pairs)} minimal pairs:\n")
    print("=" * 60)

    # Sort by reading for nice output
    pairs.sort(key=lambda p: p['reading'])

    seen = set()
    for pair in pairs:
        # Deduplicate
        key = tuple(sorted([pair['word1']['surface'], pair['word2']['surface']]))
        if key in seen:
            continue
        seen.add(key)

        reading = pair['reading']
        w1 = pair['word1']
        w2 = pair['word2']

        mora = count_mora(reading)
        p1 = accent_to_pattern(w1['accent'], mora)
        p2 = accent_to_pattern(w2['accent'], mora)

        print(f"{reading}:")
        print(f"  {w1['surface']} [{w1['accent']}] {p1}")
        print(f"  {w2['surface']} [{w2['accent']}] {p2}")
        print()

    # Save to JSON
    output_file = Path(__file__).parent.parent / "pitch_accent" / "minimal_pairs.json"

    # Deduplicate for JSON output
    unique_pairs = []
    seen = set()
    for pair in pairs:
        key = tuple(sorted([pair['word1']['surface'], pair['word2']['surface']]))
        if key not in seen:
            seen.add(key)
            unique_pairs.append(pair)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_pairs, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(unique_pairs)} pairs to {output_file}")


if __name__ == "__main__":
    main()

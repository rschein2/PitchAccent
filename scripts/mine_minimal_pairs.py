#!/usr/bin/env python3
"""
Mine Minimal Pairs from UniDic

Finds words with the same reading but different pitch accents.
These are valuable for learners to distinguish meanings by accent alone.

Examples:
- 雨[1] vs 飴[0] (あめ - rain vs candy)
- 橋[2] vs 箸[1] vs 端[0] (はし - bridge vs chopsticks vs edge)
- 酒[0] vs 鮭[1] (さけ - sake vs salmon)
"""
import json
import fugashi
import unidic
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional
import sys

# Common words to check - we'll expand this
# These are words known to have homophones with different accents
SEED_WORDS = [
    # Classic minimal pairs
    "雨", "飴",  # あめ
    "橋", "箸", "端",  # はし
    "牡蠣", "柿", "下記",  # かき
    "酒", "鮭",  # さけ
    "雲", "蜘蛛",  # くも
    "花", "鼻",  # はな
    "日", "火", "灯",  # ひ
    "神", "髪", "紙", "上",  # かみ
    "今", "居間",  # いま
    "蚊", "日", "課",  # か
    "木", "気", "記",  # き
    "戸", "都", "途",  # と
    "夜", "世", "代",  # よ

    # Common verbs that can be confusing
    "切る", "着る",  # きる
    "要る", "入る", "煎る",  # いる
    "帰る", "返る", "変える",  # かえる
    "掛ける", "欠ける", "駆ける",  # かける

    # Nouns with accent variations
    "朝", "麻",  # あさ
    "足", "脚",  # あし
    "青", "藍",  # あお
    "赤", "垢",  # あか
    "声", "越え",  # こえ
    "腰", "越し",  # こし
    "型", "方", "肩",  # かた
    "数", "和図",  # かず
    "鉛", "なまり",  # なまり

    # Location/direction words
    "東", "吾妻",  # あずま
    "北", "来た",  # きた
    "西", "虹",  # にし... wait, these aren't same reading

    # Time words
    "今日", "京",  # きょう
    "明日", "飛鳥",  # あす/あすか

    # Body parts with homophones
    "目", "芽", "女",  # め
    "歯", "葉", "刃",  # は
    "耳", "実",  # みみ/み

    # Common adjectives/adverbs
    "高い", "高",  # たかい/たか
    "甘い", "雨",  # あまい/あめ

    # Add many more common words for thoroughness
    "学校", "学生", "先生", "日本", "東京", "大阪",
    "食べる", "飲む", "行く", "来る", "見る", "聞く",
    "大きい", "小さい", "新しい", "古い", "良い", "悪い",
    "人", "男", "女", "子供", "友達", "家族",
    "水", "山", "川", "海", "空", "雨",
    "本", "車", "電車", "駅", "道", "店",
]

# Additional reading-based seeds (we know these readings have pairs)
READING_SEEDS = [
    "あめ", "はし", "かき", "さけ", "くも", "はな",
    "かみ", "いま", "きる", "いる", "かえる", "かける",
    "あさ", "あし", "こえ", "かた", "かず", "きた",
    "きょう", "あす", "め", "は", "み",
]


@dataclass
class WordEntry:
    surface: str      # 書字形 (漢字表記)
    reading: str      # 読み (ひらがな)
    accent: int       # アクセント型
    pos: str          # 品詞
    meaning: str = "" # 意味（後で追加可能）


@dataclass
class MinimalPair:
    reading: str
    words: list[WordEntry]
    mora_count: int

    def to_dict(self):
        return {
            "reading": self.reading,
            "mora_count": self.mora_count,
            "words": [asdict(w) for w in self.words]
        }


class MinimalPairMiner:
    """Mine minimal pairs from UniDic."""

    SMALL_KANA = set("ぁぃぅぇぉゃゅょゎっ")

    def __init__(self):
        self.tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')
        self.words_by_reading: dict[str, list[WordEntry]] = defaultdict(list)

    def count_mora(self, reading: str) -> int:
        """Count mora in a reading."""
        count = 0
        for char in reading:
            if char not in self.SMALL_KANA:
                count += 1
        return count

    def kata_to_hira(self, text: str) -> str:
        """Convert katakana to hiragana."""
        result = []
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)

    def parse_word(self, word: str) -> Optional[WordEntry]:
        """Parse a word and extract accent information."""
        nodes = list(self.tagger(word))
        if not nodes:
            return None

        # Get the first content word
        for node in nodes:
            f = node.feature
            pos = f.pos1 if hasattr(f, 'pos1') else ""

            # Skip particles and punctuation
            if pos in ("助詞", "助動詞", "補助記号", "空白"):
                continue

            # Get reading
            reading = self.kata_to_hira(f.kana) if hasattr(f, 'kana') and f.kana else ""
            if not reading:
                continue

            # Get accent
            atype = f.aType if hasattr(f, 'aType') else "*"
            if atype and atype != "*":
                # Handle multiple accent options (take first)
                accent = int(atype.split(",")[0])
            else:
                accent = 0

            return WordEntry(
                surface=node.surface,
                reading=reading,
                accent=accent,
                pos=pos
            )

        return None

    def add_word(self, word: str) -> Optional[WordEntry]:
        """Add a word to the database."""
        entry = self.parse_word(word)
        if entry:
            # Check if we already have this exact entry
            existing = self.words_by_reading[entry.reading]
            for e in existing:
                if e.surface == entry.surface and e.accent == entry.accent:
                    return entry  # Already exists
            self.words_by_reading[entry.reading].append(entry)
        return entry

    def add_words(self, words: list[str]) -> int:
        """Add multiple words, return count of successfully added."""
        count = 0
        for word in words:
            if self.add_word(word):
                count += 1
        return count

    def find_minimal_pairs(self) -> list[MinimalPair]:
        """Find all minimal pairs (same reading, different accent)."""
        pairs = []

        for reading, entries in self.words_by_reading.items():
            if len(entries) < 2:
                continue

            # Check if there are different accents
            accents = set(e.accent for e in entries)
            if len(accents) < 2:
                continue

            # Sort by accent for consistent ordering
            sorted_entries = sorted(entries, key=lambda e: (e.accent, e.surface))

            pairs.append(MinimalPair(
                reading=reading,
                words=sorted_entries,
                mora_count=self.count_mora(reading)
            ))

        # Sort by mora count, then reading
        pairs.sort(key=lambda p: (p.mora_count, p.reading))
        return pairs

    def find_pairs_for_reading(self, reading: str) -> Optional[MinimalPair]:
        """Find minimal pair for a specific reading."""
        reading = self.kata_to_hira(reading)
        entries = self.words_by_reading.get(reading, [])

        if len(entries) < 2:
            return None

        accents = set(e.accent for e in entries)
        if len(accents) < 2:
            return None

        sorted_entries = sorted(entries, key=lambda e: (e.accent, e.surface))
        return MinimalPair(
            reading=reading,
            words=sorted_entries,
            mora_count=self.count_mora(reading)
        )


def mine_from_seeds():
    """Mine minimal pairs from seed words."""
    miner = MinimalPairMiner()

    print("Mining minimal pairs from seed words...")
    count = miner.add_words(SEED_WORDS)
    print(f"Added {count} words from seed list")

    pairs = miner.find_minimal_pairs()
    print(f"Found {len(pairs)} minimal pairs")

    return pairs


def main():
    pairs = mine_from_seeds()

    print("\n" + "="*60)
    print("MINIMAL PAIRS FOUND")
    print("="*60)

    for pair in pairs:
        words_str = ", ".join(
            f"{w.surface}[{w.accent}]" for w in pair.words
        )
        print(f"\n{pair.reading} ({pair.mora_count}拍):")
        print(f"  {words_str}")

    # Save to JSON
    output = {
        "pairs": [p.to_dict() for p in pairs],
        "count": len(pairs)
    }

    output_path = "data/minimal_pairs.json"
    import os
    os.makedirs("data", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(pairs)} pairs to {output_path}")


if __name__ == "__main__":
    main()

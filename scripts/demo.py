#!/usr/bin/env python3
"""
Demo of the Japanese Pitch Accent Engine.
Shows computed patterns for various verb conjugations.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pitch_accent.engine import FugashiAccentEngine


def visualize_pattern(pattern: str, reading: str) -> str:
    """Create a visual representation of pitch pattern."""
    if not pattern or not reading:
        return ""

    # Simple ASCII visualization
    lines = []
    high = "▔"
    low = "▁"

    # Match pattern to reading characters
    top = ""
    for i, p in enumerate(pattern):
        char = reading[i] if i < len(reading) else "•"
        top += high if p == "H" else low

    return top


def main():
    engine = FugashiAccentEngine()

    print("=" * 70)
    print("JAPANESE PITCH ACCENT ENGINE - DEMO")
    print("=" * 70)
    print()
    print("Legend: ▔ = High pitch, ▁ = Low pitch")
    print("        Pattern includes following particle position")
    print()

    # Group verbs by accent type
    verb_groups = [
        ("Ichidan 2型 (中高)", "食べる", ["食べる", "食べた", "食べて", "食べない", "食べます", "食べたい"]),
        ("Ichidan 1型 (頭高)", "見る", ["見る", "見た", "見て", "見ない", "見ます"]),
        ("Godan 1型 (頭高)", "書く", ["書く", "書いた", "書いて", "書かない", "書きます", "書ける"]),
        ("Godan 0型 (平板)", "行く", ["行く", "行った", "行って", "行かない", "行きます"]),
        ("Godan 1型 (頭高)", "飲む", ["飲む", "飲んだ", "飲んで", "飲まない", "飲みます"]),
    ]

    for group_name, base, forms in verb_groups:
        base_result = engine.analyze(base)
        print(f"\n{'─'*70}")
        print(f"{group_name}: {base} (base accent: {base_result.accent_type}型)")
        print(f"{'─'*70}")
        print(f"{'Form':<12} {'Reading':<12} {'Pattern':<10} {'Type':<8} {'Visual'}")
        print(f"{'-'*12} {'-'*12} {'-'*10} {'-'*8} {'-'*20}")

        for form in forms:
            r = engine.analyze(form)
            type_str = {0: "平板", 1: "頭高"}.get(r.accent_type, f"{r.accent_type}型")
            visual = visualize_pattern(r.pattern, r.reading + "•")
            print(f"{form:<12} {r.reading:<12} {r.pattern:<10} {type_str:<8} {visual}")

    # Minimal pairs
    print(f"\n{'='*70}")
    print("MINIMAL PAIRS (nouns)")
    print(f"{'='*70}")

    pairs = [
        ("箸", "橋", "端"),  # hashi
        ("雨", "飴"),  # ame
        ("酒", "鮭"),  # sake
        ("神", "紙", "髪"),  # kami
    ]

    for group in pairs:
        print(f"\n{group[0]}系:")
        for word in group:
            r = engine.analyze(word)
            visual = visualize_pattern(r.pattern, r.reading + "•")
            type_str = {0: "平板", 1: "頭高"}.get(r.accent_type, f"{r.accent_type}型")
            print(f"  {word} [{r.reading}]: {r.pattern} ({type_str}) {visual}")

    print(f"\n{'='*70}")
    print("ENGINE SUMMARY")
    print(f"{'='*70}")
    print("""
This engine computes pitch accent for Japanese words and conjugations using:

1. UniDic's aType (base accent position)
2. UniDic's aModType (inflection modification, e.g., M4@1 for ichidan stems)
3. UniDic's aConType (suffix combination rules using F1-F6 system)

Unlike JPDB which returns dictionary form patterns, this engine computes
the actual pitch pattern for conjugated forms.
""")


if __name__ == "__main__":
    main()

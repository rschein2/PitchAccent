#!/usr/bin/env python3
"""Compare our accent engine against JPDB."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from pitch_accent.engine import FugashiAccentEngine

API_KEY = os.environ.get("JPDB_API_KEY", "af4dc26c0bc3616ab2c483556fa7c495")

engine = FugashiAccentEngine()

# JPDB session
session = requests.Session()
session.headers["Authorization"] = f"Bearer {API_KEY}"
session.headers["Content-Type"] = "application/json"


def get_jpdb_pattern(word):
    """Get pattern from JPDB."""
    payload = {
        "text": word,
        "token_fields": ["vocabulary_index", "furigana"],
        "vocabulary_fields": ["spelling", "reading", "pitch_accent"],
    }
    resp = session.post("https://jpdb.io/api/v1/parse", json=payload, timeout=10)
    data = resp.json()
    if data.get("vocabulary"):
        vocab = data["vocabulary"][0]
        pitch = vocab[2] if len(vocab) > 2 else []
        return pitch[0] if pitch else ""
    return ""


print("=" * 70)
print("DICTIONARY FORM COMPARISON (JPDB gives dictionary form patterns only)")
print("=" * 70)

dict_forms = ["食べる", "書く", "行く", "見る", "話す", "飲む", "読む", "聞く"]

print(f"{'Word':<12} {'Engine':<12} {'JPDB':<12} {'Match'}")
print("-" * 50)

matches = 0
for word in dict_forms:
    result = engine.analyze(word)
    jpdb = get_jpdb_pattern(word)
    match = "✓" if result.pattern == jpdb else "✗"
    if result.pattern == jpdb:
        matches += 1
    print(f"{word:<12} {result.pattern:<12} {jpdb:<12} {match}")

print(f"\nDictionary form accuracy: {matches}/{len(dict_forms)}")

print("\n" + "=" * 70)
print("CONJUGATED FORM COMPARISON")
print("(JPDB returns dict pattern; our engine computes actual conjugated pattern)")
print("=" * 70)

conj_forms = [
    ("食べる", "食べた", "食べて", "食べない", "食べます"),
    ("書く", "書いた", "書いて", "書かない", "書きます"),
    ("行く", "行った", "行って", "行かない", "行きます"),
]

for group in conj_forms:
    base = group[0]
    jpdb_base = get_jpdb_pattern(base)
    print(f"\n{base} (JPDB dict pattern: {jpdb_base}):")

    for form in group:
        result = engine.analyze(form)
        jpdb = get_jpdb_pattern(form)
        same_as_dict = "← dict" if jpdb == jpdb_base else ""
        print(f"  {form:<12} engine={result.pattern:<8} jpdb={jpdb:<8} {same_as_dict}")

print("\n" + "=" * 70)
print("NOTE: JPDB lemmatizes, so 食べた → 食べる pattern")
print("Our engine computes actual conjugated form pitch (more accurate for TTS/learning)")
print("=" * 70)

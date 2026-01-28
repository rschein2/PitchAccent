#!/usr/bin/env python3
"""
Extract accent combination rules from UniDic and build a lookup table.
"""
import fugashi
import unidic
import json
import re
from collections import defaultdict

tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

# Parse aConType string into structured data
F_RE = re.compile(r"^F(?P<ft>[1-6])(?:@(?P<m>-?\d+))?(?:@(?P<l>-?\d+))?$")

def parse_acon_type(acon: str) -> dict:
    """Parse aConType like '動詞%F4@1,名詞%F1' into structured dict."""
    if not acon or acon == '*':
        return {}

    result = {}
    for part in acon.split(','):
        if '%' not in part:
            continue
        prev_pos, spec = part.split('%', 1)
        m = F_RE.match(spec)
        if m:
            ft = f"F{m.group('ft')}"
            M = int(m.group('m')) if m.group('m') else None
            L = int(m.group('l')) if m.group('l') else None
            result[prev_pos] = {"type": ft, "M": M, "L": L}
        else:
            result[prev_pos] = {"type": spec, "M": None, "L": None}
    return result

# Comprehensive list of suffixes/particles to extract
test_items = [
    # Auxiliary verbs (助動詞)
    "ます", "た", "だ", "です", "ない", "ぬ", "れる", "られる",
    "せる", "させる", "たい", "たがる", "らしい", "ようだ", "そうだ",
    "べきだ", "はずだ", "つもりだ", "う", "よう", "まい",
    # Particles (助詞)
    "が", "を", "に", "へ", "で", "と", "から", "まで", "より",
    "は", "も", "か", "な", "ね", "よ", "の", "ば", "て", "で",
    "けど", "けれど", "のに", "ので", "たり", "ながら", "し",
    # Conditional/other
    "なら", "たら",
]

print("=" * 70)
print("SUFFIX/PARTICLE ACCENT COMBINATION RULES (from UniDic 3.1.0)")
print("=" * 70)

suffix_rules = {}

for item in test_items:
    for node in tagger(item):
        f = node.feature
        if f.pos1 in ('助動詞', '助詞'):
            key = f"{node.surface}|{f.pos1}|{f.pos2}|{f.cType}"
            if key not in suffix_rules:
                parsed = parse_acon_type(f.aConType)
                suffix_rules[key] = {
                    "surface": node.surface,
                    "pos1": f.pos1,
                    "pos2": f.pos2,
                    "cType": f.cType,
                    "lemma": f.lemma,
                    "aConType_raw": f.aConType,
                    "aConType": parsed,
                }
                print(f"\n{node.surface} ({f.pos1}/{f.pos2}, {f.cType}):")
                print(f"  aConType: {f.aConType}")
                for pos, rule in parsed.items():
                    print(f"    {pos}: {rule['type']}" +
                          (f"@{rule['M']}" if rule['M'] is not None else "") +
                          (f"@{rule['L']}" if rule['L'] is not None else ""))

# Also extract verb aModType patterns
print("\n" + "=" * 70)
print("VERB INFLECTION PATTERNS (aModType)")
print("=" * 70)

verb_forms = [
    ("食べる", "ichidan"),
    ("食べ", "ichidan-stem"),
    ("食べない", "ichidan-neg"),
    ("食べた", "ichidan-past"),
    ("食べて", "ichidan-te"),
    ("食べれば", "ichidan-ba"),
    ("食べろ", "ichidan-imp"),
    ("食べよう", "ichidan-vol"),
    ("食べられる", "ichidan-potential"),
    ("書く", "godan"),
    ("書か", "godan-stem-a"),
    ("書き", "godan-stem-i"),
    ("書いた", "godan-past"),
    ("書いて", "godan-te"),
    ("書けば", "godan-ba"),
    ("書け", "godan-imp"),
    ("書こう", "godan-vol"),
    ("書ける", "godan-potential"),
    ("する", "suru"),
    ("し", "suru-stem"),
    ("した", "suru-past"),
    ("して", "suru-te"),
    ("すれば", "suru-ba"),
    ("しろ", "suru-imp"),
    ("しよう", "suru-vol"),
    ("できる", "dekiru"),
    ("来る", "kuru"),
    ("来", "kuru-stem"),
    ("来た", "kuru-past"),
]

verb_patterns = {}
for phrase, label in verb_forms:
    print(f"\n{phrase} ({label}):")
    for node in tagger(phrase):
        f = node.feature
        if f.pos1 == '動詞':
            print(f"  {node.surface}: cForm={f.cForm}, aType={f.aType}, aModType={f.aModType}")
            key = f"{f.cType}|{f.cForm}"
            if key not in verb_patterns:
                verb_patterns[key] = {
                    "cType": f.cType,
                    "cForm": f.cForm,
                    "aModType": f.aModType,
                    "example": node.surface,
                }

# Save to JSON
output = {
    "suffix_rules": suffix_rules,
    "verb_inflection_patterns": verb_patterns,
}

with open("accent_rules.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 70)
print(f"Saved {len(suffix_rules)} suffix rules and {len(verb_patterns)} verb patterns to accent_rules.json")
print("=" * 70)

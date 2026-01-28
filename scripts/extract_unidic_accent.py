#!/usr/bin/env python3
"""
Extract accent combination rules (aConType) from UniDic via fugashi/MeCab.
"""
import fugashi
import unidic
from collections import defaultdict
import json
import re

# Initialize tagger with UniDic
tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

# Test what fields are available
print("=== Testing UniDic field access ===\n")

test_words = ["ます", "た", "て", "ない", "を", "が", "は", "に", "食べる", "行く"]

for word in test_words:
    print(f"--- {word} ---")
    for node in tagger(word):
        print(f"  surface: {node.surface}")
        print(f"  feature: {node.feature}")
        # Try to access named features
        try:
            f = node.feature
            print(f"  pos1: {f.pos1}")
            print(f"  pos2: {f.pos2}")
            print(f"  pos3: {f.pos3}")
            print(f"  pos4: {f.pos4}")
            print(f"  cType: {f.cType}")
            print(f"  cForm: {f.cForm}")
            print(f"  lForm: {f.lForm}")
            print(f"  lemma: {f.lemma}")
            print(f"  orth: {f.orth}")
            print(f"  pron: {f.pron}")
            print(f"  kana: {f.kana}")
            # Try accent-related fields
            if hasattr(f, 'aType'):
                print(f"  aType: {f.aType}")
            if hasattr(f, 'aConType'):
                print(f"  aConType: {f.aConType}")
            if hasattr(f, 'aModType'):
                print(f"  aModType: {f.aModType}")
            # Print all available attributes
            print(f"  [all attrs]: {[a for a in dir(f) if not a.startswith('_')]}")
        except Exception as e:
            print(f"  Error accessing features: {e}")
    print()

#!/usr/bin/env python3
import requests
import json
import os

api_key = os.environ.get("JPDB_API_KEY")
session = requests.Session()
session.headers["Authorization"] = f"Bearer {api_key}"
session.headers["Content-Type"] = "application/json"

test_inputs = [
    "食べる",      # dictionary form
    "食べた",      # past
    "食べている",  # progressive
    "食べません",  # polite negative
    "食べられる",  # potential
    "雨が降っている",  # full sentence
    "箸で食べる",      # phrase
]

for text in test_inputs:
    payload = {
        "text": text,
        "token_fields": ["vocabulary_index", "furigana"],
        "vocabulary_fields": ["spelling", "reading", "pitch_accent"],
        "position_length_encoding": "utf16",
    }
    resp = session.post("https://jpdb.io/api/v1/parse", json=payload, timeout=10)
    data = resp.json()
    print(f"\n=== Input: {text} ===")
    tokens = data.get("tokens", [])
    vocab_list = data.get("vocabulary", [])
    print(f"Tokens: {len(tokens)}, Vocabulary entries: {len(vocab_list)}")

    for i, tok in enumerate(tokens):
        vocab_idx = tok[0]
        furigana = tok[1]
        pos = tok[2] if len(tok) > 2 else "?"
        length = tok[3] if len(tok) > 3 else "?"

        vocab = vocab_list[vocab_idx] if vocab_idx < len(vocab_list) else None
        if vocab:
            spelling, reading = vocab[0], vocab[1]
            pitch = vocab[2] if len(vocab) > 2 else []
            print(f"  Token {i}: pos={pos}, len={length}, furigana={furigana}")
            print(f"    -> vocab: {spelling} [{reading}] pitch={pitch}")

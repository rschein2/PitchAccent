#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a gold accent corpus by mining OJAD's verb conjugation tables.

OJAD (Online Japanese Accent Dictionary, U. Tokyo) publishes expert-curated
accent for every major conjugation of thousands of verbs. This script
scrapes the search results for a list of common verbs (JLPT vocabulary),
parses the accent nucleus positions, and writes tests/gold/ojad_verbs.json.

The scrape is polite (single-threaded, DELAY seconds between requests) and
resumable: verbs already present in the output file are skipped, so
re-running only fetches what's missing.

Usage:
    python scripts/build_ojad_gold.py [--limit N] [--verbs 食べる 行く ...]

Requires: requests, beautifulsoup4, fugashi, unidic.
"""
import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from pitch_accent.utils import kata_to_hira  # noqa: E402

BASE_URL = "https://www.gavo.t.u-tokyo.ac.jp/ojad/search/index"
DELAY = 1.5  # seconds between requests — be polite, this is an academic site
OUTPUT = Path(__file__).parent.parent / "tests" / "gold" / "ojad_verbs.json"
JLPT_VOCAB = Path(__file__).parent.parent / "data" / "jlpt" / "jlpt_vocabulary.json"

# OJAD conjugation columns, in table order
FORM_KEYS = [
    "jisho", "masu", "te", "ta", "nai", "nakatta",
    "ba", "shieki", "ukemi", "meirei", "kano", "ishi",
]

session = requests.Session()
session.headers["User-Agent"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(PitchAccent gold-corpus builder; contact: russelltodd@gmail.com)"
)


def parse_accented_word(span) -> tuple[str, int]:
    """
    Parse one span.accented_word into (kana, accent).

    OJAD marks the accent nucleus mora with class 'accent_top'.
    No accent_top mora => heiban (0).
    """
    kana = ""
    accent = 0
    mora_index = 0
    for mola in span.select("span[class*=mola_]"):
        mora_index += 1
        chars = "".join(c.get_text() for c in mola.select("span.char"))
        kana += chars
        if "accent_top" in (mola.get("class") or []):
            accent = mora_index
    return kana, accent


def fetch_word(word: str) -> list[dict]:
    """
    Fetch ALL of OJAD's conjugation rows for a headword.

    Homographs get one row per reading (開く: あく AND ひらく), so the
    result is a list of {"reading": ..., "forms": {...}} entries. Empty
    list if the word wasn't found.
    """
    url = f"{BASE_URL}/yure:visible/word:{quote(word)}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    entries = []
    seen_readings = set()
    for tr in soup.select("tr"):
        midashi = tr.select_one("td.midashi")
        if not midashi:
            continue
        headword = midashi.get_text(strip=True).split("・")[0]
        if headword != word:
            continue

        cells = tr.select("td.katsuyo")
        if len(cells) != len(FORM_KEYS):
            continue

        forms = {}
        for key, cell in zip(FORM_KEYS, cells):
            variants = []
            kana = ""
            for aw in cell.select("span.accented_word"):
                k, accent = parse_accented_word(aw)
                if not k:
                    continue
                if not kana:
                    kana = k
                if k == kana and accent not in variants:
                    variants.append(accent)
            if kana:
                forms[key] = {"kana": kana, "accents": variants}

        if not forms:
            continue
        reading = forms.get("jisho", {}).get("kana", "")
        if reading in seen_readings:
            continue
        seen_readings.add(reading)
        entries.append({"reading": reading, "forms": forms})

    return entries


def collect_words(limit: int, pos: str = "動詞") -> list[str]:
    """Common single-word verbs/adjectives from JLPT vocab, easiest level first."""
    import fugashi
    import unidic
    tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

    with open(JLPT_VOCAB, encoding="utf-8") as f:
        vocab = json.load(f)

    level_order = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4}
    candidates = sorted(vocab.items(), key=lambda kv: level_order.get(kv[1], 9))

    words = []
    for word, _level in candidates:
        if len(words) >= limit:
            break
        nodes = list(tagger(word))
        if len(nodes) != 1:
            continue
        f0 = nodes[0].feature
        if f0.pos1 != pos or nodes[0].surface != f0.lemma:
            continue
        ctype = f0.cType or ""
        if pos == "動詞" and not any(
                t in ctype for t in ("五段", "一段", "サ行変格", "カ行変格")):
            continue
        if pos == "形容詞" and "形容詞" not in ctype:
            continue
        words.append(word)
    return words


def migrate_v1(gold: dict) -> dict:
    """Wrap v1 single-entry records ({reading, forms}) into the v2 schema
    ({pos, entries: [...]})."""
    migrated = {}
    for word, rec in gold.items():
        if "entries" in rec:
            migrated[word] = rec
        else:
            migrated[word] = {"pos": rec.get("pos", "verb"),
                              "entries": [{"reading": rec["reading"],
                                           "forms": rec["forms"]}]}
    return migrated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200,
                    help="number of JLPT words to mine (default 200)")
    ap.add_argument("--verbs", nargs="*",
                    help="explicit word list (overrides JLPT selection)")
    ap.add_argument("--adjectives", action="store_true",
                    help="mine i-adjectives instead of verbs")
    ap.add_argument("--refetch", nargs="*",
                    help="re-fetch these words even if already present")
    args = ap.parse_args()

    pos_label = "adjective" if args.adjectives else "verb"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    gold: dict[str, dict] = {}
    if OUTPUT.exists():
        with open(OUTPUT, encoding="utf-8") as f:
            gold = migrate_v1(json.load(f))
        print(f"Resuming: {len(gold)} words already mined")

    if args.refetch:
        for w in args.refetch:
            gold.pop(w, None)
        words = args.refetch
    elif args.verbs:
        words = args.verbs
    else:
        words = collect_words(args.limit, "形容詞" if args.adjectives else "動詞")

    todo = [w for w in words if w not in gold]
    print(f"Fetching {len(todo)} {pos_label}s from OJAD ({DELAY}s delay)...")

    fetched = failed = 0
    for i, word in enumerate(todo):
        try:
            entries = fetch_word(word)
        except requests.RequestException as exc:
            print(f"  [{i+1}/{len(todo)}] {word}: network error {exc}")
            failed += 1
            time.sleep(DELAY)
            continue

        if entries:
            gold[word] = {"pos": pos_label, "entries": entries}
            fetched += 1
            readings = "/".join(e["reading"] for e in entries)
            print(f"  [{i+1}/{len(todo)}] {word} [{readings}] "
                  f"{len(entries)} entr{'ies' if len(entries) > 1 else 'y'}")
        else:
            failed += 1
            print(f"  [{i+1}/{len(todo)}] {word}: not found in OJAD")

        # Save incrementally so interruptions lose nothing
        if fetched % 10 == 0 or i == len(todo) - 1:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(gold, f, ensure_ascii=False, indent=1)

        time.sleep(DELAY)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(gold, f, ensure_ascii=False, indent=1)
    print(f"\nDone: {len(gold)} words total ({fetched} new, {failed} failed/missing)")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()

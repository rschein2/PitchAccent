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


def fetch_verb(verb: str) -> dict | None:
    """
    Fetch OJAD's conjugation row for one verb.

    Returns {"reading": ..., "forms": {form_key: {"kana": ..., "accents": [...]}}}
    or None if the verb wasn't found.
    """
    url = f"{BASE_URL}/yure:visible/word:{quote(verb)}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tr in soup.select("tr"):
        midashi = tr.select_one("td.midashi")
        if not midashi:
            continue
        headword = midashi.get_text(strip=True).split("・")[0]
        if headword != verb:
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
            return None
        reading = forms.get("jisho", {}).get("kana", "")
        return {"reading": reading, "forms": forms}

    return None


def collect_verbs(limit: int) -> list[str]:
    """Common single-word verbs from the JLPT vocabulary, easiest level first."""
    import fugashi
    import unidic
    tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

    with open(JLPT_VOCAB, encoding="utf-8") as f:
        vocab = json.load(f)

    level_order = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4}
    candidates = sorted(vocab.items(), key=lambda kv: level_order.get(kv[1], 9))

    verbs = []
    for word, _level in candidates:
        if len(verbs) >= limit:
            break
        nodes = list(tagger(word))
        if len(nodes) != 1:
            continue
        f0 = nodes[0].feature
        if f0.pos1 != "動詞" or nodes[0].surface != f0.lemma:
            continue
        ctype = f0.cType or ""
        if not any(t in ctype for t in ("五段", "一段", "サ行変格", "カ行変格")):
            continue
        verbs.append(word)
    return verbs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200,
                    help="number of JLPT verbs to mine (default 200)")
    ap.add_argument("--verbs", nargs="*",
                    help="explicit verb list (overrides JLPT selection)")
    args = ap.parse_args()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    gold: dict[str, dict] = {}
    if OUTPUT.exists():
        with open(OUTPUT, encoding="utf-8") as f:
            gold = json.load(f)
        print(f"Resuming: {len(gold)} verbs already mined")

    verbs = args.verbs if args.verbs else collect_verbs(args.limit)
    todo = [v for v in verbs if v not in gold]
    print(f"Fetching {len(todo)} verbs from OJAD ({DELAY}s delay)...")

    fetched = failed = 0
    for i, verb in enumerate(todo):
        try:
            entry = fetch_verb(verb)
        except requests.RequestException as exc:
            print(f"  [{i+1}/{len(todo)}] {verb}: network error {exc}")
            failed += 1
            time.sleep(DELAY)
            continue

        if entry:
            gold[verb] = entry
            fetched += 1
            print(f"  [{i+1}/{len(todo)}] {verb} [{entry['reading']}] "
                  f"{len(entry['forms'])} forms")
        else:
            failed += 1
            print(f"  [{i+1}/{len(todo)}] {verb}: not found in OJAD")

        # Save incrementally so interruptions lose nothing
        if fetched % 10 == 0 or i == len(todo) - 1:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(gold, f, ensure_ascii=False, indent=1)

        time.sleep(DELAY)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(gold, f, ensure_ascii=False, indent=1)
    print(f"\nDone: {len(gold)} verbs total ({fetched} new, {failed} failed/missing)")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()

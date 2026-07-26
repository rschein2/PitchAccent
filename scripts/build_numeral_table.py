#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build data/numeral_accent.json from the 日本語教育用アクセント辞典 counter
pages (accent.u-biq.org/counter1-4.html).

The pages mark pitch with span classes:
    a1 = initial low   a2 = high        a3 = low after the drop
    a4 = high continuing to the end (heiban tail)
Decoding per row (one row = one numeral 1..10):
    - a3 present         -> accent = number of morae before the first a3 mora
    - a4 present         -> heiban [0]
    - ends in a2 (a1+a2) -> odaka  [mora count]

The live site was unreachable at build time, so pages are fetched from the
Wayback Machine by default; pass local HTML files (cp932) to skip fetching.

Usage:
    python scripts/build_numeral_table.py [counter1.html ... counter4.html]
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pitch_accent.utils import split_morae  # noqa: E402

OUTPUT = Path(__file__).parent.parent / "data" / "numeral_accent.json"
WAYBACK = "https://web.archive.org/web/2024id_/https://accent.u-biq.org/counter{n}.html"

# Fixes for quirks in the source pages
CORRECTIONS = {
    # Site typo: 2段目 printed as にかだんめ
    ("段目", "2"): {"reading": "にだんめ", "accent": 0},
}
# 日間 row 1 on the site is 二十四時間 ("one day's duration"), not a
# numeral+counter form — drop it.
DELETIONS = {("日間", "1")}

# Hand-drafted entries for counters the site doesn't cover (e.g. 円).
# Mark confidence "drafted" and verify in the NHK accent dictionary app by
# searching the individual words. Currently empty: everything common the
# project needs was on the site.
DRAFTED: dict = {}


def fetch_pages() -> list[str]:
    import gzip
    import urllib.request
    pages = []
    for n in range(1, 5):
        req = urllib.request.Request(
            WAYBACK.format(n=n), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        pages.append(raw.decode("cp932", errors="replace"))
        time.sleep(2)
    return pages


def parse_row(row_html: str):
    """One <p> row -> (reading, accent) via the a1-a4 span classes."""
    spans = re.findall(r'<span class="(a[1-4])">([^<]+)</span>', row_html)
    if not spans:
        return None
    reading = ""
    mora_classes = []
    for cls, text in spans:
        for mora in split_morae(text):
            reading += mora
            mora_classes.append(cls)
    if not mora_classes:
        return None

    if "a3" in mora_classes:
        accent = mora_classes.index("a3")
    elif "a4" in mora_classes:
        accent = 0
    elif mora_classes[-1] == "a2" and "a1" in mora_classes:
        accent = len(mora_classes)  # odaka
    elif mora_classes[-1] == "a2":
        accent = len(mora_classes)  # all-a2: treat as odaka too
    else:
        accent = 0
    return reading, accent


def parse_page(src: str) -> dict:
    counters = {}
    # Split on counter headers <div class="ao">TITLE</div>
    blocks = re.split(r'<div class="ao"[^>]*>', src)[1:]
    for block in blocks:
        m = re.match(r"([^<（]+)(?:（([^）]*)）)?</div>", block)
        if not m:
            continue
        title = m.group(1).strip()
        gloss = (m.group(2) or "").strip()
        rows = re.findall(r"<p>(.*?)</p>", block, re.S)
        numerals = {}
        idx = 0
        for row in rows:
            parsed = parse_row(row)
            if not parsed:
                continue
            idx += 1
            if idx > 10:
                break
            reading, accent = parsed
            numerals[str(idx)] = {"reading": reading, "accent": accent}
        if numerals:
            counters[title] = {
                "gloss": gloss,
                "confidence": "verified",
                "numerals": numerals,
            }
    return counters


def main():
    if len(sys.argv) > 1:
        pages = [open(p, encoding="cp932", errors="replace").read()
                 for p in sys.argv[1:]]
    else:
        print("Fetching counter1-4 from the Wayback Machine...")
        pages = fetch_pages()

    counters = {}
    for src in pages:
        counters.update(parse_page(src))

    for (counter, num), fix in CORRECTIONS.items():
        if counter in counters and num in counters[counter]["numerals"]:
            counters[counter]["numerals"][num] = fix
    for counter, num in DELETIONS:
        if counter in counters:
            counters[counter]["numerals"].pop(num, None)

    for name, entry in DRAFTED.items():
        counters.setdefault(name, entry)

    data = {
        "_source": ("日本語教育用アクセント辞典 (accent.u-biq.org, counter1-4), "
                    "retrieved via Wayback Machine. Drafted entries are marked "
                    "confidence=drafted — verify in the NHK accent dictionary."),
        "counters": counters,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    total = sum(len(c["numerals"]) for c in counters.values())
    print(f"Wrote {OUTPUT}: {len(counters)} counters, {total} cells")
    for name, c in counters.items():
        n = c["numerals"]
        sample = ", ".join(f"{k}:{v['reading']}[{v['accent']}]"
                           for k, v in list(n.items())[:3])
        print(f"  {name} ({c['gloss']}): {len(n)} — {sample}")


if __name__ == "__main__":
    main()

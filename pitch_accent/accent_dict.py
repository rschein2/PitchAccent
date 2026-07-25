#!/usr/bin/env python3
"""
Local pitch accent dictionary (Kanjium data).

Provides whole-word accent lookups from the Kanjium accent database
(~124k entries). Dictionary hits take priority over rule-based
computation: rules are only needed for conjugated forms and novel
compounds that aren't lexicalized.

Data: data/kanjium/accents.txt.gz
Format per line: surface<TAB>reading(hiragana)<TAB>accents
where accents is comma-separated accent positions, primary first
(e.g. "0,3" = usually heiban, variant [3]).

Source: https://github.com/mifunetoshiro/kanjium (CC BY-SA 4.0)
"""
import gzip
from pathlib import Path
from typing import Optional

from .utils import kata_to_hira

DEFAULT_DATA_FILE = Path(__file__).parent.parent / "data" / "kanjium" / "accents.txt.gz"


class AccentDictionary:
    """
    In-memory accent dictionary keyed by surface form.

    lookup(surface, reading) returns the list of accent positions
    (primary first) or None if the word isn't in the dictionary.
    """

    def __init__(self, data_file: Path = DEFAULT_DATA_FILE):
        # surface -> list of (reading, [accent, ...]) preserving file order
        self._by_surface: dict[str, list[tuple[str, list[int]]]] = {}
        self._load(data_file)

    def _load(self, data_file: Path):
        with gzip.open(data_file, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                surface, reading, accents_str = parts
                try:
                    accents = [int(a) for a in accents_str.split(",")]
                except ValueError:
                    continue
                self._by_surface.setdefault(surface, []).append((reading, accents))

    def __len__(self):
        return sum(len(v) for v in self._by_surface.values())

    def lookup(self, surface: str, reading: Optional[str] = None) -> Optional[list[int]]:
        """
        Look up accent variants for a word.

        Args:
            surface: written form (kanji/kana)
            reading: hiragana or katakana reading, used to disambiguate
                     homographs (端: はし[0] vs たん[1]). If None and the
                     surface has exactly one entry, that entry is returned;
                     with multiple entries and no reading, returns None
                     (ambiguous — caller should supply the reading).

        Returns:
            List of accent positions, primary first, or None.
        """
        entries = self._by_surface.get(surface)
        if not entries:
            return None

        if reading is None:
            if len(entries) == 1:
                return list(entries[0][1])
            return None

        reading = kata_to_hira(reading)
        for entry_reading, accents in entries:
            if entry_reading == reading:
                return list(accents)
        return None

    def lookup_all(self, surface: str) -> dict[str, list[int]]:
        """Return {reading: [accents]} for every entry with this surface."""
        entries = self._by_surface.get(surface, [])
        return {r: list(a) for r, a in entries}


_default_instance: Optional[AccentDictionary] = None


def get_accent_dictionary() -> Optional[AccentDictionary]:
    """
    Shared lazily-loaded dictionary instance.

    Returns None if the data file is missing (the engine then falls back
    to pure rule-based computation).
    """
    global _default_instance
    if _default_instance is None:
        if not DEFAULT_DATA_FILE.exists():
            return None
        _default_instance = AccentDictionary()
    return _default_instance

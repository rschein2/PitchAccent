#!/usr/bin/env python3
"""
Japanese Pitch Accent Batch Lookup Tool
========================================

This script looks up pitch accent information for Japanese vocabulary words
using jpdb.io's API (primary) and OJAD scraping (fallback).

Usage:
    python pitch_accent_lookup.py --input words.txt --output results.csv
    python pitch_accent_lookup.py --words 家族 華族 箸 橋 雨 飴

Requirements:
    pip install requests beautifulsoup4 --break-system-packages

For jpdb.io API:
    Set your API key as environment variable: JPDB_API_KEY
    (Find it at the bottom of https://jpdb.io/settings)

Author: Claude (with Russell)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install requests beautifulsoup4 --break-system-packages")
    sys.exit(1)


@dataclass
class PitchAccentResult:
    """Result of a pitch accent lookup."""
    word: str
    reading: str = ""
    pitch_pattern: str = ""  # e.g., "LHH", "HLL", etc.
    accent_type: int = -1    # 0=平板, 1=頭高, 2+=中高/尾高
    mora_count: int = 0
    source: str = ""
    meanings: list = field(default_factory=list)
    error: str = ""
    
    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "reading": self.reading,
            "pitch_pattern": self.pitch_pattern,
            "accent_type": self.accent_type,
            "mora_count": self.mora_count,
            "source": self.source,
            "meanings": "; ".join(self.meanings[:3]) if self.meanings else "",
            "error": self.error,
        }
    
    def __str__(self) -> str:
        if self.error:
            return f"{self.word}: ERROR - {self.error}"
        
        accent_name = {
            0: "平板型",
            1: "頭高型",
        }.get(self.accent_type, f"{self.accent_type}型" if self.accent_type > 0 else "不明")
        
        return f"{self.word} [{self.reading}] - {self.pitch_pattern} ({accent_name}, {self.mora_count}拍)"


class JPDBClient:
    """Client for jpdb.io API."""
    
    BASE_URL = "https://jpdb.io/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("JPDB_API_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
        self.session.headers["Content-Type"] = "application/json"
    
    def lookup(self, word: str) -> PitchAccentResult:
        """Look up a word using jpdb.io API."""
        if not self.api_key:
            return PitchAccentResult(
                word=word,
                error="No JPDB API key set (export JPDB_API_KEY=...)"
            )
        
        try:
            # Use the parse endpoint to get vocabulary info
            payload = {
                "text": word,
                "token_fields": ["vocabulary_index", "furigana"],
                "vocabulary_fields": [
                    "vid", "sid", "spelling", "reading", 
                    "frequency_rank", "meanings",
                    "pitch_accent"  # This might be available
                ],
            }
            
            resp = self.session.post(
                f"{self.BASE_URL}/parse",
                json=payload,
                timeout=10
            )
            
            if resp.status_code == 403:
                return PitchAccentResult(word=word, error="Invalid API key")
            elif resp.status_code == 429:
                return PitchAccentResult(word=word, error="Rate limited - try again later")
            elif resp.status_code != 200:
                return PitchAccentResult(word=word, error=f"HTTP {resp.status_code}")
            
            data = resp.json()

            # Parse the response
            if not data.get("vocabulary"):
                return PitchAccentResult(word=word, error="Word not found in jpdb")

            # vocabulary is a list of lists, fields in order requested:
            # [vid, sid, spelling, reading, frequency_rank, meanings, pitch_accent]
            vocab = data["vocabulary"][0]

            # Extract fields by index (matching vocabulary_fields order)
            spelling = vocab[2] if len(vocab) > 2 else ""
            reading = vocab[3] if len(vocab) > 3 else ""
            meanings = vocab[5] if len(vocab) > 5 else []
            pitch_accent = vocab[6] if len(vocab) > 6 else []

            result = PitchAccentResult(
                word=word,
                reading=reading,
                source="jpdb.io",
                meanings=meanings if isinstance(meanings, list) else [],
            )

            # Check for pitch accent info - it comes as a list of patterns like ["LHLL"]
            if pitch_accent and isinstance(pitch_accent, list):
                pattern = pitch_accent[0] if pitch_accent else ""
                if isinstance(pattern, str):
                    result.pitch_pattern = pattern
                    # Derive accent type from pattern
                    result.accent_type = self._pattern_to_accent_type(pattern)

            # Calculate mora count from reading
            result.mora_count = self._count_mora(result.reading)

            return result
            
        except requests.RequestException as e:
            return PitchAccentResult(word=word, error=f"Network error: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            return PitchAccentResult(word=word, error=f"Parse error: {e}")
    
    def _count_mora(self, reading: str) -> int:
        """Count mora in a reading (accounting for small kana)."""
        # Small kana that don't count as separate mora
        small = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")
        count = 0
        for char in reading:
            if char not in small:
                count += 1
        return count

    def _pattern_to_accent_type(self, pattern: str) -> int:
        """
        Derive accent type from L/H pattern.
        0 = 平板 (heiban) - no drop, stays high
        1 = 頭高 (atamadaka) - drops after first mora
        2+ = 中高/尾高 - drops after nth mora
        """
        if not pattern:
            return -1
        # Find where the pitch drops from H to L
        for i in range(1, len(pattern)):
            if pattern[i-1] == "H" and pattern[i] == "L":
                return i
        # No drop found = heiban (0)
        if "H" in pattern:
            return 0
        return -1
    
    def _format_pitch(self, accent_pos: list, reading: str) -> str:
        """Format pitch accent as L/H pattern."""
        mora_count = self._count_mora(reading)
        if not mora_count or not accent_pos:
            return ""
        
        pos = accent_pos[0] if accent_pos else 0
        
        # Generate L/H pattern based on accent position
        if pos == 0:
            # 平板型: LHHH...
            return "L" + "H" * (mora_count - 1) if mora_count > 1 else "H"
        elif pos == 1:
            # 頭高型: HLL...
            return "H" + "L" * (mora_count - 1) if mora_count > 1 else "H"
        else:
            # 中高/尾高型: LH...HL...
            pattern = "L" + "H" * (pos - 1) + "L" * (mora_count - pos)
            return pattern


class OJADClient:
    """Client for OJAD (Online Japanese Accent Dictionary) via web scraping."""
    
    BASE_URL = "https://www.gavo.t.u-tokyo.ac.jp/ojad"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        )
    
    def lookup(self, word: str) -> PitchAccentResult:
        """Look up a word using OJAD's search."""
        try:
            # Use the word search endpoint
            params = {
                "word": word,
                "accent_type": "all",
            }
            
            resp = self.session.get(
                f"{self.BASE_URL}/search/index/word:{quote(word)}",
                timeout=15
            )
            
            if resp.status_code != 200:
                return PitchAccentResult(word=word, error=f"HTTP {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Try to find accent information in the page
            # OJAD uses specific classes for pitch visualization
            result = self._parse_ojad_response(soup, word)
            
            if not result.reading and not result.error:
                result.error = "Word not found in OJAD"
            
            return result
            
        except requests.RequestException as e:
            return PitchAccentResult(word=word, error=f"Network error: {e}")
    
    def lookup_suzuki(self, text: str) -> PitchAccentResult:
        """
        Use OJAD's Suzuki-kun prosody tutor for arbitrary text.
        This is more flexible but slower.
        """
        try:
            # POST to Suzuki-kun
            data = {
                "text": text,
                "curve": "advanced",
                "accent": "advanced",
            }
            
            resp = self.session.post(
                f"{self.BASE_URL}/phrasing/index",
                data=data,
                timeout=20
            )
            
            if resp.status_code != 200:
                return PitchAccentResult(word=text, error=f"HTTP {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_suzuki_response(soup, text)
            
        except requests.RequestException as e:
            return PitchAccentResult(word=text, error=f"Network error: {e}")
    
    def _parse_ojad_response(self, soup: BeautifulSoup, word: str) -> PitchAccentResult:
        """Parse OJAD search results page."""
        result = PitchAccentResult(word=word, source="OJAD")
        
        # Look for the word entry table
        # OJAD marks pitch with CSS classes and span elements
        entries = soup.select(".word_search_result tr")
        
        for entry in entries:
            # Check if this entry matches our word
            midashi = entry.select_one(".midashi")
            if midashi and word in midashi.get_text():
                # Found matching entry
                reading_el = entry.select_one(".ruby") or entry.select_one(".pron")
                if reading_el:
                    result.reading = reading_el.get_text(strip=True)
                
                # Try to extract pitch pattern from accent marks
                accent_el = entry.select_one(".accent_top, .accent_plain")
                if accent_el:
                    result.pitch_pattern = self._extract_pitch_from_html(entry)
                
                result.mora_count = self._count_mora(result.reading)
                break
        
        return result
    
    def _parse_suzuki_response(self, soup: BeautifulSoup, text: str) -> PitchAccentResult:
        """Parse Suzuki-kun prosody analysis response."""
        result = PitchAccentResult(word=text, source="OJAD/Suzuki-kun")
        
        # Suzuki-kun output has prosody curves
        prosody_div = soup.select_one("#output_analyze")
        if prosody_div:
            # Extract reading and pitch info
            text_output = prosody_div.get_text(strip=True)
            result.reading = text_output
            result.pitch_pattern = self._extract_suzuki_pitch(prosody_div)
        
        return result
    
    def _extract_pitch_from_html(self, element) -> str:
        """Extract pitch pattern from OJAD HTML elements."""
        # OJAD uses different CSS classes for high/low pitch
        # This is a simplified extraction
        pattern = []
        for span in element.select("span"):
            classes = span.get("class", [])
            if "accent_top" in classes:
                pattern.append("H")
            elif "accent_bottom" in classes or "accent_plain" in classes:
                pattern.append("L")
        return "".join(pattern) if pattern else ""
    
    def _extract_suzuki_pitch(self, element) -> str:
        """Extract pitch pattern from Suzuki-kun output."""
        # Simplified - Suzuki-kun uses SVG/Canvas for visualization
        # Would need more complex parsing for full extraction
        return ""
    
    def _count_mora(self, reading: str) -> int:
        """Count mora in reading."""
        small = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")
        return sum(1 for c in reading if c not in small)


class PitchAccentLookup:
    """Main lookup class that combines multiple sources."""
    
    def __init__(self, jpdb_api_key: Optional[str] = None):
        self.jpdb = JPDBClient(jpdb_api_key)
        self.ojad = OJADClient()
        self.cache: dict[str, PitchAccentResult] = {}
    
    def lookup(self, word: str, use_cache: bool = True) -> PitchAccentResult:
        """
        Look up pitch accent for a word.
        Tries jpdb.io first, falls back to OJAD.
        """
        if use_cache and word in self.cache:
            return self.cache[word]

        # Try jpdb first
        result = self.jpdb.lookup(word)

        # If jpdb didn't have pitch info or had an error, try OJAD
        if not result.pitch_pattern or result.error:
            ojad_result = self.ojad.lookup(word)
            if ojad_result.pitch_pattern:
                result.pitch_pattern = ojad_result.pitch_pattern
                result.source = "OJAD" if result.error else "jpdb.io + OJAD"
                result.error = ""  # Clear jpdb error if OJAD worked
            if not result.reading and ojad_result.reading:
                result.reading = ojad_result.reading
                if result.error and ojad_result.reading:
                    result.error = ""  # Got useful data from OJAD

        # If still no luck, try OJAD Suzuki-kun
        if not result.pitch_pattern:
            suzuki_result = self.ojad.lookup_suzuki(word)
            if suzuki_result.pitch_pattern:
                result.pitch_pattern = suzuki_result.pitch_pattern
                result.source = "OJAD/Suzuki-kun"
                result.error = ""
            if not result.reading and suzuki_result.reading:
                result.reading = suzuki_result.reading

        if use_cache:
            self.cache[word] = result

        return result
    
    def lookup_batch(
        self, 
        words: list[str], 
        delay: float = 0.5,
        progress: bool = True
    ) -> list[PitchAccentResult]:
        """
        Look up multiple words with rate limiting.
        
        Args:
            words: List of words to look up
            delay: Seconds to wait between requests
            progress: Show progress indicator
        
        Returns:
            List of results in same order as input
        """
        results = []
        total = len(words)
        
        for i, word in enumerate(words):
            if progress:
                print(f"\r[{i+1}/{total}] Looking up: {word}...", end="", flush=True)
            
            result = self.lookup(word)
            results.append(result)
            
            if i < total - 1:  # Don't delay after last word
                time.sleep(delay)
        
        if progress:
            print()  # New line after progress
        
        return results
    
    def group_by_accent_type(
        self, 
        results: list[PitchAccentResult]
    ) -> dict[int, list[PitchAccentResult]]:
        """Group results by accent type for study."""
        groups: dict[int, list[PitchAccentResult]] = {}
        for r in results:
            if r.accent_type >= 0:
                groups.setdefault(r.accent_type, []).append(r)
        return groups


def export_to_csv(results: list[PitchAccentResult], filename: str):
    """Export results to CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "word", "reading", "pitch_pattern", "accent_type",
            "mora_count", "source", "meanings", "error"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
    print(f"Exported {len(results)} results to {filename}")


def export_to_anki(results: list[PitchAccentResult], filename: str):
    """Export results as Anki-compatible TSV."""
    with open(filename, "w", encoding="utf-8") as f:
        for r in results:
            if not r.error:
                # Format: word<tab>reading<tab>pitch<tab>meaning
                line = f"{r.word}\t{r.reading}\t{r.pitch_pattern}\t{'; '.join(r.meanings[:2])}\n"
                f.write(line)
    print(f"Exported Anki-compatible file: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch lookup Japanese pitch accent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --words 家族 華族 箸 橋 雨 飴
  %(prog)s --input wordlist.txt --output results.csv
  %(prog)s --input wordlist.txt --anki flashcards.tsv
  
Environment:
  JPDB_API_KEY  Your jpdb.io API key (from jpdb.io/settings)
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--words", "-w",
        nargs="+",
        help="Words to look up"
    )
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="Input file (one word per line)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output CSV file"
    )
    parser.add_argument(
        "--anki", "-a",
        type=str,
        help="Output Anki-compatible TSV file"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help="Group results by accent type"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="jpdb.io API key (or set JPDB_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Get words to look up
    if args.words:
        words = args.words
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
    
    if not words:
        print("No words to look up!", file=sys.stderr)
        sys.exit(1)
    
    print(f"Looking up {len(words)} words...")
    
    # Initialize lookup client
    lookup = PitchAccentLookup(args.api_key)
    
    # Perform lookups
    results = lookup.lookup_batch(words, delay=args.delay)
    
    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if args.group:
        groups = lookup.group_by_accent_type(results)
        type_names = {
            0: "平板型 (Heiban - flat)",
            1: "頭高型 (Atamadaka - head-high)",
            2: "中高型 (Nakadaka - middle-high)",
            3: "尾高型 (Odaka - tail-high)",
        }
        for accent_type in sorted(groups.keys()):
            name = type_names.get(accent_type, f"Type {accent_type}")
            print(f"\n{name}:")
            for r in groups[accent_type]:
                print(f"  {r}")
    else:
        for r in results:
            print(r)
    
    # Show errors separately
    errors = [r for r in results if r.error]
    if errors:
        print(f"\n⚠️  {len(errors)} lookup(s) had errors:")
        for r in errors:
            print(f"  {r.word}: {r.error}")
    
    # Export if requested
    if args.output:
        export_to_csv(results, args.output)
    
    if args.anki:
        export_to_anki(results, args.anki)


if __name__ == "__main__":
    main()

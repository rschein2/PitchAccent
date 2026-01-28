#!/usr/bin/env python3
"""
Corpus Loader for Japanese Pitch Accent Anki Generator

Loads sentences from various sources:
- Tatoeba corpus (downloadable CSV)
- User-provided text files
- Interactive input
"""
import csv
import gzip
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Iterator, Optional


class TatoebaLoader:
    """
    Loader for Tatoeba Japanese sentences.

    Tatoeba provides CC-licensed sentence pairs. We use the Japanese sentences
    as source material for pitch accent practice.

    Download from: https://tatoeba.org/en/downloads
    """

    # Tatoeba download URL for Japanese sentences
    SENTENCES_URL = "https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences.tsv.gz"

    # Default cache location
    DEFAULT_CACHE = Path.home() / ".cache" / "pitch_accent" / "tatoeba"

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or self.DEFAULT_CACHE
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download(self, force: bool = False) -> Path:
        """
        Download Tatoeba Japanese sentences.

        Args:
            force: If True, re-download even if cached

        Returns:
            Path to the downloaded file
        """
        gz_path = self.cache_dir / "jpn_sentences.tsv.gz"
        tsv_path = self.cache_dir / "jpn_sentences.tsv"

        if tsv_path.exists() and not force:
            print(f"Using cached Tatoeba data: {tsv_path}")
            return tsv_path

        print(f"Downloading Tatoeba Japanese sentences...")
        print(f"  URL: {self.SENTENCES_URL}")

        try:
            urllib.request.urlretrieve(
                self.SENTENCES_URL,
                gz_path,
                reporthook=self._download_progress
            )
            print()  # New line after progress

            # Decompress
            print("Decompressing...")
            with gzip.open(gz_path, 'rt', encoding='utf-8') as f_in:
                with open(tsv_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(f_in.read())

            # Clean up gz file
            gz_path.unlink()

            print(f"Saved to: {tsv_path}")
            return tsv_path

        except Exception as e:
            print(f"Download failed: {e}", file=sys.stderr)
            raise

    def _download_progress(self, count, block_size, total_size):
        """Progress callback for download."""
        if total_size > 0:
            percent = int(count * block_size * 100 / total_size)
            print(f"\r  Progress: {percent}%", end="", flush=True)

    def load(self, limit: Optional[int] = None, min_length: int = 5, max_length: int = 100) -> list[str]:
        """
        Load sentences from Tatoeba corpus.

        Args:
            limit: Maximum number of sentences to load
            min_length: Minimum sentence length (chars)
            max_length: Maximum sentence length (chars)

        Returns:
            List of Japanese sentences
        """
        tsv_path = self.cache_dir / "jpn_sentences.tsv"

        if not tsv_path.exists():
            self.download()

        sentences = []

        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) >= 3:
                    # Format: id\tlang\ttext
                    sentence = row[2].strip()

                    # Filter by length
                    if len(sentence) < min_length:
                        continue
                    if len(sentence) > max_length:
                        continue

                    # Filter out sentences that are mostly non-Japanese
                    if not self._is_japanese(sentence):
                        continue

                    sentences.append(sentence)

                    if limit and len(sentences) >= limit:
                        break

        return sentences

    def _is_japanese(self, text: str) -> bool:
        """Check if text is primarily Japanese."""
        # Count Japanese characters (hiragana, katakana, kanji)
        jp_chars = 0
        total_chars = 0

        for char in text:
            code = ord(char)
            total_chars += 1
            # Hiragana, Katakana, or CJK
            if (0x3040 <= code <= 0x309F or  # Hiragana
                0x30A0 <= code <= 0x30FF or  # Katakana
                0x4E00 <= code <= 0x9FFF):   # CJK
                jp_chars += 1

        if total_chars == 0:
            return False

        return jp_chars / total_chars >= 0.5

    def stream(self, min_length: int = 5, max_length: int = 100) -> Iterator[str]:
        """
        Stream sentences from Tatoeba corpus (memory efficient).

        Yields:
            Japanese sentences one at a time
        """
        tsv_path = self.cache_dir / "jpn_sentences.tsv"

        if not tsv_path.exists():
            self.download()

        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) >= 3:
                    sentence = row[2].strip()

                    if len(sentence) < min_length:
                        continue
                    if len(sentence) > max_length:
                        continue

                    if not self._is_japanese(sentence):
                        continue

                    yield sentence


class TextFileLoader:
    """Loader for user-provided text files."""

    def load(self, path: str | Path) -> list[str]:
        """
        Load sentences from a text file.

        Extracts sentences by splitting on Japanese punctuation.

        Args:
            path: Path to text file

        Returns:
            List of sentences
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()

        return self.extract_sentences(text)

    def extract_sentences(self, text: str) -> list[str]:
        """
        Extract sentences from raw text.

        Splits on Japanese sentence-ending punctuation (。！？) and newlines.
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Split on sentence endings
        parts = re.split(r'([。！？]+)', text)

        sentences = []
        current = ""

        for part in parts:
            if re.match(r'^[。！？]+$', part):
                if current.strip():
                    sentences.append(current.strip() + part)
                    current = ""
            else:
                current += part

        if current.strip():
            sentences.append(current.strip())

        # Filter out very short or empty sentences
        sentences = [s for s in sentences if len(s) >= 3]

        return sentences


class InteractiveLoader:
    """Interactive loader for pasting text."""

    def load(self, prompt: str = "Paste your Japanese text (end with Ctrl+D or empty line):\n") -> list[str]:
        """
        Read text interactively from stdin.

        Args:
            prompt: Prompt to display

        Returns:
            List of sentences
        """
        print(prompt)

        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass

        text = "\n".join(lines)

        loader = TextFileLoader()
        return loader.extract_sentences(text)


class CorpusLoader:
    """
    Unified corpus loader supporting multiple sources.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.tatoeba = TatoebaLoader(cache_dir)
        self.text_file = TextFileLoader()
        self.interactive = InteractiveLoader()

    def load_tatoeba(self, limit: Optional[int] = None, **kwargs) -> list[str]:
        """Load from Tatoeba corpus."""
        return self.tatoeba.load(limit=limit, **kwargs)

    def load_file(self, path: str | Path) -> list[str]:
        """Load from text file."""
        return self.text_file.load(path)

    def load_text(self, text: str) -> list[str]:
        """Load from raw text string."""
        return self.text_file.extract_sentences(text)

    def load_interactive(self) -> list[str]:
        """Load interactively from stdin."""
        return self.interactive.load()


def main():
    """Test the corpus loaders."""
    import argparse

    parser = argparse.ArgumentParser(description="Test corpus loading")
    parser.add_argument("--tatoeba", action="store_true", help="Load from Tatoeba")
    parser.add_argument("--file", type=str, help="Load from file")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--limit", type=int, default=10, help="Number of sentences")

    args = parser.parse_args()

    loader = CorpusLoader()

    if args.tatoeba:
        print("Loading from Tatoeba...")
        sentences = loader.load_tatoeba(limit=args.limit)
    elif args.file:
        print(f"Loading from file: {args.file}")
        sentences = loader.load_file(args.file)
    elif args.interactive:
        sentences = loader.load_interactive()
    else:
        # Demo with sample text
        sample = """
        今日はいい天気ですね。明日も晴れるといいな。
        私は毎日図書館で本を読んでいます。
        新しい本を買いました！とても面白いです。
        """
        print("Loading from sample text...")
        sentences = loader.load_text(sample)

    print(f"\nLoaded {len(sentences)} sentences:")
    for i, s in enumerate(sentences, 1):
        print(f"  {i}. {s}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Anki Deck Generator for Japanese Pitch Accent

Generates Anki flashcards with:
- Front: Plain Japanese sentence
- Back: Color-coded pitch annotation + accent numbers + verb/adjective conjugation drills

Usage:
    # From Tatoeba corpus
    python anki_generator.py --corpus tatoeba --limit 100 --output deck.tsv

    # From user text file
    python anki_generator.py --input mytext.txt --output deck.tsv

    # Interactive mode (paste text)
    python anki_generator.py --interactive --output deck.tsv

    # From command-line text
    python anki_generator.py --text "今日は天気がいいですね。" --output deck.tsv
"""
import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from accent_engine import FugashiAccentEngine, AccentResult
from sentence_parser import SentenceParser, ParsedSentence, ParsedWord
from html_formatter import HTMLFormatter
from corpus_loader import CorpusLoader


@dataclass
class AnkiCard:
    """A single Anki flashcard."""
    front: str       # Plain sentence
    back: str        # HTML-formatted annotation
    tags: list[str]  # Tags for organization


class ConjugationGenerator:
    """
    Generates conjugation drills for verbs and adjectives.
    """

    # Common verb conjugations to include
    VERB_FORMS = [
        ("た", "past"),
        ("て", "te-form"),
        ("ない", "negative"),
        ("ます", "polite"),
    ]

    # Common adjective conjugations
    ADJ_FORMS = [
        ("かった", "past"),
        ("くない", "negative"),
        ("くて", "te-form"),
    ]

    def __init__(self, engine: FugashiAccentEngine):
        self.engine = engine

    def generate_verb_conjugations(self, word: ParsedWord) -> list[tuple[str, int, str]]:
        """
        Generate conjugation forms for a verb.

        Returns list of (form, accent_type, pattern) tuples.
        """
        if word.pos1 != "動詞":
            return []

        results = []

        # Get the dictionary form (lemma)
        lemma = word.lemma

        # Generate common forms by analyzing them
        for suffix, name in self.VERB_FORMS:
            # Construct the conjugated form
            # This is a simplification - we let the engine figure out the actual form
            # by analyzing the text directly
            try:
                test_form = self._make_verb_form(lemma, suffix)
                if test_form:
                    result = self.engine.analyze(test_form)
                    results.append((result.surface, result.accent_type, result.pattern))
            except Exception:
                continue

        return results

    def generate_adj_conjugations(self, word: ParsedWord) -> list[tuple[str, int, str]]:
        """Generate conjugation forms for an adjective."""
        if word.pos1 != "形容詞":
            return []

        results = []
        lemma = word.lemma

        for suffix, name in self.ADJ_FORMS:
            try:
                test_form = self._make_adj_form(lemma, suffix)
                if test_form:
                    result = self.engine.analyze(test_form)
                    results.append((result.surface, result.accent_type, result.pattern))
            except Exception:
                continue

        return results

    def _make_verb_form(self, lemma: str, suffix: str) -> Optional[str]:
        """
        Attempt to construct a verb conjugation.

        This is a best-effort approach - we construct potential forms
        and rely on the analyzer to validate them.
        """
        if not lemma:
            return None

        # Special cases: 行く, 来る, する (check FIRST before regular patterns)
        if lemma == "行く":
            if suffix == "た": return "行った"
            elif suffix == "て": return "行って"
            elif suffix == "ない": return "行かない"
            elif suffix == "ます": return "行きます"
        elif lemma == "来る":
            if suffix == "た": return "来た"
            elif suffix == "て": return "来て"
            elif suffix == "ない": return "来ない"
            elif suffix == "ます": return "来ます"
        elif lemma == "する":
            if suffix == "た": return "した"
            elif suffix == "て": return "して"
            elif suffix == "ない": return "しない"
            elif suffix == "ます": return "します"

        # For -る verbs (ichidan), typically remove る and add suffix
        if lemma.endswith("る"):
            stem = lemma[:-1]
            if suffix == "た":
                return stem + "た"
            elif suffix == "て":
                return stem + "て"
            elif suffix == "ない":
                return stem + "ない"
            elif suffix == "ます":
                return stem + "ます"

        # For -う verbs (godan), the conjugation is more complex
        # Let's just try analyzing the lemma + suffix and see if it parses
        # Actually, better to construct proper forms

        # Godan verb endings and their te/ta forms
        godan_map = {
            "う": ("った", "って", "わない", "います"),
            "つ": ("った", "って", "たない", "ちます"),
            "る": ("った", "って", "らない", "ります"),
            "む": ("んだ", "んで", "まない", "みます"),
            "ぬ": ("んだ", "んで", "なない", "にます"),
            "ぶ": ("んだ", "んで", "ばない", "びます"),
            "く": ("いた", "いて", "かない", "きます"),
            "ぐ": ("いだ", "いで", "がない", "ぎます"),
            "す": ("した", "して", "さない", "します"),
        }

        for ending, (ta, te, nai, masu) in godan_map.items():
            if lemma.endswith(ending):
                stem = lemma[:-1]
                if suffix == "た":
                    return stem + ta
                elif suffix == "て":
                    return stem + te
                elif suffix == "ない":
                    return stem + nai
                elif suffix == "ます":
                    return stem + masu
                break

        return None

    def _make_adj_form(self, lemma: str, suffix: str) -> Optional[str]:
        """Construct an adjective conjugation."""
        if not lemma or not lemma.endswith("い"):
            return None

        stem = lemma[:-1]

        if suffix == "かった":
            return stem + "かった"
        elif suffix == "くない":
            return stem + "くない"
        elif suffix == "くて":
            return stem + "くて"

        return None


class AnkiGenerator:
    """
    Main Anki card generator.

    Processes sentences and generates flashcards with pitch accent annotations.
    """

    def __init__(self):
        self.engine = FugashiAccentEngine()
        self.parser = SentenceParser()
        self.formatter = HTMLFormatter()
        self.conjugator = ConjugationGenerator(self.engine)

    def process_sentence(self, sentence: str) -> AnkiCard:
        """
        Process a single sentence and generate an Anki card.

        Args:
            sentence: Japanese sentence

        Returns:
            AnkiCard with front and back content
        """
        # Parse the sentence
        parsed = self.parser.parse_sentence(sentence)

        # Get annotations for content words
        annotated_words = []
        conjugation_drills = []
        seen_lemmas = set()  # Avoid duplicate drills

        for word in parsed.content_words():
            # For compounds, use the parser's pre-computed reading and accent
            # (which includes numeral conversion and sandhi rules)
            if word.is_compound:
                reading = word.reading
                accent_type = int(word.aType) if word.aType and word.aType != "*" else 0
                mora_count = self.engine.count_mora(reading)
                pattern = self.engine.accent_to_pattern(accent_type, mora_count)
            else:
                # For simple words, compute accent from morphemes
                result = self.engine.compute_accent(word.morphemes)
                reading = result.reading
                accent_type = result.accent_type
                pattern = result.pattern

            annotated_words.append((
                word.surface,
                reading,
                accent_type,
                pattern,
            ))

            # Generate conjugation drills for verbs/adjectives
            if word.pos1 == "動詞" and word.lemma not in seen_lemmas:
                seen_lemmas.add(word.lemma)
                conjugations = self.conjugator.generate_verb_conjugations(word)
                if conjugations:
                    # Get base form info
                    base_result = self.engine.analyze(word.lemma)
                    drill = self.formatter.format_conjugation_line(
                        word.lemma,
                        base_result.accent_type,
                        base_result.pattern,
                        conjugations
                    )
                    conjugation_drills.append(drill)

            elif word.pos1 == "形容詞" and word.lemma not in seen_lemmas:
                seen_lemmas.add(word.lemma)
                conjugations = self.conjugator.generate_adj_conjugations(word)
                if conjugations:
                    base_result = self.engine.analyze(word.lemma)
                    drill = self.formatter.format_conjugation_line(
                        word.lemma,
                        base_result.accent_type,
                        base_result.pattern,
                        conjugations
                    )
                    conjugation_drills.append(drill)

        # Format the back of the card
        back_html = self.formatter.format_anki_back(annotated_words, conjugation_drills)

        return AnkiCard(
            front=sentence,
            back=back_html,
            tags=["pitch_accent"]
        )

    def process_sentences(self, sentences: list[str], progress: bool = True) -> list[AnkiCard]:
        """
        Process multiple sentences.

        Args:
            sentences: List of Japanese sentences
            progress: Show progress indicator

        Returns:
            List of AnkiCards
        """
        cards = []
        total = len(sentences)

        for i, sentence in enumerate(sentences, 1):
            if progress:
                print(f"\rProcessing: {i}/{total}", end="", flush=True)

            try:
                card = self.process_sentence(sentence)
                cards.append(card)
            except Exception as e:
                print(f"\nError processing '{sentence[:20]}...': {e}", file=sys.stderr)

        if progress:
            print()

        return cards

    def export_tsv(self, cards: list[AnkiCard], path: str | Path):
        """
        Export cards to Anki-compatible TSV file.

        Format: front<TAB>back<TAB>tags
        """
        path = Path(path)

        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)

            for card in cards:
                tags = " ".join(card.tags)
                writer.writerow([card.front, card.back, tags])

        print(f"Exported {len(cards)} cards to {path}")

    def export_csv(self, cards: list[AnkiCard], path: str | Path):
        """
        Export cards to CSV file with headers.
        """
        path = Path(path)

        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['front', 'back', 'tags'])
            writer.writeheader()

            for card in cards:
                writer.writerow({
                    'front': card.front,
                    'back': card.back,
                    'tags': " ".join(card.tags),
                })

        print(f"Exported {len(cards)} cards to {path}")

    def export_html(self, cards: list[AnkiCard], path: str | Path):
        """
        Export cards to a standalone HTML file for viewing in browser.
        """
        path = Path(path)

        html = '''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pitch Accent Study</title>
<style>
body {
    font-family: "Hiragino Kaku Gothic Pro", "Yu Gothic", "Meiryo", sans-serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    background: #f5f5f5;
    line-height: 1.8;
}
h1 { color: #333; border-bottom: 2px solid #667; padding-bottom: 10px; }
.card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.sentence {
    font-size: 1.4em;
    margin-bottom: 15px;
    padding-bottom: 15px;
    border-bottom: 1px solid #eee;
}
.annotation { font-size: 1.1em; }
.conjugation {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px dashed #ccc;
    font-size: 0.95em;
    color: #555;
}
.legend {
    background: #fff;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
}
.legend span { margin-right: 20px; }
</style>
</head>
<body>
<h1>Pitch Accent Study Sheet</h1>
<div class="legend">
    <b>Legend:</b>
    <span style="color:red">High (H)</span>
    <span style="color:blue">Low (L)</span>
    <span>[n] = accent drops after mora n (0 = flat/heiban)</span>
</div>
'''
        for i, card in enumerate(cards, 1):
            # Split back into annotation and conjugation parts
            back_parts = card.back.split('<div style="border-top:')
            annotation = back_parts[0]
            conjugation = ""
            if len(back_parts) > 1:
                conjugation = '<div style="border-top:' + back_parts[1]

            html += f'''
<div class="card">
    <div class="sentence">{i}. {card.front}</div>
    <div class="annotation">{annotation}</div>
    {f'<div class="conjugation">{conjugation}</div>' if conjugation else ''}
</div>
'''

        html += '''
</body>
</html>
'''
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Exported {len(cards)} sentences to {path}")

    def export_text(self, cards: list[AnkiCard], path: str | Path):
        """
        Export cards to plain text with ASCII pitch markers.
        """
        import re
        path = Path(path)

        lines = []
        lines.append("PITCH ACCENT STUDY SHEET")
        lines.append("=" * 60)
        lines.append("Legend: [n] = accent type (0=flat, 1=drops after 1st, etc.)")
        lines.append("")

        for i, card in enumerate(cards, 1):
            lines.append(f"{'─' * 60}")
            lines.append(f"{i}. {card.front}")
            lines.append("")

            # Strip HTML tags for plain text
            back_text = card.back.replace('<br>', '\n').replace('\n\n', '\n')
            back_text = re.sub(r'<[^>]+>', '', back_text)

            for line in back_text.strip().split('\n'):
                if line.strip():
                    lines.append(f"   {line.strip()}")

            lines.append("")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"Exported {len(cards)} sentences to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for Japanese pitch accent learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --corpus tatoeba --limit 100 --output deck.tsv
  %(prog)s --input novel.txt --output deck.tsv
  %(prog)s --text "今日は天気がいいですね。" --output deck.tsv
  %(prog)s --interactive --output deck.tsv

Output:
  Generates a TSV file that can be imported directly into Anki.
  Front: Plain Japanese sentence
  Back: Color-coded pitch annotations with conjugation drills
        """
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--corpus",
        choices=["tatoeba"],
        help="Use built-in corpus (downloads if needed)"
    )
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="Input text file"
    )
    input_group.add_argument(
        "--text", "-t",
        type=str,
        help="Process text directly from command line"
    )
    input_group.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - paste text"
    )

    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        required=True,
        help="Output file (.tsv=Anki, .csv=CSV, .html=webpage, .txt=plain text)"
    )

    # Processing options
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Maximum number of sentences to process"
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=5,
        help="Minimum sentence length in characters (default: 5)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=100,
        help="Maximum sentence length in characters (default: 100)"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress indicator"
    )

    args = parser.parse_args()

    # Load sentences
    loader = CorpusLoader()
    sentences = []

    if args.corpus == "tatoeba":
        print("Loading sentences from Tatoeba corpus...")
        sentences = loader.load_tatoeba(
            limit=args.limit,
            min_length=args.min_length,
            max_length=args.max_length
        )
    elif args.input:
        print(f"Loading sentences from {args.input}...")
        sentences = loader.load_file(args.input)
    elif args.text:
        sentences = loader.load_text(args.text)
    elif args.interactive:
        sentences = loader.load_interactive()

    if args.limit and len(sentences) > args.limit:
        sentences = sentences[:args.limit]

    if not sentences:
        print("No sentences to process!", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(sentences)} sentences")

    # Generate cards
    generator = AnkiGenerator()
    cards = generator.process_sentences(sentences, progress=not args.no_progress)

    if not cards:
        print("No cards generated!", file=sys.stderr)
        sys.exit(1)

    # Export based on file extension
    output_path = Path(args.output)
    suffix = output_path.suffix.lower()

    if suffix == '.csv':
        generator.export_csv(cards, output_path)
    elif suffix == '.html':
        generator.export_html(cards, output_path)
    elif suffix == '.txt':
        generator.export_text(cards, output_path)
    else:  # Default to TSV (Anki format)
        generator.export_tsv(cards, output_path)

    # Show sample for non-HTML formats
    if suffix not in ('.html',):
        print("\nSample card:")
        print(f"  Front: {cards[0].front}")
        import re
        back_sample = re.sub(r'<[^>]+>', '', cards[0].back[:300])
        print(f"  Back: {back_sample}...")


if __name__ == "__main__":
    main()

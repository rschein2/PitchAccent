#!/usr/bin/env python3
"""
Sentence Parser for Japanese Pitch Accent Anki Generator

Extracts sentences from text and identifies content words (nouns, verbs, adjectives)
that need pitch accent annotation.

Now includes:
- Compound noun detection and accent sandhi
- Numeral phrase handling
"""
import re
from dataclasses import dataclass, field
from typing import Optional

import fugashi
import unidic

from compound_accent import CompoundAccentEngine
from numeral_accent import NumeralAccentEngine
from numeral_reading import number_to_reading


@dataclass
class ParsedWord:
    """A parsed word with its morphological information."""
    surface: str
    reading: str  # Hiragana reading
    pos1: str     # Primary POS (動詞, 名詞, 形容詞, etc.)
    pos2: str     # Secondary POS
    lemma: str    # Dictionary form
    aType: str    # Accent type from UniDic
    aConType: str # Combination type
    aModType: str # Modification type
    cType: str    # Conjugation type
    cForm: str    # Conjugation form
    is_content_word: bool = False
    morphemes: list = field(default_factory=list)  # For compound analysis
    is_compound: bool = False      # True if this is a computed compound
    compound_rules: list = field(default_factory=list)  # Rules applied


@dataclass
class ParsedSentence:
    """A parsed sentence with its words."""
    original: str
    words: list[ParsedWord]

    def content_words(self) -> list[ParsedWord]:
        """Return only content words (nouns, verbs, adjectives)."""
        return [w for w in self.words if w.is_content_word]


class SentenceParser:
    """
    Parser for Japanese sentences using fugashi/MeCab with UniDic.

    Identifies content words that need pitch accent annotation:
    - Nouns (名詞) including compounds with sandhi
    - Verbs (動詞)
    - Adjectives (形容詞)
    - Adverbs (副詞)
    - Numerals with counters
    """

    # POS tags for content words
    CONTENT_POS = {"動詞", "名詞", "形容詞", "副詞", "代名詞"}

    # POS tags to skip (particles, punctuation, etc.)
    SKIP_POS = {"助詞", "助動詞", "補助記号", "空白", "記号"}

    # Noun subtypes that are part of noun phrases (NOT skipped anymore)
    NUMERAL_NOUN_TYPES = {"数詞"}
    COUNTER_NOUN_TYPES = {"助数詞"}

    # Suffix types that should attach to nouns
    NOUN_SUFFIX_POS2 = {"名詞的"}

    # POS that can be part of noun compounds
    NOUN_COMPOUND_POS = {"名詞", "接尾辞"}

    def __init__(self, use_compound_rules: bool = True, use_numeral_rules: bool = True):
        self.tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')
        self.use_compound_rules = use_compound_rules
        self.use_numeral_rules = use_numeral_rules

        if use_compound_rules:
            self.compound_engine = CompoundAccentEngine()
        if use_numeral_rules:
            self.numeral_engine = NumeralAccentEngine()

    def parse_sentence(self, sentence: str) -> ParsedSentence:
        """
        Parse a sentence and identify content words.

        Returns a ParsedSentence with all words and their properties.
        """
        words = []
        current_compound = []  # For building verb/adj compounds with auxiliaries

        nodes = list(self.tagger(sentence))
        i = 0

        while i < len(nodes):
            node = nodes[i]
            f = node.feature

            # Get morpheme info
            surface = node.surface
            reading = self._kata_to_hira(f.kana) if hasattr(f, 'kana') and f.kana else surface
            pos1 = f.pos1 if hasattr(f, 'pos1') else ""
            pos2 = f.pos2 if hasattr(f, 'pos2') else ""
            lemma = f.lemma if hasattr(f, 'lemma') else surface
            aType = f.aType if hasattr(f, 'aType') else "*"
            aConType = f.aConType if hasattr(f, 'aConType') else "*"
            aModType = f.aModType if hasattr(f, 'aModType') else "*"
            cType = f.cType if hasattr(f, 'cType') else "*"
            cForm = f.cForm if hasattr(f, 'cForm') else "*"

            # Check if this is a content word
            is_content = self._is_content_word(pos1, pos2)

            # Build morpheme dict for accent computation
            morpheme = {
                "surface": surface,
                "reading": f.kana if hasattr(f, 'kana') and f.kana else surface,
                "pos1": pos1,
                "pos2": pos2,
                "cType": cType,
                "cForm": cForm,
                "aType": aType,
                "aConType": aConType,
                "aModType": aModType,
                "lemma": lemma,
            }

            # Handle noun-like sequences (nouns, numerals, counters, suffixes)
            if pos1 in ("名詞", "代名詞") or pos2 in self.NUMERAL_NOUN_TYPES or pos2 in self.COUNTER_NOUN_TYPES:
                # Collect all consecutive noun-like morphemes
                noun_morphemes = [morpheme]
                j = i + 1

                while j < len(nodes):
                    next_node = nodes[j]
                    next_f = next_node.feature
                    next_pos1 = next_f.pos1 if hasattr(next_f, 'pos1') else ""
                    next_pos2 = next_f.pos2 if hasattr(next_f, 'pos2') else ""

                    # Continue if it's a noun, numeral, counter, or noun suffix
                    is_noun_like = (
                        next_pos1 == "名詞" or
                        next_pos2 in self.NUMERAL_NOUN_TYPES or
                        next_pos2 in self.COUNTER_NOUN_TYPES or
                        (next_pos1 == "接尾辞" and next_pos2 in self.NOUN_SUFFIX_POS2)
                    )

                    if is_noun_like:
                        next_morpheme = {
                            "surface": next_node.surface,
                            "reading": next_f.kana if hasattr(next_f, 'kana') and next_f.kana else next_node.surface,
                            "pos1": next_pos1,
                            "pos2": next_pos2,
                            "cType": next_f.cType if hasattr(next_f, 'cType') else "*",
                            "cForm": next_f.cForm if hasattr(next_f, 'cForm') else "*",
                            "aType": next_f.aType if hasattr(next_f, 'aType') else "*",
                            "aConType": next_f.aConType if hasattr(next_f, 'aConType') else "*",
                            "aModType": next_f.aModType if hasattr(next_f, 'aModType') else "*",
                            "lemma": next_f.lemma if hasattr(next_f, 'lemma') else next_node.surface,
                        }
                        noun_morphemes.append(next_morpheme)
                        j += 1
                    else:
                        break

                # Process the noun sequence
                word = self._process_noun_sequence(noun_morphemes)
                words.append(word)
                i = j
                continue

            # If this is a verb or adjective, collect following auxiliaries
            if pos1 in ("動詞", "形容詞"):
                compound_morphemes = [morpheme]
                compound_surface = surface
                compound_reading = reading
                j = i + 1

                # Collect auxiliaries that attach to this verb/adjective
                while j < len(nodes):
                    next_node = nodes[j]
                    next_f = next_node.feature
                    next_pos1 = next_f.pos1 if hasattr(next_f, 'pos1') else ""
                    next_pos2 = next_f.pos2 if hasattr(next_f, 'pos2') else ""

                    # Include auxiliaries (助動詞) and some particles (助詞-接続助詞 like て)
                    if next_pos1 == "助動詞" or (next_pos1 == "助詞" and next_pos2 == "接続助詞"):
                        next_morpheme = {
                            "surface": next_node.surface,
                            "reading": next_f.kana if hasattr(next_f, 'kana') and next_f.kana else next_node.surface,
                            "pos1": next_pos1,
                            "pos2": next_pos2,
                            "cType": next_f.cType if hasattr(next_f, 'cType') else "*",
                            "cForm": next_f.cForm if hasattr(next_f, 'cForm') else "*",
                            "aType": next_f.aType if hasattr(next_f, 'aType') else "*",
                            "aConType": next_f.aConType if hasattr(next_f, 'aConType') else "*",
                            "aModType": next_f.aModType if hasattr(next_f, 'aModType') else "*",
                            "lemma": next_f.lemma if hasattr(next_f, 'lemma') else next_node.surface,
                        }
                        compound_morphemes.append(next_morpheme)
                        compound_surface += next_node.surface
                        next_reading = self._kata_to_hira(next_f.kana) if hasattr(next_f, 'kana') and next_f.kana else next_node.surface
                        compound_reading += next_reading
                        j += 1
                    else:
                        break

                word = ParsedWord(
                    surface=compound_surface,
                    reading=compound_reading,
                    pos1=pos1,
                    pos2=pos2,
                    lemma=lemma,
                    aType=aType,
                    aConType=aConType,
                    aModType=aModType,
                    cType=cType,
                    cForm=cForm,
                    is_content_word=True,
                    morphemes=compound_morphemes,
                )
                words.append(word)
                i = j
                continue

            # Regular word (noun, etc.)
            word = ParsedWord(
                surface=surface,
                reading=reading,
                pos1=pos1,
                pos2=pos2,
                lemma=lemma,
                aType=aType,
                aConType=aConType,
                aModType=aModType,
                cType=cType,
                cForm=cForm,
                is_content_word=is_content,
                morphemes=[morpheme],
            )
            words.append(word)
            i += 1

        return ParsedSentence(original=sentence, words=words)

    def _process_noun_sequence(self, morphemes: list[dict]) -> ParsedWord:
        """
        Process a sequence of noun-like morphemes.

        Applies compound noun accent sandhi rules and numeral rules as appropriate.
        """
        if not morphemes:
            return ParsedWord("", "", "", "", "", "", "", "", "", "", False, [])

        # Combine surface and reading
        combined_surface = "".join(m["surface"] for m in morphemes)

        # Build reading, converting Arabic numerals to Japanese
        reading_parts = []
        for m in morphemes:
            surface = m["surface"]
            reading = self._kata_to_hira(m["reading"])

            # If this is a numeral (Arabic digits), convert to Japanese reading
            if surface.isdigit():
                try:
                    reading = number_to_reading(int(surface))
                except ValueError:
                    pass  # Keep original reading
            # Also handle readings that are just the Arabic numeral
            elif reading.isdigit():
                try:
                    reading = number_to_reading(int(reading))
                except ValueError:
                    pass

            reading_parts.append(reading)

        combined_reading = "".join(reading_parts)

        # Determine if this is primarily a numeral phrase or noun compound
        has_numeral = any(m["pos2"] in self.NUMERAL_NOUN_TYPES for m in morphemes)
        has_counter = any(m["pos2"] in self.COUNTER_NOUN_TYPES for m in morphemes)

        compound_rules = []
        computed_accent = None

        # If it's a numeral + counter phrase, use numeral rules
        if has_numeral and has_counter and self.use_numeral_rules:
            # Find numeral and counter parts
            numeral_morphemes = [m for m in morphemes if m["pos2"] in self.NUMERAL_NOUN_TYPES]
            counter_morphemes = [m for m in morphemes if m["pos2"] in self.COUNTER_NOUN_TYPES]

            if counter_morphemes:
                merged = self.numeral_engine.process_numeral_phrase(
                    numeral_morphemes,
                    counter_morphemes[0]
                )
                computed_accent = merged.get("aType", "0")
                if "_numeral_rule" in merged:
                    compound_rules.append(f"numeral: {merged['_numeral_rule']}")

        # If it's multiple nouns (compound), use compound rules
        elif len(morphemes) > 1 and self.use_compound_rules:
            merged = self.compound_engine.process_noun_sequence(morphemes)
            computed_accent = merged.get("aType", morphemes[0].get("aType", "0"))
            if "_compound_rules" in merged:
                compound_rules.extend(merged["_compound_rules"])

        # Single noun - use its own accent
        else:
            computed_accent = morphemes[0].get("aType", "0")

        # Handle comma in aType (multiple options - take first)
        if computed_accent and "," in str(computed_accent):
            computed_accent = str(computed_accent).split(",")[0]

        first = morphemes[0]
        return ParsedWord(
            surface=combined_surface,
            reading=combined_reading,
            pos1=first.get("pos1", "名詞"),
            pos2="複合" if len(morphemes) > 1 else first.get("pos2", ""),
            lemma=combined_surface,
            aType=str(computed_accent) if computed_accent else "0",
            aConType=first.get("aConType", "*"),
            aModType=first.get("aModType", "*"),
            cType=first.get("cType", "*"),
            cForm=first.get("cForm", "*"),
            is_content_word=True,
            morphemes=morphemes,
            is_compound=len(morphemes) > 1,
            compound_rules=compound_rules,
        )

    def _is_content_word(self, pos1: str, pos2: str) -> bool:
        """Check if a word is a content word based on POS."""
        if pos1 in self.SKIP_POS:
            return False
        # Numerals and counters are now content words (handled specially)
        if pos2 in self.NUMERAL_NOUN_TYPES or pos2 in self.COUNTER_NOUN_TYPES:
            return True
        if pos1 in self.CONTENT_POS:
            return True
        return False

    def _kata_to_hira(self, text: str) -> str:
        """Convert katakana to hiragana."""
        result = []
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)

    def extract_sentences(self, text: str) -> list[str]:
        """
        Extract individual sentences from text.

        Splits on Japanese sentence-ending punctuation.
        """
        # Split on Japanese sentence endings
        sentences = re.split(r'([。！？\n]+)', text)

        result = []
        current = ""

        for part in sentences:
            if re.match(r'^[。！？\n]+$', part):
                if current:
                    result.append(current + part.rstrip('\n'))
                    current = ""
            else:
                current += part

        if current.strip():
            result.append(current.strip())

        # Clean up and filter
        result = [s.strip() for s in result if s.strip()]
        return result


def main():
    """Test the sentence parser with compound nouns and numerals."""
    parser = SentenceParser()

    test_sentences = [
        # Basic sentences
        "彼女は毎日図書館で本を読んでいる。",
        "今日は天気がいいですね。",
        # Compound nouns
        "安全保障面では重要です。",
        "日米関係は緊密です。",
        # Numerals
        "1952年に条約が発効した。",
        "約6万人の米軍部隊がいる。",
        "3本のペンがある。",
    ]

    for sentence in test_sentences:
        print(f"\n{'='*60}")
        print(f"Sentence: {sentence}")
        print(f"{'='*60}")

        parsed = parser.parse_sentence(sentence)

        print("\nAll words:")
        for word in parsed.words:
            marker = "✓" if word.is_content_word else " "
            compound = " [COMPOUND]" if word.is_compound else ""
            print(f"  {marker} {word.surface} [{word.reading}] - {word.pos1}/{word.pos2} aType={word.aType}{compound}")
            if word.compound_rules:
                for rule in word.compound_rules:
                    print(f"      → {rule}")

        print("\nContent words:")
        for word in parsed.content_words():
            print(f"  {word.surface} [{word.reading}] aType=[{word.aType}]")
            if len(word.morphemes) > 1:
                print(f"    Morphemes: {[m['surface'] for m in word.morphemes]}")


if __name__ == "__main__":
    main()

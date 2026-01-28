"""
Japanese Pitch Accent Library

Core components for computing and formatting Japanese pitch accent patterns.
"""

from .engine import AccentEngine, FugashiAccentEngine, AccentResult
from .compound import CompoundAccentEngine, compute_compound_accent
from .numeral import NumeralAccentEngine, compute_numeral_phrase_accent
from .numeral_reading import number_to_reading
from .parser import SentenceParser, ParsedWord, ParsedSentence
from .formatter import HTMLFormatter
from .corpus import CorpusLoader, TextFileLoader, InteractiveLoader

__version__ = "0.1.0"

__all__ = [
    # Engine
    "AccentEngine",
    "FugashiAccentEngine",
    "AccentResult",
    # Compound
    "CompoundAccentEngine",
    "compute_compound_accent",
    # Numeral
    "NumeralAccentEngine",
    "compute_numeral_phrase_accent",
    "number_to_reading",
    # Parser
    "SentenceParser",
    "ParsedWord",
    "ParsedSentence",
    # Formatter
    "HTMLFormatter",
    # Corpus
    "CorpusLoader",
    "TextFileLoader",
    "InteractiveLoader",
]

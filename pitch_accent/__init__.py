"""
Japanese Pitch Accent Library

Core components for computing and formatting Japanese pitch accent patterns.

Note: Heavy components (FugashiAccentEngine, SentenceParser, etc.) that require
UniDic/fugashi are lazily imported. Import them explicitly when needed:

    from pitch_accent import SentenceParser, FugashiAccentEngine

Lightweight utilities can be imported without triggering UniDic:

    from pitch_accent.utils import accent_to_pattern, pattern_to_contour
"""

__version__ = "0.1.0"

# Lightweight utilities (no UniDic dependency)
from .utils import accent_to_pattern, pattern_to_contour, count_mora

# Re-export lightweight utilities
__all__ = [
    # Lightweight utilities
    "accent_to_pattern",
    "pattern_to_contour",
    "count_mora",
    # Heavy components (lazily loaded when accessed)
    "AccentEngine",
    "FugashiAccentEngine",
    "AccentResult",
    "CompoundAccentEngine",
    "compute_compound_accent",
    "NumeralAccentEngine",
    "compute_numeral_phrase_accent",
    "number_to_reading",
    "SentenceParser",
    "ParsedWord",
    "ParsedSentence",
    "HTMLFormatter",
    "CorpusLoader",
    "TextFileLoader",
    "InteractiveLoader",
    "VerbConjugator",
    "ConjugatedForm",
    "AccentGroup",
]


def __getattr__(name):
    """Lazy loading of heavy components that require UniDic."""
    if name in ("AccentEngine", "FugashiAccentEngine", "AccentResult"):
        from .engine import AccentEngine, FugashiAccentEngine, AccentResult
        return {"AccentEngine": AccentEngine, "FugashiAccentEngine": FugashiAccentEngine,
                "AccentResult": AccentResult}[name]
    elif name in ("CompoundAccentEngine", "compute_compound_accent"):
        from .compound import CompoundAccentEngine, compute_compound_accent
        return {"CompoundAccentEngine": CompoundAccentEngine,
                "compute_compound_accent": compute_compound_accent}[name]
    elif name in ("NumeralAccentEngine", "compute_numeral_phrase_accent"):
        from .numeral import NumeralAccentEngine, compute_numeral_phrase_accent
        return {"NumeralAccentEngine": NumeralAccentEngine,
                "compute_numeral_phrase_accent": compute_numeral_phrase_accent}[name]
    elif name == "number_to_reading":
        from .numeral_reading import number_to_reading
        return number_to_reading
    elif name in ("SentenceParser", "ParsedWord", "ParsedSentence"):
        from .parser import SentenceParser, ParsedWord, ParsedSentence
        return {"SentenceParser": SentenceParser, "ParsedWord": ParsedWord,
                "ParsedSentence": ParsedSentence}[name]
    elif name == "HTMLFormatter":
        from .formatter import HTMLFormatter
        return HTMLFormatter
    elif name in ("CorpusLoader", "TextFileLoader", "InteractiveLoader"):
        from .corpus import CorpusLoader, TextFileLoader, InteractiveLoader
        return {"CorpusLoader": CorpusLoader, "TextFileLoader": TextFileLoader,
                "InteractiveLoader": InteractiveLoader}[name]
    elif name in ("VerbConjugator", "ConjugatedForm", "AccentGroup"):
        from .verb_conjugator import VerbConjugator, ConjugatedForm, AccentGroup
        return {"VerbConjugator": VerbConjugator, "ConjugatedForm": ConjugatedForm,
                "AccentGroup": AccentGroup}[name]
    raise AttributeError(f"module 'pitch_accent' has no attribute {name!r}")

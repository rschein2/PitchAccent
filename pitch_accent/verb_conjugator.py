#!/usr/bin/env python3
"""
Verb Conjugation Engine for Pitch Accent Analysis

Conjugates verbs across all forms and groups them by accent pattern behavior
using UniDic's F-type rules.

This module generates conjugated forms and then parses them with UniDic to get
the actual aConType/aModType values, ensuring accurate accent computation.

UniDic Accent Combination System:
- aType: Base accent type (0=heiban, n=drop after nth mora)
- aModType: Modification applied to stems (e.g., M4@1 subtracts 1 from accent)
- aConType: Combination rule for suffixes (e.g., F3@0)

F-Rule Definitions (from UniDic):
- F1: M2 = M1 (preserve preceding accent)
- F2@M: If M1=0 then M2=N1+M, else M2=M1 (heiban gains accent, accented preserves)
- F3@M: If M1=0 then M2=0, else M2=N1+M (heiban stays flat, accented shifts)
- F4@M: M2 = N1+M (always shift)
- F5: M2 = 0 (always heiban)
- F6@M@L: If M1=0 then M2=N1+M, else M2=N1+L

Where:
- M1 = accent type of preceding element (after aModType applied)
- N1 = mora count of preceding element
- M2 = resulting accent type
- M, L = parameters from aConType

M-Type Modifications:
- M1@n: Set accent to n (used for volitional よう)
- M4@n: Subtract n from accent position (used for shortened stems)
"""
from dataclasses import dataclass, field
from typing import Optional
import re
import fugashi
import unidic

from .engine import AccentEngine, AccentResult
from .utils import count_mora, kata_to_hira


@dataclass
class ConjugatedForm:
    """A conjugated verb form with accent information."""
    form_name: str          # e.g., "te-form", "masu-form"
    surface: str            # e.g., "食べて"
    reading: str            # e.g., "たべて"
    accent_type: int        # e.g., 1
    pattern: str            # e.g., "HLL"
    f_rule: str             # e.g., "F1"
    group: str              # e.g., "A"


@dataclass
class AccentGroup:
    """A group of conjugations with similar accent behavior."""
    name: str               # e.g., "Group A: Accent Preserved"
    description: str        # e.g., "F1 rule - preserves base accent"
    f_rule: str             # e.g., "F1"
    representative: ConjugatedForm  # Main form to display
    other_forms: list[ConjugatedForm] = field(default_factory=list)
    example_sentence: str = ""  # LLM-generated sentence


# Godan verb conjugation endings by row
GODAN_CONJUGATIONS = {
    "カ行": {
        "te": ("い", "て"),
        "ta": ("い", "た"),
        "nai": ("か", "ない"),
        "masu": ("き", "ます"),
        "tai": ("き", "たい"),
        "you": ("こ", "う"),
        "ba": ("け", "ば"),
        "potential": ("け", "る"),
    },
    "ガ行": {
        "te": ("い", "で"),
        "ta": ("い", "だ"),
        "nai": ("が", "ない"),
        "masu": ("ぎ", "ます"),
        "tai": ("ぎ", "たい"),
        "you": ("ご", "う"),
        "ba": ("げ", "ば"),
        "potential": ("げ", "る"),
    },
    "サ行": {
        "te": ("し", "て"),
        "ta": ("し", "た"),
        "nai": ("さ", "ない"),
        "masu": ("し", "ます"),
        "tai": ("し", "たい"),
        "you": ("そ", "う"),
        "ba": ("せ", "ば"),
        "potential": ("せ", "る"),
    },
    "タ行": {
        "te": ("っ", "て"),
        "ta": ("っ", "た"),
        "nai": ("た", "ない"),
        "masu": ("ち", "ます"),
        "tai": ("ち", "たい"),
        "you": ("と", "う"),
        "ba": ("て", "ば"),
        "potential": ("て", "る"),
    },
    "ナ行": {
        "te": ("ん", "で"),
        "ta": ("ん", "だ"),
        "nai": ("な", "ない"),
        "masu": ("に", "ます"),
        "tai": ("に", "たい"),
        "you": ("の", "う"),
        "ba": ("ね", "ば"),
        "potential": ("ね", "る"),
    },
    "バ行": {
        "te": ("ん", "で"),
        "ta": ("ん", "だ"),
        "nai": ("ば", "ない"),
        "masu": ("び", "ます"),
        "tai": ("び", "たい"),
        "you": ("ぼ", "う"),
        "ba": ("べ", "ば"),
        "potential": ("べ", "る"),
    },
    "マ行": {
        "te": ("ん", "で"),
        "ta": ("ん", "だ"),
        "nai": ("ま", "ない"),
        "masu": ("み", "ます"),
        "tai": ("み", "たい"),
        "you": ("も", "う"),
        "ba": ("め", "ば"),
        "potential": ("め", "る"),
    },
    "ラ行": {
        "te": ("っ", "て"),
        "ta": ("っ", "た"),
        "nai": ("ら", "ない"),
        "masu": ("り", "ます"),
        "tai": ("り", "たい"),
        "you": ("ろ", "う"),
        "ba": ("れ", "ば"),
        "potential": ("れ", "る"),
    },
    "ワ行": {
        "te": ("っ", "て"),
        "ta": ("っ", "た"),
        "nai": ("わ", "ない"),
        "masu": ("い", "ます"),
        "tai": ("い", "たい"),
        "you": ("お", "う"),
        "ba": ("え", "ば"),
        "potential": ("え", "る"),
    },
}

# Ichidan verb conjugations (drop る, add suffix)
ICHIDAN_CONJUGATIONS = {
    "te": "て",
    "ta": "た",
    "nai": "ない",
    "masu": "ます",
    "tai": "たい",
    "you": "よう",
    "ba": "れば",
    "potential": "られる",
}

# Irregular verb surface forms (in kanji for parsing)
IRREGULAR_SURU_SURFACE = {
    "te": "して",
    "ta": "した",
    "nai": "しない",
    "masu": "します",
    "tai": "したい",
    "you": "しよう",
    "ba": "すれば",
    "potential": "できる",
}

IRREGULAR_KURU_SURFACE = {
    "te": "来て",
    "ta": "来た",
    "nai": "来ない",
    "masu": "来ます",
    "tai": "来たい",
    "you": "来よう",
    "ba": "来れば",
    "potential": "来られる",
}

# Special case: 行く has irregular te/ta forms
IRREGULAR_IKU = {
    "te": "行って",
    "ta": "行った",
}

# Form groupings by accent behavior pattern
FORM_GROUPS = {
    "te": {"group": "A", "group_name": "Accent Preserved"},
    "ta": {"group": "B", "group_name": "Past/Conditional"},
    "nai": {"group": "C", "group_name": "Negative/Potential"},
    "masu": {"group": "D", "group_name": "Polite/Desiderative"},
    "tai": {"group": "D", "group_name": "Polite/Desiderative"},
    "you": {"group": "E", "group_name": "Volitional"},
    "ba": {"group": "B", "group_name": "Past/Conditional"},
    "potential": {"group": "C", "group_name": "Negative/Potential"},
}

FORM_DISPLAY_NAMES = {
    "te": "te-form",
    "ta": "ta-form",
    "nai": "nai-form",
    "masu": "masu-form",
    "tai": "tai-form",
    "you": "volitional",
    "ba": "ba-form",
    "potential": "potential",
}


class VerbConjugator:
    """
    Conjugates verbs and computes accent using UniDic's actual F-rules.

    Instead of reimplementing F-rules, this class:
    1. Generates conjugated surface forms using conjugation tables
    2. Parses them with UniDic to get actual aType/aConType/aModType
    3. Uses AccentEngine to compute the correct accent
    """

    def __init__(self):
        self.tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')
        self.accent_engine = AccentEngine()

    def count_mora(self, reading: str) -> int:
        """Count mora in a reading (delegates to utils.count_mora)."""
        return count_mora(reading)

    def detect_verb_type(self, verb_text: str) -> Optional[dict]:
        """
        Detect verb type from UniDic parsing.
        """
        nodes = list(self.tagger(verb_text))
        if not nodes:
            return None

        verb_node = None
        for node in nodes:
            if hasattr(node.feature, 'pos1') and node.feature.pos1 == "動詞":
                verb_node = node
                break

        if not verb_node:
            return None

        f = verb_node.feature
        ctype = f.cType if hasattr(f, 'cType') else ""

        reading = self._kata_to_hira(f.kana) if hasattr(f, 'kana') else verb_node.surface
        lemma = f.lemma if hasattr(f, 'lemma') else verb_node.surface

        atype = f.aType if hasattr(f, 'aType') else "0"
        if atype and atype != "*":
            base_accent = int(atype.split(",")[0])
        else:
            base_accent = 0

        result = {
            "lemma": lemma,
            "reading": reading,
            "base_accent": base_accent,
            "surface": verb_node.surface,
        }

        if "五段" in ctype:
            parts = ctype.split("-")
            row = parts[1] if len(parts) > 1 else ""
            if lemma == "行く":
                result["is_iku"] = True
            result["verb_type"] = "godan"
            result["row"] = row
            result["stem"] = reading[:-1] if reading else ""
            result["kanji_stem"] = verb_node.surface[:-1] if verb_node.surface else ""

        elif "一段" in ctype:
            result["verb_type"] = "ichidan"
            result["row"] = None
            result["stem"] = reading[:-1] if reading.endswith("る") else reading
            result["kanji_stem"] = verb_node.surface[:-1] if verb_node.surface.endswith("る") else verb_node.surface

        elif "サ行変格" in ctype or "サ変" in ctype:
            result["verb_type"] = "suru"
            result["row"] = None
            result["stem"] = ""
            result["kanji_stem"] = ""

        elif "カ行変格" in ctype or "カ変" in ctype:
            result["verb_type"] = "kuru"
            result["row"] = None
            result["stem"] = ""
            result["kanji_stem"] = ""

        else:
            return None

        return result

    def _generate_conjugated_surface(self, verb_info: dict, form_name: str) -> Optional[str]:
        """Generate the surface form (with kanji) for UniDic parsing."""
        verb_type = verb_info["verb_type"]
        kanji_stem = verb_info.get("kanji_stem", "")

        if verb_type == "godan":
            row = verb_info["row"]

            # Special case for 行く
            if verb_info.get("is_iku") and form_name in IRREGULAR_IKU:
                return IRREGULAR_IKU[form_name]

            if row in GODAN_CONJUGATIONS and form_name in GODAN_CONJUGATIONS[row]:
                stem_change, suffix = GODAN_CONJUGATIONS[row][form_name]
                # Use kanji stem for better UniDic parsing
                return kanji_stem + stem_change + suffix
            return None

        elif verb_type == "ichidan":
            if form_name in ICHIDAN_CONJUGATIONS:
                suffix = ICHIDAN_CONJUGATIONS[form_name]
                return kanji_stem + suffix
            return None

        elif verb_type == "suru":
            return IRREGULAR_SURU_SURFACE.get(form_name)

        elif verb_type == "kuru":
            return IRREGULAR_KURU_SURFACE.get(form_name)

        return None

    def _parse_and_compute_accent(self, surface: str) -> Optional[tuple[str, int, str]]:
        """
        Parse a conjugated form with UniDic and compute its accent.

        Returns (reading, accent_type, f_rule) or None.
        """
        nodes = list(self.tagger(surface))
        if not nodes:
            return None

        # Build morpheme list for accent computation
        morphemes = []
        detected_f_rule = "F1"  # Default

        for node in nodes:
            f = node.feature

            morph = {
                "surface": node.surface,
                "reading": f.kana if hasattr(f, 'kana') and f.kana else node.surface,
                "pos1": f.pos1 if hasattr(f, 'pos1') else "",
                "pos2": f.pos2 if hasattr(f, 'pos2') else "",
                "aType": f.aType if hasattr(f, 'aType') else "*",
                "aConType": f.aConType if hasattr(f, 'aConType') else "*",
                "aModType": f.aModType if hasattr(f, 'aModType') else "*",
            }
            morphemes.append(morph)

            # Extract F-rule from suffix's aConType
            acon = morph["aConType"]
            if acon and acon != "*" and "%" in acon:
                # Parse "動詞%F3@0" -> "F3@0"
                for part in acon.split(","):
                    if "動詞%" in part:
                        rule_part = part.split("%")[1]
                        detected_f_rule = rule_part
                        break

        # Use the existing engine to compute accent
        result = self.accent_engine.compute_accent(morphemes)
        reading = self._kata_to_hira(result.reading)

        return (reading, result.accent_type, detected_f_rule)

    def conjugate_verb(self, verb_info: dict, form_name: str) -> Optional[ConjugatedForm]:
        """
        Generate a specific conjugated form with computed accent.
        """
        # Generate surface form for parsing
        surface = self._generate_conjugated_surface(verb_info, form_name)
        if not surface:
            return None

        # Parse and compute accent using UniDic's actual rules
        result = self._parse_and_compute_accent(surface)
        if not result:
            return None

        reading, accent_type, f_rule = result

        # Get group info
        group_info = FORM_GROUPS.get(form_name, {"group": "A"})
        group = group_info["group"]

        # Generate pattern
        total_mora = self.count_mora(reading)
        pattern = self.accent_engine.accent_to_pattern(accent_type, total_mora, include_particle=False)

        return ConjugatedForm(
            form_name=FORM_DISPLAY_NAMES.get(form_name, form_name),
            surface=reading,  # Use hiragana for display
            reading=reading,
            accent_type=accent_type,
            pattern=pattern,
            f_rule=f_rule,
            group=group,
        )

    def get_all_conjugations(self, verb_text: str) -> Optional[list[ConjugatedForm]]:
        """Get all conjugations for a verb."""
        verb_info = self.detect_verb_type(verb_text)
        if not verb_info:
            return None

        forms = []
        for form_name in FORM_GROUPS.keys():
            conjugated = self.conjugate_verb(verb_info, form_name)
            if conjugated:
                forms.append(conjugated)

        return forms

    def get_accent_groups(self, verb_text: str) -> Optional[list[AccentGroup]]:
        """Get conjugations grouped by accent behavior."""
        verb_info = self.detect_verb_type(verb_text)
        if not verb_info:
            return None

        all_forms = self.get_all_conjugations(verb_text)
        if not all_forms:
            return None

        # Group by F-rule group
        groups_dict = {}
        for form in all_forms:
            group_key = form.group
            if group_key not in groups_dict:
                groups_dict[group_key] = []
            groups_dict[group_key].append(form)

        group_info = {
            "A": ("Accent Preserved", "F1 - preserves base accent"),
            "B": ("Past/Conditional", "F2 - heiban gains accent, accented preserves"),
            "C": ("Negative/Potential", "F3 - heiban stays flat, accented shifts"),
            "D": ("Polite/Desiderative", "F4 - always shifts to stem boundary"),
            "E": ("Volitional", "M1@1 - fixed accent position"),
        }

        accent_groups = []
        for group_key in ["A", "B", "C", "D", "E"]:
            if group_key not in groups_dict:
                continue

            forms = groups_dict[group_key]
            name, description = group_info.get(group_key, ("Unknown", ""))

            accent_groups.append(AccentGroup(
                name=f"Group {group_key}: {name}",
                description=description,
                f_rule=forms[0].f_rule if forms else "",
                representative=forms[0] if forms else None,
                other_forms=forms[1:] if len(forms) > 1 else [],
            ))

        return accent_groups

    def get_verb_info_display(self, verb_text: str) -> Optional[dict]:
        """Get display info for a verb."""
        verb_info = self.detect_verb_type(verb_text)
        if not verb_info:
            return None

        type_names = {
            "godan": "Godan (五段)",
            "ichidan": "Ichidan (一段)",
            "suru": "Suru irregular (サ変)",
            "kuru": "Kuru irregular (カ変)",
        }

        base_mora = self.count_mora(verb_info["reading"])
        base_pattern = self.accent_engine.accent_to_pattern(
            verb_info["base_accent"],
            base_mora,
            include_particle=False
        )

        return {
            "lemma": verb_info["lemma"],
            "reading": verb_info["reading"],
            "verb_type": type_names.get(verb_info["verb_type"], verb_info["verb_type"]),
            "verb_type_raw": verb_info["verb_type"],
            "row": verb_info.get("row"),
            "base_accent": verb_info["base_accent"],
            "base_pattern": base_pattern,
            "is_heiban": verb_info["base_accent"] == 0,
        }

    def _kata_to_hira(self, text: str) -> str:
        """Convert katakana to hiragana (delegates to utils.kata_to_hira)."""
        return kata_to_hira(text)


def main():
    """Test the verb conjugator."""
    conjugator = VerbConjugator()

    test_verbs = [
        "食べる",  # Ichidan, accented [2]
        "起きる",  # Ichidan, accented [2] - key test case
        "行く",    # Godan, heiban [0]
        "書く",    # Godan, accented [1]
        "見る",    # Ichidan, accented [1]
        "する",    # Irregular
        "来る",    # Irregular
    ]

    for verb in test_verbs:
        print(f"\n{'='*60}")
        print(f"Verb: {verb}")
        print(f"{'='*60}")

        info = conjugator.get_verb_info_display(verb)
        if info:
            print(f"Type: {info['verb_type']}")
            print(f"Reading: {info['reading']}")
            print(f"Base accent: [{info['base_accent']}] {info['base_pattern']}")
            print(f"Heiban: {info['is_heiban']}")

        groups = conjugator.get_accent_groups(verb)
        if groups:
            for group in groups:
                print(f"\n--- {group.name} ---")
                print(f"Rule: {group.f_rule}")

                rep = group.representative
                print(f"  {rep.surface} [{rep.accent_type}] {rep.pattern} ({rep.form_name})")

                for other in group.other_forms:
                    print(f"  {other.surface} [{other.accent_type}] {other.pattern} ({other.form_name})")


if __name__ == "__main__":
    main()

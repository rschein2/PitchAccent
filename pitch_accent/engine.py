#!/usr/bin/env python3
"""
Japanese Pitch Accent Computation Engine

Computes pitch accent for conjugated forms using UniDic's F-type combination rules.
"""
import json
import re
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Load extracted rules
RULES_FILE = Path(__file__).parent / "rules.json"


@dataclass
class AccentResult:
    """Result of accent computation."""
    surface: str           # The full conjugated form
    reading: str           # Kana reading
    accent_type: int       # 0=heiban, k=drop after k-th mora
    mora_count: int        # Total mora count
    pattern: str           # L/H pattern like "LHLL"
    breakdown: list        # Step-by-step computation trace

    def __str__(self):
        type_name = {
            0: "平板",
            1: "頭高",
        }.get(self.accent_type, f"{self.accent_type}型")
        return f"{self.surface} [{self.reading}] {self.pattern} ({type_name}, {self.mora_count}拍)"


class AccentEngine:
    """
    Computes pitch accent using UniDic's F-type combination rules.

    The engine applies:
    1. Base word accent (aType)
    2. Inflection modification (aModType)
    3. Suffix combination (aConType with F1-F6 rules)
    """

    # Small kana that don't count as separate mora
    SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮっッ")
    # But っ/ッ DO count as mora for accent purposes
    SOKUON = set("っッ")

    def __init__(self, rules_file: Path = RULES_FILE):
        with open(rules_file, encoding="utf-8") as f:
            data = json.load(f)
        self.suffix_rules = data["suffix_rules"]
        self.verb_patterns = data["verb_inflection_patterns"]

        # Build quick lookup by surface
        self.suffix_by_surface = {}
        for key, rule in self.suffix_rules.items():
            surface = rule["surface"]
            if surface not in self.suffix_by_surface:
                self.suffix_by_surface[surface] = []
            self.suffix_by_surface[surface].append(rule)

    def count_mora(self, reading: str) -> int:
        """Count mora in a reading."""
        count = 0
        for i, char in enumerate(reading):
            # Small kana (except っ) don't count
            if char in self.SMALL_KANA and char not in self.SOKUON:
                continue
            count += 1
        return count

    def accent_to_pattern(self, accent_type: int, mora_count: int,
                          include_particle: bool = True) -> str:
        """
        Convert accent type to L/H pattern.

        Args:
            accent_type: 0=heiban, k=drop after k-th mora
            mora_count: number of mora in the word
            include_particle: if True, add extra mora to show pitch on particle
                              (matches JPDB convention)

        Rules:
        - First mora is L (low) except for 頭高 (type 1)
        - After accent position, pitch drops to L and stays L
        - Type 0 (heiban): LHHH...H (stays high, including particle)
        """
        if mora_count == 0:
            return ""

        # Total positions to generate (word + optional particle)
        total = mora_count + (1 if include_particle else 0)

        if mora_count == 1 and not include_particle:
            return "H" if accent_type == 1 else "L"

        if accent_type == 0:
            # Heiban: LHHH...H (stays high through particle)
            return "L" + "H" * (total - 1)
        elif accent_type == 1:
            # Atamadaka: HLLL...L (drops after first)
            return "H" + "L" * (total - 1)
        else:
            # Nakadaka/Odaka: LHHH...HL...L
            # Rise after first, drop after accent position
            if accent_type > total:
                # Edge case: accent beyond word+particle
                return "L" + "H" * (total - 1)
            else:
                high_count = accent_type - 1  # H's after initial L
                low_count = total - accent_type
                return "L" + "H" * high_count + "L" * low_count

    def apply_f_rule(self, f_type: str, m_val: Optional[int], l_val: Optional[int],
                     prev_accent: int, prev_mora: int) -> int:
        """
        Apply F-type combination rule.

        Args:
            f_type: F1, F2, F3, F4, F5, or F6
            m_val: M parameter (position offset)
            l_val: L parameter (only for F6)
            prev_accent: M1 - accent type of preceding element
            prev_mora: N1 - mora count of preceding element

        Returns:
            New accent type for the combined form
        """
        m = m_val if m_val is not None else 0
        l = l_val if l_val is not None else 0

        if f_type == "F1":
            # Preserve preceding accent
            return prev_accent

        elif f_type == "F2":
            # If heiban -> N1+M, else preserve
            if prev_accent == 0:
                return prev_mora + m
            else:
                return prev_accent

        elif f_type == "F3":
            # If heiban -> stay heiban, else N1+M
            if prev_accent == 0:
                return 0
            else:
                return prev_mora + m

        elif f_type == "F4":
            # Always N1+M
            return prev_mora + m

        elif f_type == "F5":
            # Always heiban
            return 0

        elif f_type == "F6":
            # If heiban -> N1+M, else N1+L
            if prev_accent == 0:
                return prev_mora + m
            else:
                return prev_mora + l

        else:
            # Unknown, preserve
            return prev_accent

    def apply_mod_type(self, mod_type: str, base_accent: int) -> int:
        """
        Apply aModType inflection modification.

        M4@1 means: if accented, subtract 1 from accent position
        M1@1 means: set accent to 1 (?)
        """
        if not mod_type or mod_type == "*":
            return base_accent

        # Parse M-type: M4@1, M1@1, etc.
        match = re.match(r"M(\d+)@(-?\d+)", mod_type)
        if not match:
            return base_accent

        m_type = int(match.group(1))
        m_val = int(match.group(2))

        if m_type == 4:
            # M4@n: Shift accent position by subtracting n (for shortened stems)
            if base_accent == 0:
                return 0  # Heiban stays heiban
            else:
                new_accent = base_accent - m_val
                return max(0, new_accent)  # Don't go below 0

        elif m_type == 1:
            # M1@n: Set accent to n (used for volitional)
            return m_val

        return base_accent

    def compute_accent(self, morphemes: list[dict]) -> AccentResult:
        """
        Compute accent for a sequence of morphemes.

        Each morpheme dict should have:
        - surface: str
        - reading: str (katakana)
        - pos1: str (品詞)
        - aType: str (accent type, or "*")
        - aConType: str (combination type)
        - aModType: str (modification type)

        Returns AccentResult with computed accent.
        """
        if not morphemes:
            return AccentResult("", "", 0, 0, "", [])

        breakdown = []

        # Start with first morpheme (usually the content word)
        first = morphemes[0]

        # Get base accent
        # aType can be "1", "*", or "1,0" (multiple options - take first)
        if first["aType"] and first["aType"] != "*":
            atype_str = first["aType"].split(",")[0]  # Take first if multiple
            current_accent = int(atype_str)
        else:
            current_accent = 0

        # Apply inflection modification if present
        if first.get("aModType") and first["aModType"] != "*":
            orig_accent = current_accent
            current_accent = self.apply_mod_type(first["aModType"], current_accent)
            breakdown.append(f"{first['surface']}: base={orig_accent}, aModType={first['aModType']} → {current_accent}")
        else:
            breakdown.append(f"{first['surface']}: base accent={current_accent}")

        reading = first.get("reading", first["surface"])
        current_mora = self.count_mora(reading)
        surface = first["surface"]

        # Process remaining morphemes (suffixes/particles)
        for morph in morphemes[1:]:
            m_reading = morph.get("reading", morph["surface"])
            m_surface = morph["surface"]
            m_mora = self.count_mora(m_reading)

            # Determine POS category for F-rule lookup
            pos1 = morph.get("pos1", "")
            prev_pos = morphemes[0].get("pos1", "動詞")  # Assume verb if unknown

            # Map to lookup key (動詞, 形容詞, 名詞)
            if "動詞" in prev_pos or prev_pos == "動詞":
                pos_key = "動詞"
            elif "形容詞" in prev_pos:
                pos_key = "形容詞"
            else:
                pos_key = "名詞"

            # Get F-rule from aConType
            acon = morph.get("aConType", "")
            f_rule = self._parse_acon_for_pos(acon, pos_key)

            if f_rule:
                f_type = f_rule["type"]
                m_val = f_rule.get("M")
                l_val = f_rule.get("L")

                prev_accent = current_accent
                current_accent = self.apply_f_rule(f_type, m_val, l_val, current_accent, current_mora)

                rule_str = f_type
                if m_val is not None:
                    rule_str += f"@{m_val}"
                if l_val is not None:
                    rule_str += f",{l_val}"

                breakdown.append(
                    f"+ {m_surface}: {rule_str} (N1={current_mora}, M1={prev_accent}) → accent={current_accent}"
                )
            else:
                breakdown.append(f"+ {m_surface}: no F-rule found, preserving accent={current_accent}")

            # Update totals
            current_mora += m_mora
            reading += m_reading
            surface += m_surface

        # Convert to pattern
        pattern = self.accent_to_pattern(current_accent, current_mora)

        # Convert katakana reading to hiragana for display
        reading_hira = self._kata_to_hira(reading)

        return AccentResult(
            surface=surface,
            reading=reading_hira,
            accent_type=current_accent,
            mora_count=current_mora,
            pattern=pattern,
            breakdown=breakdown,
        )

    def _parse_acon_for_pos(self, acon: str, pos_key: str) -> Optional[dict]:
        """Parse aConType string and extract rule for given POS."""
        if not acon or acon == "*":
            return None

        for part in acon.split(","):
            if "%" not in part:
                continue
            pos, spec = part.split("%", 1)
            if pos == pos_key:
                match = re.match(r"F([1-6])(?:@(-?\d+))?(?:@(-?\d+))?", spec)
                if match:
                    return {
                        "type": f"F{match.group(1)}",
                        "M": int(match.group(2)) if match.group(2) else None,
                        "L": int(match.group(3)) if match.group(3) else None,
                    }
        return None

    def _kata_to_hira(self, text: str) -> str:
        """Convert katakana to hiragana."""
        result = []
        for char in text:
            code = ord(char)
            # Katakana range: 0x30A0-0x30FF -> Hiragana: 0x3040-0x309F
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)


class FugashiAccentEngine(AccentEngine):
    """
    AccentEngine that uses fugashi/MeCab to parse input text.
    """

    def __init__(self, rules_file: Path = RULES_FILE):
        super().__init__(rules_file)

        import fugashi
        import unidic
        self.tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

    def analyze(self, text: str) -> AccentResult:
        """
        Parse text with MeCab and compute accent.
        """
        morphemes = []

        for node in self.tagger(text):
            f = node.feature
            morphemes.append({
                "surface": node.surface,
                "reading": f.kana if hasattr(f, 'kana') else node.surface,
                "pos1": f.pos1,
                "pos2": f.pos2 if hasattr(f, 'pos2') else "*",
                "cType": f.cType if hasattr(f, 'cType') else "*",
                "cForm": f.cForm if hasattr(f, 'cForm') else "*",
                "aType": f.aType if hasattr(f, 'aType') else "*",
                "aConType": f.aConType if hasattr(f, 'aConType') else "*",
                "aModType": f.aModType if hasattr(f, 'aModType') else "*",
            })

        return self.compute_accent(morphemes)

    def analyze_verbose(self, text: str) -> None:
        """Parse and print detailed analysis."""
        print(f"\n{'='*60}")
        print(f"Input: {text}")
        print(f"{'='*60}")

        print("\nMorpheme breakdown:")
        for node in self.tagger(text):
            f = node.feature
            print(f"  {node.surface}: pos={f.pos1}, aType={f.aType}, "
                  f"aConType={f.aConType}, aModType={f.aModType}")

        result = self.analyze(text)

        print("\nAccent computation:")
        for step in result.breakdown:
            print(f"  {step}")

        print(f"\nResult: {result}")
        print(f"Pattern: {result.pattern}")


def main():
    """Test the accent engine."""
    engine = FugashiAccentEngine()

    test_forms = [
        # Ichidan verb conjugations
        "食べる",
        "食べた",
        "食べて",
        "食べない",
        "食べます",
        "食べたい",
        "食べれば",
        "食べられる",
        # Godan verb conjugations
        "書く",
        "書いた",
        "書いて",
        "書かない",
        "書きます",
        "書きたい",
        "書けば",
        "書ける",
        # Heiban verb (行く)
        "行く",
        "行った",
        "行って",
        "行かない",
        "行きます",
        # Short verbs
        "見る",
        "見た",
        "見て",
        "見ない",
        "見ます",
        # Minimal pairs
        "箸",
        "橋",
        "端",
    ]

    print("=" * 70)
    print("PITCH ACCENT ENGINE TEST")
    print("=" * 70)

    for form in test_forms:
        engine.analyze_verbose(form)


if __name__ == "__main__":
    main()

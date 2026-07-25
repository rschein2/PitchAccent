#!/usr/bin/env python3
"""
Japanese Pitch Accent Computation Engine

Computes pitch accent for conjugated forms using UniDic's F-type combination rules.

The rules come directly from UniDic's per-morpheme fields (aType, aConType,
aModType) as returned by MeCab — there is no separate rules file. Known-wrong
UniDic data is corrected in one place: AccentEngine.ACON_OVERRIDES.

Accuracy layering (highest priority first):
1. Whole-word dictionary lookup (Kanjium, ~124k entries) — lexicalized
   accents win over computation (FugashiAccentEngine.analyze).
2. Base-word accent correction — the first morpheme's lemma is looked up
   in the dictionary and its accent replaces UniDic's aType if they
   disagree (compute_accent).
3. Rule-based combination (F/C/M rules) for everything else.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from .utils import (
    count_mora,
    kata_to_hira,
    accent_to_pattern,
    pattern_to_contour,
)


@dataclass
class AccentResult:
    """Result of accent computation."""
    surface: str           # The full conjugated form
    reading: str           # Kana reading
    accent_type: int       # 0=heiban, k=drop after k-th mora
    mora_count: int        # Total mora count
    pattern: str           # L/H pattern like "LHLL"
    breakdown: list        # Step-by-step computation trace
    contour: str = ""      # Pitch contour like "た/べ\る" (/ = rise, \ = fall)
    accent_variants: list = field(default_factory=list)  # All accepted accents
                           # (dictionary variants, primary first; empty if
                           # the word has a single known accent)

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

    # Corrections for UniDic data that yields wrong accents.
    # Keyed by (cType, pos_key) -> parsed rule dict (same shape as
    # _parse_acon_for_pos output). This is the ONLY place such fixes live.
    #
    # 助動詞-タ (た/だ/たら): UniDic ships 動詞%F2@1, which would turn the
    # past tense of every heiban verb odaka (行った→[3]). Standard Tokyo
    # accent (NHK/OJAD) keeps it heiban: 行った[0], 買った[0]. Accented verbs
    # preserve their accent either way, so plain F1 is correct for verbs.
    # (たら still gains an accent on heiban verbs via its own aModType M2@1,
    # which compute_accent applies after combination: 行ったら→[3].)
    ACON_OVERRIDES = {
        ("助動詞-タ", "動詞"): {"type": "F1", "M": None, "L": None},
    }

    def __init__(self, use_dictionary: bool = True):
        """
        Args:
            use_dictionary: consult the Kanjium accent dictionary to correct
                base-word accents (and, in FugashiAccentEngine.analyze, to
                short-circuit whole-word lookups). Falls back gracefully to
                pure rule computation if the data file is absent.
        """
        self.accent_dict = None
        if use_dictionary:
            from .accent_dict import get_accent_dictionary
            self.accent_dict = get_accent_dictionary()

    def count_mora(self, reading: str) -> int:
        """Count mora in a reading (delegates to utils.count_mora)."""
        return count_mora(reading)

    def accent_to_pattern(self, accent_type: int, mora_count: int,
                          include_particle: bool = True) -> str:
        """Convert accent type to L/H pattern (delegates to utils)."""
        return accent_to_pattern(accent_type, mora_count, include_particle)

    def pattern_to_contour(self, reading: str, pattern: str) -> str:
        """Convert reading + L/H pattern to contour (delegates to utils)."""
        return pattern_to_contour(reading, pattern)

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

    def apply_c_rule(self, c_type: str, front_mora: int, front_accent: int, rear_accent: int) -> int:
        """
        Apply C-type compound accent rules (UniDic Table 10).

        C-types determine accent for compounds and adjective combinations.

        Variables:
        - N1 = mora count of front element
        - M1 = accent type of front element
        - M2 = accent type of rear element

        Rules:
        - C1: N1 + M2 (front mora + rear accent)
        - C2: N1 + 1
        - C3: N1 (accent at front element's mora boundary)
        - C4: 0 (heiban)
        - C5: M1 (preserve front element's accent)
        """
        # Parse C-type: C1, C2, C3, C4, C5
        match = re.match(r"C(\d+)", c_type)
        if not match:
            return front_accent  # Unknown, preserve

        c_num = int(match.group(1))

        if c_num == 1:
            # C1: N1 + M2
            if rear_accent == 0:
                return 0  # Rear is heiban, result is heiban
            return front_mora + rear_accent

        elif c_num == 2:
            # C2: N1 + 1
            return front_mora + 1

        elif c_num == 3:
            # C3: N1 (accent at front boundary)
            return front_mora

        elif c_num == 4:
            # C4: 0 (always heiban)
            return 0

        elif c_num == 5:
            # C5: M1 (preserve front accent)
            return front_accent

        else:
            return front_accent

    def apply_mod_type(self, mod_type: str, base_accent: int, mora_count: int = 0) -> int:
        """
        Apply aModType inflection modification.

        From UniDic Table 9:
        - M1@M: Accent = N0 - M (where N0 is mora count of inflected form)
                Used for volitional form.
        - M2@M: Conditional - only modifies heiban words.
                If base accent is 0 (heiban) → N0 - M
                Otherwise → preserve base accent (unchanged)
                Used for adjective inflections like 高かっ.
        - M4@M: For shortened stems (ichidan verb mizenkei, etc.)
                If base accent is 0 or 1, keep it unchanged.
                Otherwise, subtract M from accent position.
        """
        if not mod_type or mod_type == "*":
            return base_accent

        # Parse M-type: M4@1, M1@1, M2@2, etc.
        match = re.match(r"M(\d+)@(-?\d+)", mod_type)
        if not match:
            return base_accent

        m_type = int(match.group(1))
        m_val = int(match.group(2))

        if m_type == 1:
            # M1@M: Accent = N0 - M (mora count based)
            # Used for volitional and other forms where accent position
            # is determined by the inflected form's length.
            if mora_count > 0:
                new_accent = mora_count - m_val
                return max(0, new_accent)
            else:
                # Fallback if no mora count provided
                return m_val

        elif m_type == 2:
            # M2@M: Only modifies heiban (base=0) words.
            # If heiban → N0 - M; otherwise preserve base accent.
            # Used for adjective inflections (高かっ, 高けれ, etc.)
            if base_accent == 0:
                if mora_count > 0:
                    new_accent = mora_count - m_val
                    return max(0, new_accent)
                else:
                    return base_accent
            else:
                return base_accent  # Non-heiban stays unchanged

        elif m_type == 4:
            # M4@M: For shortened stems (e.g., ichidan verbs losing る)
            # UniDic Table 9: If base accent is 0 or 1, preserve it.
            #                 Otherwise, subtract M.
            if base_accent <= 1:
                return base_accent  # 0 stays 0, 1 stays 1
            else:
                new_accent = base_accent - m_val
                return max(1, new_accent)  # Don't go below 1 for accented

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
            return AccentResult("", "", 0, 0, "", [], "")

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

        # Dictionary correction: if the lemma's accent is known (Kanjium)
        # and disagrees with UniDic's aType, trust the dictionary. The
        # combination rules then run from the corrected base.
        dict_variants: list[int] = []
        if self.accent_dict is not None:
            lemma = first.get("lemma")
            if lemma:
                found = self.accent_dict.lookup(lemma, first.get("lemma_reading"))
                if found:
                    dict_variants = found
                    if current_accent != found[0]:
                        breakdown.append(
                            f"{lemma}: dictionary accent {found} overrides aType={current_accent}"
                        )
                        current_accent = found[0]

        reading = first.get("reading", first["surface"])
        current_mora = self.count_mora(reading)

        # Apply inflection modification if present
        if first.get("aModType") and first["aModType"] != "*":
            orig_accent = current_accent
            current_accent = self.apply_mod_type(first["aModType"], current_accent, current_mora)
            breakdown.append(f"{first['surface']}: base={orig_accent}, aModType={first['aModType']}, N0={current_mora} → {current_accent}")
        else:
            breakdown.append(f"{first['surface']}: base accent={current_accent}")

        surface = first["surface"]

        # Track current POS category for F-rule lookup
        # Starts as the base word's POS, but changes when suffixes like たい/ない
        # make the whole thing adjective-like.
        base_pos = morphemes[0].get("pos1", "動詞")
        if "動詞" in base_pos:
            current_pos_key = "動詞"
        elif "形容詞" in base_pos:
            current_pos_key = "形容詞"
        else:
            current_pos_key = "名詞"

        # Process remaining morphemes (suffixes/particles)
        # Track whether the previous morpheme was the connective て/で,
        # which signals that a following verb is an auxiliary (いる/みる/くる...).
        prev_was_te = False

        for morph in morphemes[1:]:
            m_reading = morph.get("reading", morph["surface"])
            m_surface = morph["surface"]
            m_pos1 = morph.get("pos1", "")
            m_pos2 = morph.get("pos2", "")
            m_ctype = morph.get("cType", "") or ""
            m_mod = morph.get("aModType", "*")
            m_mora = self.count_mora(m_reading)
            new_total_mora = current_mora + m_mora

            # Get rear element's accent (for C-type rules and auxiliary verbs)
            # Apply any aModType to the rear element first
            rear_atype = morph.get("aType", "*")
            if rear_atype and rear_atype != "*":
                rear_accent = int(str(rear_atype).split(",")[0])
                rear_mod = m_mod
                if rear_mod and rear_mod != "*":
                    rear_accent = self.apply_mod_type(rear_mod, rear_accent, m_mora)
            else:
                rear_accent = 0

            # Use current POS key for F-rule lookup
            pos_key = current_pos_key

            # Check aConType - could be C-type (compounds) or F-type (suffixes)
            acon = morph.get("aConType", "")
            c_match = re.match(r"C([1-5])", acon)

            if m_pos1 == "動詞" and current_pos_key == "動詞":
                # A verb following a verb phrase is an auxiliary or a compound
                # verb, NOT the rear of a noun compound — its C-type (which
                # describes noun-compound behavior) must not be applied here.
                prev_accent = current_accent
                if prev_was_te:
                    # て + auxiliary (いる/ある/おく/みる/くる/しまう/くれる...):
                    # unaccented auxiliary keeps the te-form accent
                    # (食べている[1], 行っている[0]); accented auxiliary takes
                    # the accent at N1 + M2 (行ってくる[4], 食べてみる[4]).
                    if rear_accent != 0:
                        current_accent = current_mora + rear_accent
                    breakdown.append(
                        f"+ {m_surface}: aux verb after て (M2={rear_accent}) → accent={current_accent}"
                    )
                else:
                    # Renyokei compound verb (食べ+始める, 書き+直す):
                    # accented on V2's penultimate mora → N1 + (mora(V2) - 1).
                    current_accent = current_mora + max(1, m_mora - 1)
                    breakdown.append(
                        f"+ {m_surface}: compound verb (V2 penult) → accent={current_accent}"
                    )
            elif c_match:
                c_type = f"C{c_match.group(1)}"
                prev_accent = current_accent
                current_accent = self.apply_c_rule(c_type, current_mora, current_accent, rear_accent)

                breakdown.append(
                    f"+ {m_surface}: {c_type} (N1={current_mora}, M1={prev_accent}, M2={rear_accent}) → accent={current_accent}"
                )
            else:
                # Look for F-type rules; check the override table first
                # (corrections for known-wrong UniDic data).
                f_rule = self.ACON_OVERRIDES.get((m_ctype, pos_key))
                overridden = f_rule is not None
                if not f_rule:
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
                    if overridden:
                        rule_str += " (override)"

                    breakdown.append(
                        f"+ {m_surface}: {rule_str} (N1={current_mora}, M1={prev_accent}) → accent={current_accent}"
                    )
                else:
                    breakdown.append(f"+ {m_surface}: no rule found (aConType={acon}), preserving accent={current_accent}")

                # Inflected suffixes carry their own aModType, which adjusts
                # the accent of the COMBINED form (N0 = total mora so far):
                # ましょ(う) M1@1 → 食べましょう[4]; られ M4@1 → 食べられて[3];
                # たら M2@1 → 行ったら[3]. Suffixes with their own aType were
                # already adjusted above (rear_accent), so skip those.
                if m_mod and m_mod != "*" and (not rear_atype or rear_atype == "*"):
                    mod_prev = current_accent
                    current_accent = self.apply_mod_type(m_mod, current_accent, new_total_mora)
                    if current_accent != mod_prev:
                        breakdown.append(
                            f"  aModType {m_mod} (N0={new_total_mora}): {mod_prev} → {current_accent}"
                        )

            # Update totals
            current_mora = new_total_mora
            reading += m_reading
            surface += m_surface

            # Update POS key for next suffix based on cType
            # たい and ない make the whole thing adjective-like for subsequent suffixes
            if "タイ" in m_ctype or "ナイ" in m_ctype:
                current_pos_key = "形容詞"
                breakdown.append(f"  (POS becomes 形容詞 after {m_surface})")

            prev_was_te = (m_pos1 == "助詞" and m_pos2 == "接続助詞"
                           and m_surface in ("て", "で"))

        # Convert to pattern
        pattern = self.accent_to_pattern(current_accent, current_mora)

        # Convert katakana reading to hiragana for display
        reading_hira = self._kata_to_hira(reading)

        # Generate pitch contour notation (た/べ\る style)
        contour = self.pattern_to_contour(reading_hira, pattern)

        return AccentResult(
            surface=surface,
            reading=reading_hira,
            accent_type=current_accent,
            mora_count=current_mora,
            pattern=pattern,
            breakdown=breakdown,
            contour=contour,
            # Variants only apply unmodified when nothing combined onto the
            # base word; conjugation may collapse or shift them.
            accent_variants=dict_variants if (len(morphemes) == 1 and len(dict_variants) > 1) else [],
        )

    def _parse_acon_for_pos(self, acon: str, pos_key: str) -> Optional[dict]:
        """Parse aConType string and extract rule for given POS.

        Handles formats like:
        - "動詞%F2@1,形容詞%F4@-2"
        - "動詞%F6@1,-1,形容詞%F2@-2" (F6 with two parameters)
        - "動詞 %F2@1" (with whitespace)

        The tricky part is F6@M,L where the comma is part of the rule,
        not a separator between POS branches. We split on commas that
        start a new POS% chunk, not all commas.
        """
        if not acon or acon == "*":
            return None

        # Split into POS branches, but preserve F6's comma-separated L parameter
        # Strategy: split on comma, then rejoin orphaned parts (those without %)
        raw_parts = acon.split(",")
        parts = []
        for p in raw_parts:
            p = p.strip()
            if "%" in p:
                # New POS branch
                parts.append(p)
            elif parts:
                # Orphaned part (like "-1" from F6@1,-1) - append to previous
                parts[-1] += "," + p

        for part in parts:
            if "%" not in part:
                continue
            pos, spec = part.split("%", 1)
            pos = pos.strip()
            spec = spec.strip()
            if pos == pos_key:
                # Match F-rules: F1, F2@1, F3@0, F4@1, F5, F6@1,-1
                match = re.match(r"F([1-6])(?:@(-?\d+))?(?:,(-?\d+))?", spec)
                if match:
                    return {
                        "type": f"F{match.group(1)}",
                        "M": int(match.group(2)) if match.group(2) else None,
                        "L": int(match.group(3)) if match.group(3) else None,
                    }
        return None

    def _kata_to_hira(self, text: str) -> str:
        """Convert katakana to hiragana (delegates to utils.kata_to_hira)."""
        return kata_to_hira(text)


class FugashiAccentEngine(AccentEngine):
    """
    AccentEngine that uses fugashi/MeCab to parse input text.
    """

    def __init__(self, use_dictionary: bool = True):
        super().__init__(use_dictionary=use_dictionary)
        import fugashi
        import unidic
        self.tagger = fugashi.Tagger(f'-d "{unidic.DICDIR}"')

    def analyze(self, text: str) -> AccentResult:
        """
        Parse text with MeCab and compute accent.

        Lexicalized whole words win: if the input as a whole is in the
        accent dictionary (with the reading MeCab chose), that accent is
        returned directly and no combination rules run. Rules handle
        conjugated forms and unlisted compounds.
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
                "lemma": f.lemma if hasattr(f, 'lemma') else node.surface,
                "lemma_reading": f.lForm if hasattr(f, 'lForm') else None,
            })

        # Whole-word dictionary hit takes priority over rule computation
        if self.accent_dict is not None and morphemes:
            reading_hira = kata_to_hira(
                "".join(m.get("reading") or m["surface"] for m in morphemes)
            )
            variants = self.accent_dict.lookup(text, reading_hira)
            if variants:
                accent = variants[0]
                mora = count_mora(reading_hira)
                pattern = accent_to_pattern(accent, mora)
                return AccentResult(
                    surface=text,
                    reading=reading_hira,
                    accent_type=accent,
                    mora_count=mora,
                    pattern=pattern,
                    breakdown=[f"dictionary: {text} [{reading_hira}] → {variants}"],
                    contour=pattern_to_contour(reading_hira, pattern),
                    accent_variants=variants if len(variants) > 1 else [],
                )

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

#!/usr/bin/env python3
"""
HTML Formatter for Japanese Pitch Accent Anki Cards

Converts pitch accent patterns to color-coded HTML for Anki display.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ColorScheme:
    """Color scheme for pitch visualization."""
    high: str = "red"      # High pitch
    low: str = "blue"      # Low pitch
    drop: str = "orange"   # Where pitch drops (optional highlight)


class HTMLFormatter:
    """
    Formats pitch accent patterns as color-coded HTML.

    Uses the common convention:
    - Blue for low pitch (L)
    - Red for high pitch (H)
    """

    DEFAULT_COLORS = ColorScheme()

    def __init__(self, colors: Optional[ColorScheme] = None):
        self.colors = colors or self.DEFAULT_COLORS

    def format_word(
        self,
        reading: str,
        pattern: str,
        accent_type: int,
        include_number: bool = True
    ) -> str:
        """
        Format a single word with pitch accent coloring.

        Args:
            reading: Hiragana/katakana reading
            pattern: L/H pattern (e.g., "LHL")
            accent_type: Accent number (0=heiban, etc.)
            include_number: Whether to append [n] accent number

        Returns:
            HTML string with colored spans
        """
        if not reading or not pattern:
            if include_number:
                return f"{reading} [{accent_type}]"
            return reading

        # The pattern may include an extra mora for particle position
        # We only color the actual reading characters
        html_parts = []
        mora_index = 0

        for char in reading:
            # Check if this character is a small kana that combines with previous
            if char in "ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ":
                # Small kana - use same color as previous mora
                if html_parts:
                    # Append to previous span's content
                    last_part = html_parts[-1]
                    # Extract color and text from last span
                    if 'style="color:' in last_part:
                        color = last_part.split('color:')[1].split('"')[0]
                        text = last_part.split('>')[1].split('<')[0]
                        html_parts[-1] = f'<span style="color:{color}">{text}{char}</span>'
                    else:
                        html_parts[-1] = last_part[:-7] + char + "</span>"
                else:
                    # Shouldn't happen, but handle gracefully
                    color = self.colors.low
                    html_parts.append(f'<span style="color:{color}">{char}</span>')
                continue

            # Regular mora
            if mora_index < len(pattern):
                pitch = pattern[mora_index]
                color = self.colors.high if pitch == "H" else self.colors.low
            else:
                # Pattern shorter than reading - use low
                color = self.colors.low

            html_parts.append(f'<span style="color:{color}">{char}</span>')
            mora_index += 1

        html = "".join(html_parts)

        if include_number:
            html += f" [{accent_type}]"

        return html

    def format_pattern_only(self, pattern: str) -> str:
        """
        Format just the L/H pattern with colors.

        Returns HTML like: <span style="color:blue">L</span><span style="color:red">HH</span>
        """
        if not pattern:
            return ""

        html_parts = []
        current_pitch = None
        current_chars = ""

        for char in pattern:
            if char == current_pitch:
                current_chars += char
            else:
                if current_chars:
                    color = self.colors.high if current_pitch == "H" else self.colors.low
                    html_parts.append(f'<span style="color:{color}">{current_chars}</span>')
                current_pitch = char
                current_chars = char

        if current_chars:
            color = self.colors.high if current_pitch == "H" else self.colors.low
            html_parts.append(f'<span style="color:{color}">{current_chars}</span>')

        return "".join(html_parts)

    def format_conjugation_line(
        self,
        base_form: str,
        accent_type: int,
        pattern: str,
        conjugations: list[tuple[str, int, str]]  # [(form, accent, pattern), ...]
    ) -> str:
        """
        Format a conjugation drill line.

        Args:
            base_form: Dictionary form (e.g., "読む")
            accent_type: Base accent type
            pattern: Base pattern
            conjugations: List of (conjugated_form, accent, pattern) tuples

        Returns:
            HTML line like: 読む [1] HLL: 読んだ [1] HLLL, 読んで [1] HLLL, ...
        """
        parts = []

        # Base form
        base_html = f"{base_form} [{accent_type}] {pattern}"
        parts.append(base_html)

        # Conjugations
        conj_parts = []
        for form, accent, pat in conjugations:
            conj_parts.append(f"{form} [{accent}] {pat}")

        if conj_parts:
            parts.append(": " + ", ".join(conj_parts))

        return "".join(parts)

    def format_sentence_annotation(
        self,
        words: list[tuple[str, str, int, str]]  # [(surface, reading, accent, pattern), ...]
    ) -> str:
        """
        Format a full sentence annotation.

        Args:
            words: List of (surface, reading, accent_type, pattern) tuples

        Returns:
            HTML with each word on a new line, color-coded
        """
        lines = []
        for surface, reading, accent, pattern in words:
            colored = self.format_word(reading, pattern, accent)
            # Include original surface if different from reading
            if surface != reading:
                lines.append(f"{surface} {colored}")
            else:
                lines.append(colored)

        return "<br>\n".join(lines)

    def format_anki_back(
        self,
        annotated_words: list[tuple[str, str, int, str]],
        conjugation_drills: Optional[list[str]] = None
    ) -> str:
        """
        Format complete Anki card back.

        Args:
            annotated_words: List of (surface, reading, accent, pattern)
            conjugation_drills: Optional list of conjugation drill lines

        Returns:
            Complete HTML for card back
        """
        parts = []

        # Word annotations
        word_html = self.format_sentence_annotation(annotated_words)
        parts.append(word_html)

        # Conjugation drills section
        if conjugation_drills:
            parts.append("<br><br>")
            parts.append('<div style="border-top: 1px solid #ccc; margin-top: 10px; padding-top: 10px;">')
            parts.append("<b>\u2500\u2500 \u6d3b\u7528\u5f62 \u2500\u2500</b><br>")  # ── 活用形 ──
            for drill in conjugation_drills:
                parts.append(drill + "<br>")
            parts.append("</div>")

        return "\n".join(parts)


def main():
    """Test the HTML formatter."""
    formatter = HTMLFormatter()

    # Test single word formatting
    test_words = [
        ("かのじょ", "LHL", 2),
        ("まいにち", "LHHH", 0),
        ("よむ", "HL", 1),
        ("たべる", "LHL", 2),
    ]

    print("=" * 60)
    print("WORD FORMATTING TEST")
    print("=" * 60)

    for reading, pattern, accent in test_words:
        html = formatter.format_word(reading, pattern, accent)
        print(f"{reading} ({pattern}, type {accent}):")
        print(f"  {html}")
        print()

    # Test conjugation line
    print("=" * 60)
    print("CONJUGATION LINE TEST")
    print("=" * 60)

    conj_line = formatter.format_conjugation_line(
        "読む", 1, "HLL",
        [
            ("読んだ", 1, "HLLL"),
            ("読んで", 1, "HLLL"),
            ("読まない", 2, "LHLLL"),
            ("読みます", 3, "LHHLL"),
        ]
    )
    print(conj_line)
    print()

    # Test full annotation
    print("=" * 60)
    print("FULL ANNOTATION TEST")
    print("=" * 60)

    words = [
        ("彼女", "かのじょ", 2, "LHL"),
        ("毎日", "まいにち", 0, "LHHH"),
        ("図書館", "としょかん", 2, "LHLL"),
        ("本", "ほん", 1, "HL"),
        ("読んでいる", "よんでいる", 1, "HLLLL"),
    ]

    back_html = formatter.format_anki_back(
        words,
        ["読む [1] HLL: 読んだ [1] HLLL, 読んで [1] HLLL, 読まない [2] LHLLL"]
    )
    print(back_html)


if __name__ == "__main__":
    main()

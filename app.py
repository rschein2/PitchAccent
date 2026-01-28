#!/usr/bin/env python3
"""
Streamlit Web Interface for Japanese Pitch Accent Tool

Run locally:
    pip install streamlit
    streamlit run app.py

Deploy free on Streamlit Cloud:
    1. Push to GitHub
    2. Go to share.streamlit.io
    3. Connect your repo
    4. Deploy
"""
import streamlit as st
import subprocess
import sys

# Page config
st.set_page_config(
    page_title="Japanese Pitch Accent Tool",
    page_icon="🎵",
    layout="wide"
)

# Download UniDic if not present (required for first run on Streamlit Cloud)
@st.cache_resource
def ensure_unidic():
    """Download UniDic dictionary if not already installed."""
    import os
    try:
        import unidic
        # Check if dictionary files actually exist
        dicdir = unidic.DICDIR
        if not os.path.exists(os.path.join(dicdir, "dicrc")):
            raise FileNotFoundError("UniDic not fully installed")
    except Exception as e:
        st.info(f"Downloading UniDic dictionary (first time only, ~500MB)... This may take a few minutes.")
        result = subprocess.run(
            [sys.executable, "-m", "unidic", "download"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            st.error(f"Failed to download UniDic: {result.stderr}")
            st.stop()

ensure_unidic()

from pitch_accent import SentenceParser, HTMLFormatter, FugashiAccentEngine

# Initialize components (cached for performance)
@st.cache_resource
def load_components():
    return SentenceParser(), HTMLFormatter(), FugashiAccentEngine()

parser, formatter, engine = load_components()


def get_accent_html(word, reading, accent_type, pattern):
    """Generate colored HTML for a word."""
    # Color each mora based on pattern
    html_parts = []
    mora_idx = 0
    i = 0

    SMALL_KANA = set("ぁぃぅぇぉゃゅょゎ")

    while i < len(reading):
        char = reading[i]
        # Check if next char is small kana (combine them)
        mora = char
        if i + 1 < len(reading) and reading[i + 1] in SMALL_KANA:
            mora += reading[i + 1]
            i += 1

        if mora_idx < len(pattern):
            color = "#d73027" if pattern[mora_idx] == "H" else "#4575b4"  # red high, blue low
            html_parts.append(f'<span style="color:{color};font-size:1.3em">{mora}</span>')
            mora_idx += 1
        else:
            html_parts.append(mora)
        i += 1

    return "".join(html_parts)


def process_text(text):
    """Process text and return annotated results."""
    sentences = parser.extract_sentences(text)
    results = []

    for sentence in sentences:
        parsed = parser.parse_sentence(sentence)
        words_data = []

        for word in parsed.content_words():
            if word.is_compound:
                reading = word.reading
                accent_type = int(word.aType) if word.aType and word.aType != "*" else 0
                mora_count = engine.count_mora(reading)
                pattern = engine.accent_to_pattern(accent_type, mora_count)
            else:
                result = engine.compute_accent(word.morphemes)
                reading = result.reading
                accent_type = result.accent_type
                pattern = result.pattern

            words_data.append({
                'surface': word.surface,
                'reading': reading,
                'accent': accent_type,
                'pattern': pattern,
                'pos': word.pos1,
            })

        results.append({
            'sentence': sentence,
            'words': words_data,
        })

    return results


# UI
st.title("🎵 Japanese Pitch Accent Analyzer")
st.markdown("*Enter Japanese text to see pitch accent patterns*")

# Input
text_input = st.text_area(
    "Japanese text:",
    value="今日は天気がいいですね。",
    height=100,
    help="Enter any Japanese text - sentences, paragraphs, or single words"
)

if st.button("Analyze", type="primary") or text_input:
    if text_input.strip():
        results = process_text(text_input)

        for result in results:
            st.markdown("---")

            # Show original sentence
            st.markdown(f"**{result['sentence']}**")

            # Show each word with pitch
            cols = st.columns(min(len(result['words']), 4))

            for i, word in enumerate(result['words']):
                with cols[i % 4]:
                    # Colored reading
                    html = get_accent_html(
                        word['surface'],
                        word['reading'],
                        word['accent'],
                        word['pattern']
                    )

                    st.markdown(
                        f"""
                        <div style="padding:10px;border:1px solid #ddd;border-radius:5px;margin:5px 0;background:#fafafa">
                            <div style="font-size:1.1em;font-weight:bold">{word['surface']}</div>
                            <div>{html}</div>
                            <div style="font-size:0.9em;color:#666">
                                [{word['accent']}] {word['pattern'][:len(word['pattern'])-1]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# Legend
with st.expander("How to read pitch patterns"):
    st.markdown("""
    ### Pitch Pattern Legend

    - **<span style="color:#d73027">Red</span>** = High pitch (H)
    - **<span style="color:#4575b4">Blue</span>** = Low pitch (L)

    ### Accent Types

    | Type | Name | Pattern | Example |
    |------|------|---------|---------|
    | [0] | 平板 (heiban) | LH...H | せんせい LHHH |
    | [1] | 頭高 (atamadaka) | HL...L | あめ HLL (雨) |
    | [2] | 中高 (nakadaka) | LHL...L | あめ LHL (飴) |
    | [n] | 尾高 (odaka) | LH...HL | はな LHL (鼻) |

    The number [n] indicates where the pitch drops: after the nth mora.
    [0] means no drop (stays high through particles).
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "*Data from [UniDic](https://clrd.ninjal.ac.jp/unidic/) (NINJAL). "
    "Compound accent ~80-90% accurate. "
    "[GitHub](https://github.com/rschein2/PitchAccent)*"
)

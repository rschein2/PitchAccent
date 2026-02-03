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
import base64
import json
import random
from datetime import datetime
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Japanese Pitch Accent Tool",
    page_icon="🎵",
    layout="wide"
)

# Custom CSS for visual polish
st.markdown("""
<style>
/* Card styling with subtle shadows */
.word-card {
    padding: 12px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin: 6px 0;
    background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    transition: transform 0.2s, box-shadow 0.2s;
}
.word-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.word-surface {
    font-size: 1.2em;
    font-weight: bold;
    color: #333;
    margin-bottom: 4px;
}
.accent-info {
    font-size: 0.85em;
    color: #666;
    margin-top: 4px;
    padding-top: 4px;
    border-top: 1px solid #eee;
}
.accent-type-name {
    font-weight: 500;
    color: #555;
}
/* Inline sentence styling */
.inline-sentence {
    font-size: 1.4em;
    line-height: 2;
    padding: 16px;
    background: #f8f9fa;
    border-radius: 8px;
    margin: 10px 0;
}
/* History item styling */
.history-item {
    padding: 8px 12px;
    border-radius: 4px;
    background: #f0f2f6;
    margin: 4px 0;
    cursor: pointer;
    font-size: 0.9em;
}
/* Mobile responsive improvements */
@media (max-width: 768px) {
    .word-card {
        padding: 10px;
        margin: 4px 0;
    }
    .inline-sentence {
        font-size: 1.2em;
        padding: 12px;
    }
}
/* Verb conjugation view styles */
.verb-group {
    padding: 16px;
    border: 1px solid #ddd;
    border-radius: 8px;
    margin: 12px 0;
    background: linear-gradient(135deg, #fafbfc 0%, #f5f6f7 100%);
}
.verb-group-header {
    font-size: 1.1em;
    font-weight: bold;
    color: #333;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 2px solid #4575b4;
}
.verb-form-main {
    font-size: 1.3em;
    margin: 10px 0;
}
.verb-form-accent {
    font-size: 0.9em;
    color: #666;
    margin: 4px 0;
}
.verb-example-sentence {
    font-style: italic;
    color: #555;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 4px;
    margin: 8px 0;
    border-left: 3px solid #4575b4;
}
.verb-other-forms {
    font-size: 0.85em;
    color: #888;
    margin-top: 8px;
}
.verb-info-box {
    background: #e8f4fd;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
}
/* Minimal pairs drill styles */
.drill-card {
    padding: 20px;
    border: 2px solid #ddd;
    border-radius: 12px;
    margin: 10px 0;
    background: #fafafa;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
}
.drill-card:hover {
    border-color: #4575b4;
    transform: scale(1.02);
}
.drill-card-correct {
    border-color: #2e7d32 !important;
    background: #e8f5e9 !important;
}
.drill-card-incorrect {
    border-color: #c62828 !important;
    background: #ffebee !important;
}
.drill-reading {
    font-size: 2em;
    margin-bottom: 15px;
    color: #333;
}
.drill-word {
    font-size: 1.5em;
    margin: 8px 0;
}
.drill-accent-pattern {
    font-size: 1.2em;
    margin-top: 10px;
}
.drill-stats {
    padding: 15px;
    background: #f0f2f6;
    border-radius: 8px;
    margin-bottom: 20px;
}
/* Accent filter styles */
.filter-chip {
    display: inline-block;
    padding: 6px 12px;
    margin: 3px;
    border-radius: 20px;
    font-size: 0.9em;
    cursor: pointer;
}
.filter-chip-heiban { background: #e3f2fd; color: #1565c0; }
.filter-chip-atamadaka { background: #fce4ec; color: #c2185b; }
.filter-chip-nakadaka { background: #fff3e0; color: #ef6c00; }
.filter-chip-odaka { background: #e8f5e9; color: #2e7d32; }
/* Word family styles */
.family-tree {
    padding: 15px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin: 10px 0;
    background: #fafbfc;
}
.family-header {
    font-size: 1.1em;
    font-weight: bold;
    margin-bottom: 10px;
    color: #333;
    border-bottom: 2px solid #4575b4;
    padding-bottom: 5px;
}
.family-member {
    display: inline-block;
    padding: 8px 12px;
    margin: 4px;
    border-radius: 6px;
    background: white;
    border: 1px solid #ddd;
}
</style>
""", unsafe_allow_html=True)

# Example texts for different levels
EXAMPLE_TEXTS = {
    "-- Select an example --": "",
    "Beginner (N5): Weather": "今日は天気がいいですね。",
    "Beginner (N5): Self-intro": "私は学生です。日本語を勉強しています。",
    "Intermediate (N3): Daily life": "毎朝六時に起きて、朝ご飯を食べてから会社に行きます。",
    "Intermediate (N3): Travel": "来週、京都に旅行に行く予定です。お寺を見たいです。",
    "Advanced (N2): Opinion": "環境問題について、私たちはもっと真剣に考えるべきだと思います。",
    "Advanced (N1): Abstract": "言語習得における音声の役割は、しばしば過小評価されがちである。",
    "Minimal pairs: Rain/Candy": "雨が降っています。飴を食べます。",
    "Minimal pairs: Bridge/Chopsticks": "橋を渡ります。箸を使います。",
    "Minimal pairs: Flower/Nose": "花が咲いています。鼻が高いです。",
}

# Load minimal pairs data
@st.cache_data
def load_minimal_pairs():
    """Load minimal pairs from JSON file."""
    pairs_file = Path(__file__).parent / "data" / "minimal_pairs.json"
    if pairs_file.exists():
        with open(pairs_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("pairs", [])
    return []

MINIMAL_PAIRS = load_minimal_pairs()

# Accent type names mapping
ACCENT_TYPE_NAMES = {
    0: ("平板", "heiban", "flat"),
    1: ("頭高", "atamadaka", "head-high"),
    # For types 2+, we determine dynamically based on mora count
}

def get_accent_type_name(accent_type, mora_count):
    """Get the Japanese name for an accent type."""
    if accent_type == 0:
        return "平板 heiban"
    elif accent_type == 1:
        return "頭高 atamadaka"
    elif accent_type == mora_count:
        return "尾高 odaka"
    else:
        return "中高 nakadaka"

# Import lightweight utilities (no UniDic dependency)
from pitch_accent.utils import accent_to_pattern, pattern_to_contour, count_mora

# Lazy-load heavy components that require UniDic
_parser = None
_formatter = None
_engine = None
_verb_conjugator = None


def ensure_unidic():
    """Download UniDic dictionary if not already installed."""
    import os
    try:
        import unidic
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


def get_heavy_components():
    """Lazy-load heavy components that require UniDic."""
    global _parser, _formatter, _engine, _verb_conjugator

    if _parser is None:
        ensure_unidic()
        from pitch_accent import SentenceParser, HTMLFormatter, FugashiAccentEngine, VerbConjugator
        _parser = SentenceParser()
        _formatter = HTMLFormatter()
        _engine = FugashiAccentEngine()
        _verb_conjugator = VerbConjugator()

    return _parser, _formatter, _engine, _verb_conjugator

# LiteLLM for LLM-generated example sentences
import os
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Lazy load LiteLLM only when needed
_litellm_client = None

def get_llm_client():
    """Lazily initialize LiteLLM client."""
    global _litellm_client

    if not OPENAI_API_KEY:
        return None

    if _litellm_client is None:
        try:
            import litellm
            litellm.api_key = OPENAI_API_KEY
            _litellm_client = litellm
        except Exception as e:
            return None

    return _litellm_client


def generate_sentence_with_llm(verb_form: str, verb_meaning: str) -> str:
    """Generate an example sentence using LLM."""
    client = get_llm_client()
    if not client:
        return ""

    try:
        response = client.completion(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Generate a single natural Japanese sentence using the verb form '{verb_form}' ({verb_meaning}). The sentence should be 10-15 words, natural and useful for language learning. Output ONLY the Japanese sentence, nothing else."
            }],
            max_tokens=100,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return ""



SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")

def get_accent_html(word, reading, accent_type, pattern, inline=False):
    """Generate colored HTML for a word."""
    # Color each mora based on pattern
    html_parts = []
    mora_idx = 0
    i = 0

    font_size = "1.3em" if not inline else "inherit"

    while i < len(reading):
        char = reading[i]
        # Check if next char is small kana (combine them)
        mora = char
        if i + 1 < len(reading) and reading[i + 1] in SMALL_KANA:
            mora += reading[i + 1]
            i += 1

        if mora_idx < len(pattern):
            color = "#d73027" if pattern[mora_idx] == "H" else "#4575b4"  # red high, blue low
            html_parts.append(f'<span style="color:{color};font-size:{font_size}">{mora}</span>')
            mora_idx += 1
        else:
            html_parts.append(mora)
        i += 1

    return "".join(html_parts)


def generate_html_download(results, original_text):
    """Generate a standalone HTML file with colored pitch accent output."""
    words_html = []
    for result in results:
        words_html.append(f"<h3>{result['sentence']}</h3>")
        words_html.append('<div style="display:flex;flex-wrap:wrap;gap:10px;">')
        for word in result['words']:
            accent_html = get_accent_html(
                word['surface'], word['reading'], word['accent'], word['pattern']
            )
            mora_count = len([c for i, c in enumerate(word['reading'])
                            if c not in SMALL_KANA or i == 0])
            type_name = get_accent_type_name(word['accent'], mora_count)
            words_html.append(f'''
            <div style="padding:12px;border:1px solid #ddd;border-radius:8px;background:#fafafa;">
                <div style="font-weight:bold;font-size:1.1em;">{word['surface']}</div>
                <div>{accent_html}</div>
                <div style="font-size:0.85em;color:#666;">[{word['accent']}] {type_name}</div>
            </div>
            ''')
        words_html.append('</div>')

    html_content = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pitch Accent Analysis</title>
    <style>
        body {{ font-family: "Hiragino Kaku Gothic Pro", "Meiryo", sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h3 {{ color: #555; margin-top: 20px; }}
        .legend {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .legend span {{ margin-right: 20px; }}
    </style>
</head>
<body>
    <h1>Pitch Accent Analysis</h1>
    <div class="legend">
        <span style="color:#d73027;font-weight:bold;">Red = High (H)</span>
        <span style="color:#4575b4;font-weight:bold;">Blue = Low (L)</span>
    </div>
    <div class="original" style="background:#e8f4fd;padding:10px;border-radius:4px;margin-bottom:20px;">
        <strong>Original:</strong> {original_text}
    </div>
    {''.join(words_html)}
    <hr style="margin-top:30px;">
    <p style="color:#888;font-size:0.9em;">Generated by Japanese Pitch Accent Tool</p>
</body>
</html>'''
    return html_content


def generate_anki_tsv(results):
    """Generate TSV for Anki import with colored HTML."""
    lines = []
    for result in results:
        sentence = result['sentence']
        # Create colored reading for each word
        colored_parts = []
        for word in result['words']:
            accent_html = get_accent_html(
                word['surface'], word['reading'], word['accent'], word['pattern']
            )
            colored_parts.append(f"{word['surface']}【{accent_html}】")

        back_content = " ".join(colored_parts)
        # Escape tabs and newlines for TSV
        front = sentence.replace('\t', ' ').replace('\n', ' ')
        back = back_content.replace('\t', ' ').replace('\n', ' ')
        lines.append(f"{front}\t{back}")

    return '\n'.join(lines)


def generate_inline_sentence_html(result):
    """Generate HTML for inline sentence view with all words colored.

    Particles follow the pitch of the preceding word:
    - After heiban [0]: particles stay HIGH (no drop)
    - After odaka [n=mora]: drop happens at boundary, particle is LOW
    - After atamadaka/nakadaka: drop already happened, particle is LOW
    """
    parts = []
    last_content_word = None

    for word in result['all_words']:
        if word['is_content'] and word['pattern']:
            # Content word - show with pitch colors
            accent_html = get_accent_html(
                word['surface'], word['reading'], word['accent'], word['pattern'], inline=True
            )
            parts.append(f'<span title="{word["surface"]} [{word["accent"]}]">{accent_html}</span>')
            last_content_word = word
        else:
            # Particle/function word - pitch depends on preceding word
            if last_content_word is None:
                # No preceding content word, use neutral
                color = "#666"
            elif last_content_word['accent'] == 0:
                # Heiban - particles stay high
                color = "#d73027"  # red = high
            else:
                # Odaka, atamadaka, nakadaka - drop has occurred, particles are low
                color = "#4575b4"  # blue = low

            # Skip coloring punctuation
            if word['pos'] in ('補助記号', '記号'):
                parts.append(f'<span style="color:#999">{word["reading"]}</span>')
            else:
                parts.append(f'<span style="color:{color}">{word["reading"]}</span>')

    return ''.join(parts)


def kata_to_hira(text: str) -> str:
    """Convert katakana to hiragana."""
    result = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return "".join(result)


def process_text(text):
    """Process text and return annotated results."""
    parser, formatter, engine, verb_conjugator = get_heavy_components()

    sentences = parser.extract_sentences(text)
    results = []

    for sentence in sentences:
        parsed = parser.parse_sentence(sentence)
        content_words_data = []
        all_words_data = []

        # Process ALL words for inline view
        for word in parsed.words:
            if word.is_content_word:
                if word.is_compound:
                    reading = word.reading
                    accent_type = int(word.aType) if word.aType and word.aType != "*" else 0
                    mora_cnt = count_mora(reading)
                    pattern = accent_to_pattern(accent_type, mora_cnt)
                    # Convert reading to hiragana for contour
                    reading = kata_to_hira(reading)
                else:
                    result = engine.compute_accent(word.morphemes)
                    reading = result.reading
                    accent_type = result.accent_type
                    pattern = result.pattern

                # Generate contour notation
                contour = pattern_to_contour(reading, pattern)

                word_data = {
                    'surface': word.surface,
                    'reading': reading,
                    'accent': accent_type,
                    'pattern': pattern,
                    'contour': contour,
                    'pos': word.pos1,
                    'is_content': True,
                }
                content_words_data.append(word_data)
                all_words_data.append(word_data)
            else:
                # Non-content words (particles, etc.) - include for inline view
                # Handle punctuation and missing readings
                reading = word.reading
                if not reading or reading == "*":
                    reading = word.surface
                all_words_data.append({
                    'surface': word.surface,
                    'reading': reading,
                    'accent': None,
                    'pattern': None,
                    'pos': word.pos1,
                    'is_content': False,
                })

        results.append({
            'sentence': sentence,
            'words': content_words_data,      # For card view
            'all_words': all_words_data,      # For inline view
        })

    return results


def add_to_history(text):
    """Add text to session history, keeping last 5 items."""
    if 'history' not in st.session_state:
        st.session_state.history = []

    # Don't add duplicates or empty text
    if not text.strip():
        return
    if text in st.session_state.history:
        # Move to front if already exists
        st.session_state.history.remove(text)

    st.session_state.history.insert(0, text)
    # Keep only last 5
    st.session_state.history = st.session_state.history[:5]


def generate_example_sentence(verb_form: str, verb_meaning: str) -> str:
    """Generate an example sentence using LLM, with caching."""
    cache_key = f"{verb_form}:{verb_meaning}"

    # Check cache first
    if cache_key in st.session_state.verb_sentences_cache:
        return st.session_state.verb_sentences_cache[cache_key]

    sentence = generate_sentence_with_llm(verb_form, verb_meaning)
    if sentence:
        # Cache the result
        st.session_state.verb_sentences_cache[cache_key] = sentence

    return sentence


def get_verb_accent_html(reading: str, pattern: str) -> str:
    """Generate colored HTML for a verb conjugation."""
    html_parts = []
    mora_idx = 0
    i = 0

    while i < len(reading):
        char = reading[i]
        mora = char
        if i + 1 < len(reading) and reading[i + 1] in SMALL_KANA:
            mora += reading[i + 1]
            i += 1

        if mora_idx < len(pattern):
            color = "#d73027" if pattern[mora_idx] == "H" else "#4575b4"
            html_parts.append(f'<span style="color:{color};font-size:1.3em">{mora}</span>')
            mora_idx += 1
        else:
            html_parts.append(mora)
        i += 1

    return "".join(html_parts)


# Common English meanings for verbs (used for LLM prompts)
VERB_MEANINGS = {
    "食べる": "to eat",
    "行く": "to go",
    "書く": "to write",
    "見る": "to see/watch",
    "する": "to do",
    "来る": "to come",
    "読む": "to read",
    "聞く": "to listen/ask",
    "話す": "to speak",
    "買う": "to buy",
    "飲む": "to drink",
    "作る": "to make",
    "使う": "to use",
    "待つ": "to wait",
    "走る": "to run",
    "泳ぐ": "to swim",
    "遊ぶ": "to play",
    "死ぬ": "to die",
    "持つ": "to have/hold",
    "思う": "to think",
}


def render_verbs_view(verb_text: str):
    """Render the Verbs conjugation view."""
    parser, formatter, engine, verb_conjugator = get_heavy_components()

    verb_text = verb_text.strip()

    # Try to detect if this is a verb
    verb_info = verb_conjugator.get_verb_info_display(verb_text)

    if not verb_info:
        st.warning(f"Could not detect verb: **{verb_text}**. Please enter a verb in dictionary form (e.g., 食べる, 行く, 書く).")
        st.info("**Tip:** Enter verbs in their dictionary (plain) form ending in -u/-ru.")
        return

    # Show verb info
    st.markdown("---")

    heiban_marker = " (heiban - flat)" if verb_info['is_heiban'] else ""
    base_html = get_verb_accent_html(verb_info['reading'], verb_info['base_pattern'])

    st.markdown(f"""
    <div class="verb-info-box">
        <strong style="font-size:1.4em">{verb_info['lemma']}</strong>
        <span style="margin-left:10px">{base_html}</span>
        <span style="color:#666;margin-left:10px">[{verb_info['base_accent']}]{heiban_marker}</span>
        <br>
        <span style="color:#888;font-size:0.9em">{verb_info['verb_type']}</span>
    </div>
    """, unsafe_allow_html=True)

    # Get accent groups
    accent_groups = verb_conjugator.get_accent_groups(verb_text)

    if not accent_groups:
        st.error("Could not generate conjugations for this verb.")
        return

    # Check for API key for example sentences
    has_api_key = OPENAI_API_KEY is not None
    if not has_api_key:
        st.info("Set OPENAI_API_KEY environment variable to enable LLM-generated example sentences.")

    # Get verb meaning for LLM
    verb_meaning = VERB_MEANINGS.get(verb_info['lemma'], "to do something")

    # Render each accent group
    for group in accent_groups:
        rep = group.representative
        if not rep:
            continue

        # Generate example sentence if API key is available
        example_sentence = ""
        if has_api_key:
            example_sentence = generate_example_sentence(rep.surface, verb_meaning)

        # Colored reading for representative form
        rep_html = get_verb_accent_html(rep.reading, rep.pattern)

        # Build other forms string
        other_forms_str = ""
        if group.other_forms:
            other_names = [f.form_name for f in group.other_forms]
            other_forms_str = f"Also: {', '.join(other_names)}"

        # Accent behavior description based on heiban vs accented
        if verb_info['is_heiban']:
            if group.f_rule == "F1":
                behavior = "stays heiban (flat)"
            elif group.f_rule == "F2":
                behavior = "gains accent (heiban distinguisher)"
            elif group.f_rule == "F3":
                behavior = "stays heiban"
            elif group.f_rule == "F4":
                behavior = "gains accent at stem boundary"
            elif "M1" in group.f_rule:
                behavior = "fixed accent position"
            else:
                behavior = ""
        else:
            if group.f_rule == "F1":
                behavior = "preserves original accent"
            elif group.f_rule == "F2":
                behavior = "preserves original accent"
            elif group.f_rule == "F3":
                behavior = "accent shifts to stem boundary"
            elif group.f_rule == "F4":
                behavior = "accent shifts to stem boundary"
            elif "M1" in group.f_rule:
                behavior = "fixed accent position"
            else:
                behavior = ""

        example_html = ""
        if example_sentence:
            example_html = f'<div class="verb-example-sentence">"{example_sentence}"</div>'

        st.markdown(f"""
        <div class="verb-group">
            <div class="verb-group-header">{group.name}</div>
            <div class="verb-form-main">
                {rep_html}
                <span style="color:#666;font-size:0.8em;margin-left:8px">{rep.form_name}</span>
            </div>
            <div class="verb-form-accent">
                [{rep.accent_type}] {rep.pattern}
                <span style="margin-left:10px;color:#888">({behavior})</span>
            </div>
            {example_html}
            <div class="verb-other-forms">{other_forms_str}</div>
        </div>
        """, unsafe_allow_html=True)

        # Show other forms in expander if there are any
        if group.other_forms:
            with st.expander(f"Show all {group.name.split(':')[0]} forms"):
                for other in group.other_forms:
                    other_html = get_verb_accent_html(other.reading, other.pattern)
                    st.markdown(f"{other_html} [{other.accent_type}] {other.pattern} ({other.form_name})", unsafe_allow_html=True)


def get_download_link(content, filename, mime_type, label):
    """Generate a download button for content."""
    b64 = base64.b64encode(content.encode('utf-8')).decode()
    return f'<a href="data:{mime_type};base64,{b64}" download="{filename}" style="text-decoration:none;">{label}</a>'


def render_minimal_pairs_study():
    """Render the Study mode for Minimal Pairs."""
    st.markdown("---")

    # JLPT level filter
    st.markdown("##### Filter by JLPT Level")
    jlpt_cols = st.columns(6)
    with jlpt_cols[0]:
        show_all_jlpt = st.checkbox("All Levels", value=True, key="study_jlpt_all")
    with jlpt_cols[1]:
        show_n5 = st.checkbox("N5", value=False, key="study_jlpt_n5")
    with jlpt_cols[2]:
        show_n4 = st.checkbox("N4", value=False, key="study_jlpt_n4")
    with jlpt_cols[3]:
        show_n3 = st.checkbox("N3", value=False, key="study_jlpt_n3")
    with jlpt_cols[4]:
        show_n2 = st.checkbox("N2", value=False, key="study_jlpt_n2")
    with jlpt_cols[5]:
        show_n1 = st.checkbox("N1", value=False, key="study_jlpt_n1")

    # Build JLPT filter set
    jlpt_filter = None
    if not show_all_jlpt and (show_n5 or show_n4 or show_n3 or show_n2 or show_n1):
        jlpt_filter = set()
        if show_n5:
            jlpt_filter.add(5)
        if show_n4:
            jlpt_filter.add(4)
        if show_n3:
            jlpt_filter.add(3)
        if show_n2:
            jlpt_filter.add(2)
        if show_n1:
            jlpt_filter.add(1)

    # Filter pairs by JLPT level (min_jlpt indicates easiest word in pair)
    filtered_pairs = MINIMAL_PAIRS
    if jlpt_filter:
        filtered_pairs = [p for p in MINIMAL_PAIRS if p.get('min_jlpt', 0) in jlpt_filter]

    st.markdown(f"*Showing {len(filtered_pairs)} pairs*")
    st.markdown("---")

    # Group by mora count
    pairs_by_mora = {}
    for pair in filtered_pairs:
        mora = pair['mora_count']
        if mora not in pairs_by_mora:
            pairs_by_mora[mora] = []
        pairs_by_mora[mora].append(pair)

    # Show pairs grouped by mora count
    for mora_count in sorted(pairs_by_mora.keys()):
        pairs = pairs_by_mora[mora_count]
        st.markdown(f"#### {mora_count}-Mora Words ({len(pairs)} pairs)")

        for pair in pairs:
            reading = pair['reading']
            words = pair['words']
            min_jlpt = pair.get('min_jlpt', 0)

            # Header with JLPT badge
            jlpt_badge = get_jlpt_badge_html(min_jlpt)
            header_html = f"{reading}{jlpt_badge}"

            # Create colored display for each word
            word_displays = []
            for w in words:
                pattern = accent_to_pattern(w['accent'], mora_count)
                colored = get_accent_html(w['surface'], reading, w['accent'], pattern)
                word_jlpt = get_jlpt_badge_html(w.get('jlpt_level', 0))
                word_displays.append(f"{colored} <span style='color:#666'>[{w['accent']}]</span>{word_jlpt}")

            words_html = " &nbsp;vs&nbsp; ".join(word_displays)

            st.markdown(f"""
            <div class="family-tree">
                <div class="family-header">{header_html}</div>
                <div style="font-size:1.2em;">{words_html}</div>
            </div>
            """, unsafe_allow_html=True)

            # Show details in expander
            with st.expander(f"Details for {reading}"):
                for w in words:
                    pattern = accent_to_pattern(w['accent'], mora_count)
                    type_name = get_accent_type_name(w['accent'], mora_count)
                    jlpt_label = f"N{w.get('jlpt_level', 0)}" if w.get('jlpt_level', 0) > 0 else ""
                    st.markdown(f"**{w['surface']}** - [{w['accent']}] {type_name} ({pattern}) - {w['pos']} {jlpt_label}")

        st.markdown("")  # Spacing


def render_minimal_pairs_drill():
    """Render the Minimal Pairs Drill view."""
    st.markdown("### Minimal Pairs Practice")
    st.markdown("*Learn to distinguish words with the same reading but different pitch accents*")

    if not MINIMAL_PAIRS:
        st.warning("No minimal pairs data found. Run `python scripts/mine_minimal_pairs.py` to generate the data.")
        return

    # Mode selector
    drill_mode = st.radio(
        "Mode:",
        ["Study", "Drill"],
        horizontal=True,
        help="Study: review all pairs; Drill: quiz yourself"
    )

    if drill_mode == "Study":
        render_minimal_pairs_study()
        return

    # Initialize drill state
    if 'drill_correct' not in st.session_state:
        st.session_state.drill_correct = 0
    if 'drill_total' not in st.session_state:
        st.session_state.drill_total = 0
    if 'drill_current_pair' not in st.session_state:
        st.session_state.drill_current_pair = None
    if 'drill_target_word' not in st.session_state:
        st.session_state.drill_target_word = None
    if 'drill_answered' not in st.session_state:
        st.session_state.drill_answered = False
    if 'drill_last_correct' not in st.session_state:
        st.session_state.drill_last_correct = None

    # Filter by mora count and JLPT level
    col_mora, col_jlpt, col_stats = st.columns([1, 2, 1])
    with col_mora:
        mora_options = sorted(set(p['mora_count'] for p in MINIMAL_PAIRS))
        selected_mora = st.multiselect(
            "Mora count:",
            options=mora_options,
            default=mora_options,
            format_func=lambda x: f"{x} mora"
        )

    with col_jlpt:
        jlpt_options = [5, 4, 3, 2, 1]
        selected_jlpt = st.multiselect(
            "JLPT level:",
            options=jlpt_options,
            default=jlpt_options,
            format_func=lambda x: f"N{x}"
        )

    with col_stats:
        if st.session_state.drill_total > 0:
            accuracy = st.session_state.drill_correct / st.session_state.drill_total * 100
            st.markdown(f"""
            <div class="drill-stats">
                <strong>Score:</strong> {st.session_state.drill_correct}/{st.session_state.drill_total} ({accuracy:.0f}%)
            </div>
            """, unsafe_allow_html=True)

    # Filter pairs by mora count and JLPT level
    filtered_pairs = [
        p for p in MINIMAL_PAIRS
        if p['mora_count'] in selected_mora
        and (p.get('min_jlpt', 0) in selected_jlpt or p.get('min_jlpt', 0) == 0)
    ]

    if not filtered_pairs:
        st.info("No pairs match the selected filters.")
        return

    # New question button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("New Question", type="primary", use_container_width=True):
            # Select random pair and target word
            pair = random.choice(filtered_pairs)
            target = random.choice(pair['words'])
            st.session_state.drill_current_pair = pair
            st.session_state.drill_target_word = target
            st.session_state.drill_answered = False
            st.session_state.drill_last_correct = None
            st.rerun()

    with col2:
        if st.button("Reset Score", use_container_width=True):
            st.session_state.drill_correct = 0
            st.session_state.drill_total = 0
            st.rerun()

    # Display current question
    if st.session_state.drill_current_pair and st.session_state.drill_target_word:
        pair = st.session_state.drill_current_pair
        target = st.session_state.drill_target_word

        st.markdown("---")

        # Show the reading and accent pattern to identify
        reading = pair['reading']
        accent = target['accent']
        mora_count = pair['mora_count']
        pattern = accent_to_pattern(accent, mora_count)
        pattern_html = get_accent_html("", reading, accent, pattern)

        st.markdown(f"""
        <div style="text-align:center;padding:20px;">
            <div class="drill-reading">{reading}</div>
            <div class="drill-accent-pattern">{pattern_html}</div>
            <div style="color:#666;margin-top:10px;">[{accent}] - Which word has this accent?</div>
        </div>
        """, unsafe_allow_html=True)

        # Show word choices
        st.markdown("#### Choose the correct word:")
        choices = pair['words']
        cols = st.columns(len(choices))

        for i, word in enumerate(choices):
            with cols[i]:
                # Determine card state
                card_class = "drill-card"
                if st.session_state.drill_answered:
                    if word['surface'] == target['surface'] and word['accent'] == target['accent']:
                        card_class += " drill-card-correct"
                    elif st.session_state.drill_last_correct == False and i == st.session_state.get('drill_selected_idx'):
                        card_class += " drill-card-incorrect"

                word_pattern = accent_to_pattern(word['accent'], mora_count)

                # Create button for each word
                if st.button(
                    f"{word['surface']}\n[{word['accent']}]",
                    key=f"drill_choice_{i}",
                    use_container_width=True,
                    disabled=st.session_state.drill_answered
                ):
                    st.session_state.drill_answered = True
                    st.session_state.drill_total += 1
                    st.session_state.drill_selected_idx = i

                    if word['surface'] == target['surface'] and word['accent'] == target['accent']:
                        st.session_state.drill_correct += 1
                        st.session_state.drill_last_correct = True
                    else:
                        st.session_state.drill_last_correct = False

                    st.rerun()

        # Show feedback
        if st.session_state.drill_answered:
            target_jlpt = f" (N{target.get('jlpt_level', 0)})" if target.get('jlpt_level', 0) > 0 else ""
            if st.session_state.drill_last_correct:
                st.success(f"Correct! {target['surface']} [{target['accent']}] - {target['pos']}{target_jlpt}")
            else:
                st.error(f"Incorrect. The answer was {target['surface']} [{target['accent']}] - {target['pos']}{target_jlpt}")

            # Show all words with their patterns
            st.markdown("#### All words in this pair:")
            for word in pair['words']:
                word_pattern = accent_to_pattern(word['accent'], mora_count)
                word_html = get_accent_html("", reading, word['accent'], word_pattern)
                word_jlpt = get_jlpt_badge_html(word.get('jlpt_level', 0))
                st.markdown(f"**{word['surface']}** {word_html} [{word['accent']}] - {word['pos']}{word_jlpt}", unsafe_allow_html=True)

    else:
        st.info("Click 'New Question' to start the drill!")

    # Show available pairs
    with st.expander(f"View all {len(filtered_pairs)} minimal pairs"):
        for pair in filtered_pairs:
            words_str = ", ".join(f"{w['surface']}[{w['accent']}]" for w in pair['words'])
            jlpt_label = f" N{pair.get('min_jlpt', 0)}" if pair.get('min_jlpt', 0) > 0 else ""
            st.markdown(f"**{pair['reading']}** ({pair['mora_count']}拍{jlpt_label}): {words_str}")


def get_accent_category(accent_type: int, mora_count: int) -> str:
    """Get the accent category name."""
    if accent_type == 0:
        return "heiban"
    elif accent_type == 1:
        return "atamadaka"
    elif accent_type == mora_count:
        return "odaka"
    else:
        return "nakadaka"


def get_jlpt_badge_html(level: int) -> str:
    """Generate HTML badge for JLPT level."""
    if level == 0:
        return ""

    # Color coding: N5=green (easiest), N1=red (hardest)
    colors = {
        5: ("#2e7d32", "#e8f5e9"),  # green
        4: ("#1565c0", "#e3f2fd"),  # blue
        3: ("#ef6c00", "#fff3e0"),  # orange
        2: ("#c2185b", "#fce4ec"),  # pink
        1: ("#d32f2f", "#ffebee"),  # red
    }
    text_color, bg_color = colors.get(level, ("#666", "#f5f5f5"))
    return f'<span style="font-size:0.7em;background:{bg_color};color:{text_color};padding:2px 6px;border-radius:10px;margin-left:5px;font-weight:500;">N{level}</span>'


def render_word_family_tree(word_surface: str, word_reading: str):
    """Show related words with similar readings or kanji."""
    st.markdown("---")
    st.markdown("### Related Words")

    # Find words with same reading in minimal pairs
    related_by_reading = []
    for pair in MINIMAL_PAIRS:
        if pair['reading'] == word_reading:
            for w in pair['words']:
                if w['surface'] != word_surface:
                    related_by_reading.append(w)

    if related_by_reading:
        st.markdown(f"**Same reading ({word_reading}):**")
        cols = st.columns(min(len(related_by_reading), 4))
        for i, w in enumerate(related_by_reading):
            with cols[i % 4]:
                pattern = accent_to_pattern(w['accent'], len(word_reading))
                html = get_accent_html(w['surface'], word_reading, w['accent'], pattern)
                st.markdown(f"""
                <div class="family-member">
                    <strong>{w['surface']}</strong><br>
                    {html}<br>
                    <span style="font-size:0.8em;color:#666">[{w['accent']}] {w['pos']}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown(f"*No minimal pairs found for reading: {word_reading}*")


# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = None
if 'current_text' not in st.session_state:
    st.session_state.current_text = ""
if 'verb_sentences_cache' not in st.session_state:
    st.session_state.verb_sentences_cache = {}  # Cache for LLM-generated sentences

# Display options (at least one must be enabled)
if 'show_colors' not in st.session_state:
    st.session_state.show_colors = True
if 'show_pattern' not in st.session_state:
    st.session_state.show_pattern = True
if 'show_contour' not in st.session_state:
    st.session_state.show_contour = True
if 'show_number' not in st.session_state:
    st.session_state.show_number = True

# Sidebar with legend and resources
with st.sidebar:
    st.header("Pitch Pattern Legend")
    st.markdown("""
    - **<span style="color:#d73027">Red</span>** = High pitch (H)
    - **<span style="color:#4575b4">Blue</span>** = Low pitch (L)
    """, unsafe_allow_html=True)

    st.markdown("#### Accent Types")
    st.markdown("""
    | Type | Name | Pattern |
    |------|------|---------|
    | [0] | 平板 heiban | LH...H |
    | [1] | 頭高 atamadaka | HL...L |
    | [2+] | 中高 nakadaka | LH↓L...L |
    | [n] | 尾高 odaka | LH...H↓ |

    *[n] = pitch drops after nth mora*
    """)

    st.markdown("---")
    st.header("Display Options")
    st.markdown("*Select which representations to show:*")

    # Display option checkboxes
    new_colors = st.checkbox("Colors (H/L)", value=st.session_state.show_colors, key="opt_colors")
    new_pattern = st.checkbox("Pattern (LHLL)", value=st.session_state.show_pattern, key="opt_pattern")
    new_contour = st.checkbox("Contour (た/べ\\る)", value=st.session_state.show_contour, key="opt_contour")
    new_number = st.checkbox("Number ([2])", value=st.session_state.show_number, key="opt_number")

    # Ensure at least one is selected
    selected_count = sum([new_colors, new_pattern, new_contour, new_number])
    if selected_count == 0:
        st.warning("At least one display option must be selected!")
        # Keep the previous values
    else:
        st.session_state.show_colors = new_colors
        st.session_state.show_pattern = new_pattern
        st.session_state.show_contour = new_contour
        st.session_state.show_number = new_number

    st.markdown("---")
    st.header("Resources")
    st.markdown("""
    **Learn More:**
    - [What Is Pitch Accent?](docs/what_is_pitch_accent.md)
    - [Compound Sandhi Rules](docs/compound_sandhi.md)
    - [NHK Accent Dictionary](docs/nhk_accent_dictionary.md)
    - [Pitch Across Languages](docs/pitch_accent_across_languages.md)
    """)

    st.markdown("---")
    st.header("Session History")
    if st.session_state.history:
        for i, hist_text in enumerate(st.session_state.history):
            # Truncate long texts for display
            display_text = hist_text[:30] + "..." if len(hist_text) > 30 else hist_text
            if st.button(f"{display_text}", key=f"hist_{i}", use_container_width=True):
                st.session_state.current_text = hist_text
                st.rerun()
    else:
        st.markdown("*No history yet*")

    st.markdown("---")
    st.markdown("""
    **About:**
    - [GitHub](https://github.com/rschein2/PitchAccent)
    - Data: [UniDic](https://clrd.ninjal.ac.jp/unidic/) (NINJAL)
    - Compound accuracy: ~80-90%
    """)


# Main UI
st.title("Japanese Pitch Accent Analyzer")
st.markdown("*Enter Japanese text to see pitch accent patterns*")

# Example texts dropdown
col_example, col_spacer = st.columns([2, 3])
with col_example:
    selected_example = st.selectbox(
        "Load example text:",
        options=list(EXAMPLE_TEXTS.keys()),
        index=0,
        help="Select a pre-loaded example sentence"
    )

# Determine initial text value
if st.session_state.current_text:
    initial_text = st.session_state.current_text
    st.session_state.current_text = ""  # Clear after use
elif selected_example != "-- Select an example --":
    initial_text = EXAMPLE_TEXTS[selected_example]
else:
    initial_text = "今日は天気がいいですね。"

# Input
text_input = st.text_area(
    "Japanese text:",
    value=initial_text,
    height=100,
    help="Enter any Japanese text - sentences, paragraphs, or single words"
)

# View options
col_btn, col_view = st.columns([1, 2])
with col_btn:
    analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)
with col_view:
    view_mode = st.radio(
        "View mode:",
        ["Text", "Word cards", "Verbs", "Minimal Pairs"],
        horizontal=True,
        help="Text: full sentence with colors; Cards: detailed info per word; Verbs: conjugation patterns; Minimal Pairs: accent drill"
    )

# Handle Minimal Pairs view (doesn't require text input)
if view_mode == "Minimal Pairs":
    render_minimal_pairs_drill()

# Process and display results for other views
elif analyze_clicked or text_input.strip():
    if text_input.strip():
        # Different processing based on view mode
        if view_mode == "Verbs":
            # Verbs view - conjugation analysis
            render_verbs_view(text_input)
        else:
            # Text or Word cards view - standard processing
            results = process_text(text_input)
            st.session_state.current_results = results
            add_to_history(text_input)

            # Export buttons
            st.markdown("---")
            st.markdown("##### Export Options")
            export_cols = st.columns(3)

            with export_cols[0]:
                html_content = generate_html_download(results, text_input)
                st.download_button(
                    label="Download HTML",
                    data=html_content,
                    file_name=f"pitch_accent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    help="Standalone HTML file viewable in any browser"
                )

            with export_cols[1]:
                tsv_content = generate_anki_tsv(results)
                st.download_button(
                    label="Download Anki TSV",
                    data=tsv_content,
                    file_name=f"anki_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv",
                    mime="text/tab-separated-values",
                    help="Import into Anki: File > Import, select TSV"
                )

            with export_cols[2]:
                # Copy to clipboard using Streamlit's built-in
                plain_text = ""
                for result in results:
                    for word in result['words']:
                        plain_text += f"{word['surface']}【{word['reading']}】[{word['accent']}] "
                    plain_text += "\n"
                st.text_area(
                    "Copy this text:",
                    value=plain_text.strip(),
                    height=68,
                    help="Select all and copy (Ctrl+C / Cmd+C)",
                    label_visibility="collapsed"
                )

            st.markdown("---")

            # Accent type filter for Word cards mode
            accent_filter = None
            if view_mode == "Word cards":
                st.markdown("##### Filter by Accent Type")
                filter_cols = st.columns(5)
                with filter_cols[0]:
                    show_all = st.checkbox("All", value=True, key="filter_all")
                with filter_cols[1]:
                    show_heiban = st.checkbox("平板 heiban", value=False, key="filter_heiban")
                with filter_cols[2]:
                    show_atamadaka = st.checkbox("頭高 atamadaka", value=False, key="filter_atamadaka")
                with filter_cols[3]:
                    show_nakadaka = st.checkbox("中高 nakadaka", value=False, key="filter_nakadaka")
                with filter_cols[4]:
                    show_odaka = st.checkbox("尾高 odaka", value=False, key="filter_odaka")

                # Build filter set
                if not show_all and (show_heiban or show_atamadaka or show_nakadaka or show_odaka):
                    accent_filter = set()
                    if show_heiban:
                        accent_filter.add("heiban")
                    if show_atamadaka:
                        accent_filter.add("atamadaka")
                    if show_nakadaka:
                        accent_filter.add("nakadaka")
                    if show_odaka:
                        accent_filter.add("odaka")

                st.markdown("---")

            # Display results based on view mode
            for result in results:
                # Show original sentence
                st.markdown(f"**{result['sentence']}**")

                if view_mode == "Text":
                    # Inline colored sentence view
                    inline_html = generate_inline_sentence_html(result)
                    st.markdown(
                        f'<div class="inline-sentence">{inline_html}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    # Word cards view - apply filter if set
                    filtered_words = result['words']
                    if accent_filter:
                        filtered_words = []
                        for word in result['words']:
                            mora_count = len([c for j, c in enumerate(word['reading'])
                                            if c not in SMALL_KANA or j == 0])
                            category = get_accent_category(word['accent'], mora_count)
                            if category in accent_filter:
                                filtered_words.append(word)

                    if not filtered_words:
                        st.markdown("*No words match the selected accent type filter*")
                        continue

                    cols = st.columns(min(len(filtered_words), 4))

                    for i, word in enumerate(filtered_words):
                        with cols[i % 4]:
                            # Colored reading
                            html = get_accent_html(
                                word['surface'],
                                word['reading'],
                                word['accent'],
                                word['pattern']
                            )

                            # Calculate mora count for accent type name
                            mora_count = len([c for j, c in enumerate(word['reading'])
                                            if c not in SMALL_KANA or j == 0])
                            type_name = get_accent_type_name(word['accent'], mora_count)
                            category = get_accent_category(word['accent'], mora_count)

                            # Color-coded accent type badge
                            badge_class = f"filter-chip-{category}"

                            # Check if this word has minimal pair relatives
                            has_relatives = any(
                                p['reading'] == word['reading'] and len(p['words']) > 1
                                for p in MINIMAL_PAIRS
                            )

                            relative_badge = ""
                            if has_relatives:
                                relative_badge = '<span style="font-size:0.7em;background:#e3f2fd;padding:2px 6px;border-radius:10px;margin-left:5px;">has pairs</span>'

                            # Build display based on user options
                            color_html = html if st.session_state.show_colors else f'<span style="font-size:1.3em">{word["reading"]}</span>'

                            # Build accent info lines based on options
                            info_parts = []
                            if st.session_state.show_number:
                                info_parts.append(f'<span class="accent-type-name">[{word["accent"]}] {type_name}</span>')
                            if st.session_state.show_pattern:
                                info_parts.append(f'<span style="color:#888;font-size:0.85em">{word["pattern"]}</span>')
                            if st.session_state.show_contour:
                                contour = word.get('contour', '')
                                if not contour:
                                    # Generate contour if not present
                                    contour = pattern_to_contour(word['reading'], word['pattern'])
                                info_parts.append(f'<span style="color:#555;font-size:0.95em">{contour}</span>')

                            accent_info_html = '<br>'.join(info_parts) if info_parts else ''

                            st.markdown(
                                f"""
                                <div class="word-card">
                                    <div class="word-surface">{word['surface']}{relative_badge}</div>
                                    <div>{color_html}</div>
                                    <div class="accent-info">
                                        {accent_info_html}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            # Show related words in expander if they exist
                            if has_relatives:
                                with st.expander(f"Show pairs for {word['reading']}"):
                                    for pair in MINIMAL_PAIRS:
                                        if pair['reading'] == word['reading']:
                                            for w in pair['words']:
                                                if w['surface'] != word['surface']:
                                                    w_pattern = accent_to_pattern(w['accent'], pair['mora_count'])
                                                    w_html = get_accent_html(w['surface'], pair['reading'], w['accent'], w_pattern)
                                                    st.markdown(f"**{w['surface']}** {w_html} [{w['accent']}] - {w['pos']}", unsafe_allow_html=True)

                st.markdown("")  # Spacing between sentences

# Footer
st.markdown("---")
st.caption("Japanese Pitch Accent Tool | Data from UniDic (NINJAL)")

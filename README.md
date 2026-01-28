# Japanese Pitch Accent Anki Generator

**[日本語版はこちら](README_ja.md)**

Generate Anki flashcards for Japanese pitch accent study. Takes Japanese text and produces cards with:
- Color-coded pitch patterns (red=high, blue=low)
- Accent type numbers `[n]` where n=position of downstep (0=flat/heiban)
- Verb/adjective conjugation drills with pitch patterns

## What Makes This Different

Most pitch accent tools just look up dictionary forms. This tool:

1. **Computes conjugated forms** - 食べる[2] → 食べない[2], 食べます[3], etc.
2. **Handles compound nouns** - Applies Tokyo accent sandhi rules instead of just concatenating
3. **Converts numerals** - 1952年 → せんきゅうひゃくごじゅうにねん

### Compound Noun Example

Without sandhi (wrong):
```
安全[0] + 保障[0] + 面[0] = three separate words
```

With sandhi (this tool):
```
安全保障面 [7] = single compound, accent drops after 7th mora
```

## Installation

```bash
# Clone the repo
git clone https://github.com/rschein2/PitchAccent.git
cd PitchAccent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Download UniDic dictionary (~500MB, required)
python -m unidic download
```

## Usage

### Generate from text
```bash
# Direct text input
python anki_generator.py --text "今日は天気がいいですね。" --output deck.tsv

# From a text file
python anki_generator.py --input mybook.txt --output deck.tsv

# Interactive mode (paste text, Ctrl+D to finish)
python anki_generator.py --interactive --output deck.tsv
```

### Output formats
```bash
# Anki import format (default)
python anki_generator.py --input text.txt --output deck.tsv

# Standalone HTML (viewable in browser with colors)
python anki_generator.py --input text.txt --output study.html

# Plain text
python anki_generator.py --input text.txt --output study.txt
```

### Import into Anki
1. Open Anki → File → Import
2. Select your `.tsv` file
3. Set field separator to "Tab"
4. Map fields: Field 1 → Front, Field 2 → Back
5. **Check "Allow HTML in fields"**

## Example Output

**Front:**
```
彼女は毎日図書館で本を読んでいる。
```

**Back:**
```
彼女 かのじょ [1]
毎日 まいにち [1]
図書館 としょかん [2]
本 ほん [1]
読んでいる よんでいる [1]

── 活用形 ──
読む [1] HLL: 読んだ [1] HLLL, 読んで [1] HLLL, 読まない [2] LHLLL, 読みます [3] LHHLL
```

## Data Source & Reliability

### UniDic (国語研短単位自動解析用辞書)

The pitch accent data comes from **UniDic**, developed by NINJAL (National Institute for Japanese Language and Linguistics / 国立国語研究所), Japan's premier government language research institution.

**What makes UniDic authoritative:**
- Built from linguist-annotated corpora: CSJ (Corpus of Spontaneous Japanese) and BCCWJ (Balanced Corpus of Contemporary Written Japanese)
- Accent data (`aType` field) based on Tokyo dialect standard pronunciation
- **De facto standard** for Japanese NLP research worldwide
- Used by universities, commercial products, and major NLP libraries
- Professionally maintained with versioned releases

**This is NOT:**
- Crowd-sourced or wiki-style data
- Amateur annotations
- Web-scraped content

### Accuracy Estimates

| Component | Accuracy | Notes |
|-----------|----------|-------|
| Single word accent (UniDic) | ~95%+ | Very high for common vocabulary |
| Conjugation accent (F-type rules) | ~95%+ | Based on UniDic's formal rules |
| Compound noun sandhi | ~80-90% | Some compounds are lexicalized exceptions |
| Numeral + counter | ~85-90% | Common counters well-covered |

**Why compound accuracy is lower:**
- Some compounds have become lexicalized with non-predictable accents
- Proper nouns may follow different patterns
- Very long compounds (4+ elements) become less predictable
- Regional and generational variation exists

## How It Works

### Accent Computation

Uses UniDic's morphological analysis with F-type combination rules:
- **F1**: Preserve preceding accent
- **F2**: If heiban → shift to boundary; else preserve
- **F3**: If heiban → stay heiban; else shift
- **F4**: Always shift to boundary
- etc.

**Detailed documentation:** [docs/f_type_rules.md](docs/f_type_rules.md)

### Compound Noun Sandhi

Implements Tokyo dialect length-driven rules:

| N2 Length | Rule |
|-----------|------|
| 1-2 mora | Accent on last mora of N1 |
| 3-4 mora (heiban) | Accent on first mora of N2 |
| 3-4 mora (accented) | Preserve N2's accent position |
| 5+ mora | Preserve N2's accent (or heiban if N2 is heiban) |

**Detailed documentation:** [docs/compound_sandhi.md](docs/compound_sandhi.md)

### Numeral Accent

Implements Miyazaki-style numeral × counter category system with 13 categories (α-ν) and override codes.

**Detailed documentation:** [docs/numeral_accent.md](docs/numeral_accent.md)

## File Structure

```
├── anki_generator.py     # Main CLI entry point
├── accent_engine.py      # Core accent computation (F-type rules)
├── accent_rules.json     # UniDic suffix combination rules
├── compound_accent.py    # Compound noun sandhi
├── numeral_accent.py     # Counter categories & accent rules
├── numeral_reading.py    # Arabic → hiragana conversion
├── sentence_parser.py    # Tokenization & compound detection
├── html_formatter.py     # Color-coded HTML output
├── corpus_loader.py      # Text/file input handling
├── pitch_lookup.py       # Optional: JPDB/OJAD verification
└── docs/
    ├── compound_sandhi.md    # Compound noun accent rules (detailed)
    ├── f_type_rules.md       # F-type combination rules (detailed)
    └── numeral_accent.md     # Numeral accent rules (detailed)
```

## Optional: JPDB API for Verification

The core functionality works offline. For optional pitch verification against jpdb.io:

1. Get an API key from [jpdb.io/settings](https://jpdb.io/settings)
2. Create `.env` file: `JPDB_API_KEY=your_key_here`
3. Use `pitch_lookup.py` to verify individual words

## Limitations

- **Compound accent rules are ~80-90% accurate** - Some compounds are lexicalized exceptions that don't follow productive rules. The tool uses the most common Tokyo dialect patterns, but individual speakers may vary.
- **Numeral readings don't include rendaku** - Outputs さんひゃく instead of さんびゃく. This is a simplification; full rendaku rules are complex.
- **Very long compounds** - Compounds with 4+ elements may have unpredictable accents.
- **Counter coverage** - Some less common counters aren't in the category table yet.
- **No regional variants** - Only Tokyo standard dialect is supported.

## References

### Primary Sources
- [UniDic](https://clrd.ninjal.ac.jp/unidic/) - Morphological dictionary with accent data (NINJAL)
- [TUFS Language Modules](https://www.coelang.tufs.ac.jp/mt/ja/pmod/practical/02-07-01.php) - Compound accent rules (Tokyo University of Foreign Studies)
- [Miyazaki et al. (2012)](https://www.gavo.t.u-tokyo.ac.jp/~mine/paper/PDF/2012/ASJ_1-11-11_p319-322_t2012-3.pdf) - Numeral accent rules

### Additional Resources
- [OJAD](https://www.gavo.t.u-tokyo.ac.jp/ojad/) - Online Japanese Accent Dictionary (University of Tokyo)
- Kubozono, Haruo - Research on Japanese prosody and compound accent
- NHK日本語発音アクセント新辞典 (2016) - NHK Pronunciation and Accent Dictionary

## License

MIT

# Japanese Pitch Accent Anki Generator

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
git clone https://github.com/YOUR_USERNAME/pitch-accent-anki.git
cd pitch-accent-anki

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install fugashi unidic requests beautifulsoup4

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

## How It Works

### Accent Computation

Uses UniDic's morphological analysis with F-type combination rules:
- **F1**: Preserve preceding accent
- **F2**: If heiban → shift to boundary; else preserve
- **F3**: If heiban → stay heiban; else shift
- **F4**: Always shift to boundary
- etc.

### Compound Noun Sandhi

Implements Tokyo dialect length-driven rules:

| N2 Length | Rule |
|-----------|------|
| 1-2 mora | Accent on last mora of N1 |
| 3-4 mora (heiban) | Accent on first mora of N2 |
| 3-4 mora (accented) | Preserve N2's accent position |
| 5+ mora | Preserve N2's accent (or heiban if N2 is heiban) |

Based on: [TUFS Compound Accent Rules](https://www.coelang.tufs.ac.jp/mt/ja/pmod/practical/02-07-01.php)

### Numeral Conversion

Arabic numerals are converted to Japanese readings:
- `1952` → `せんきゅうひゃくごじゅうに`
- `6万人` → `ろくまんにん`

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
└── pitch_lookup.py       # Optional: JPDB/OJAD verification
```

## Optional: JPDB API for Verification

The core functionality works offline. For optional pitch verification against jpdb.io:

1. Get an API key from [jpdb.io/settings](https://jpdb.io/settings)
2. Create `.env` file: `JPDB_API_KEY=your_key_here`
3. Use `pitch_lookup.py` to verify individual words

## Limitations

- Compound accent rules are ~80-90% accurate (some compounds are lexicalized exceptions)
- Numeral readings ignore rendaku (さんひゃく instead of さんびゃく)
- Very long compounds may have unpredictable accents
- Some counters not yet in the category table

## References

- [UniDic](https://clrd.ninjal.ac.jp/unidic/) - Morphological dictionary
- [TUFS Language Modules](https://www.coelang.tufs.ac.jp/mt/ja/pmod/practical/02-07-01.php) - Compound accent rules
- [Miyazaki et al. (2012)](https://www.gavo.t.u-tokyo.ac.jp/~mine/paper/PDF/2012/ASJ_1-11-11_p319-322_t2012-3.pdf) - Numeral accent rules
- [OJAD](https://www.gavo.t.u-tokyo.ac.jp/ojad/) - Online Japanese Accent Dictionary

## License

MIT

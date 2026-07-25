# Kanjium accent database

`accents.txt.gz` — pitch accent positions for ~124,000 Japanese words.

- Source: https://github.com/mifunetoshiro/kanjium (`data/source_files/raw/accents.txt`)
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- Format per line: `surface<TAB>reading(hiragana)<TAB>accents`
  where `accents` is a comma-separated list of accent nucleus positions,
  primary variant first (`0` = heiban).

Loaded by `pitch_accent/accent_dict.py`. Dictionary hits take priority over
rule-based accent computation; the rules handle conjugated forms and
compounds that aren't lexicalized here.

# UniDic Verb Pitch Accent Combination Rules

This document describes the accent combination system used by UniDic for computing pitch accent on conjugated verb forms.

## Overview

UniDic uses three key fields for accent computation:

1. **aType**: Base accent type (0=heiban/flat, n=drop after nth mora)
2. **aModType**: Modification rule applied to stems before combining (e.g., M4@1)
3. **aConType**: Combination rule for suffixes (e.g., F3@0)

## The M-Type Modification Rules

Applied to verb stems BEFORE suffix combination.

### M4@n (Shortened Stem Modification)

From UniDic Table 9, M4@n is used for ichidan verb stems (mizenkei, etc.) where the る is dropped.

**Special case handling:**
- If base accent is **0 or 1** → keep it unchanged
- If base accent is **≥2** → subtract n

Examples with M4@1:
- 見る[1] → 見[1] (stays 1, NOT 0)
- 食べる[2] → 食べ[1] (2-1=1)
- 起きる[2] → 起き[1] (2-1=1)

### M1@n (Fixed Accent)

Sets accent to position n. Used for volitional form (意志推量形).

## The F-Type Combination Rules

Applied when combining stem + suffix. From UniDic Table 12:

| Rule | Formula | Behavior |
|------|---------|----------|
| **F1** | M2 = M1 | Preserve stem accent |
| **F2@M** | M1=0 → N1+M; else M1 | Heiban gains accent, accented preserves |
| **F3@M** | M1=0 → 0; else N1+M | Heiban stays flat, accented shifts to N1+M |
| **F4@M** | M2 = N1+M | Always shift to position N1+M |
| **F5** | M2 = 0 | Always heiban |
| **F6@M@L** | M1=0 → N1+M; else N1+L | Different offsets for heiban vs accented |

Where:
- **M1** = accent type of stem (after aModType applied)
- **N1** = mora count of stem
- **M, L** = parameters from aConType
- **M2** = resulting accent type

## Suffix Rules from UniDic

Based on parsing conjugated forms with our UniDic installation:

| Suffix | aConType | Effect |
|--------|----------|--------|
| て (te-form) | 動詞%F1 | Preserve stem accent |
| た (ta-form) | 動詞%F2@1 → **overridden to F1** | Preserve stem accent (see below) |
| ない (negative) | 動詞%F3@0 | Heiban→stay flat, accented→N1 |
| ます (polite) | 動詞%F4@1 | Always N1+1 |
| たい (desiderative) | 動詞%F4@1 | Always N1+1 |

**Note:** UniDic's dictionary data gives た `動詞%F2@1`, which would make the
past tense of every heiban verb odaka (行った→[3]). Standard Tokyo accent keeps
it flat (行った[0], 買った[0]), and the UniDic manual's own Table 12 lists た as
F1. The engine corrects this in `AccentEngine.ACON_OVERRIDES` — the single
place where known-wrong UniDic data is fixed.

## Worked Examples

### Example 1: 見ない (ichidan verb, base [1])

1. Base verb 見る has aType=1
2. Stem 見 has aModType=M4@1 → since base is 1, stays **[1]**
3. Suffix ない has aConType=動詞%F3@0
4. F3@0: Since M1=1 (accented), M2 = N1+M = 1+0 = **1**
5. Result: みない [1] = **HLL** ✓

### Example 2: 起きない (ichidan verb, base [2])

1. Base verb 起きる has aType=2
2. Stem 起き has aModType=M4@1 → since base ≥2, accent = 2-1 = **[1]**
3. Suffix ない has aConType=動詞%F3@0
4. F3@0: Since M1=1 (accented), M2 = N1+M = 2+0 = **2**
5. Result: おきない [2] = **LHLL** ✓

### Example 3: 食べて (ichidan verb, base [2])

1. Base verb 食べる has aType=2
2. Stem 食べ has aModType=M4@1 → accent = 2-1 = **[1]**
3. Suffix て has aConType=動詞%F1
4. F1: M2 = M1 = **1**
5. Result: たべて [1] = **HLL**

### Example 4: 行かない (godan verb, base [0] heiban)

1. Base verb 行く has aType=0 (heiban)
2. Stem 行か has NO aModType (godan stems don't get M4)
3. Suffix ない has aConType=動詞%F3@0
4. F3@0: Since M1=0 (heiban), M2 = **0** (stays heiban)
5. Result: いかない [0] = **LHHH** ✓

## Test Results (current engine output — verified against NHK/OJAD)

| Verb | Base | te-form | ta-form | nai-form | masu-form | volitional |
|------|------|---------|---------|----------|-----------|------------|
| 見る | [1] | [1] HL | [1] HL | [1] HLL | [2] LHL | [2] LHL |
| 食べる | [2] | [1] HLL | [1] HLL | [2] LHLL | [3] LHHL | [3] LHHL |
| 起きる | [2] | [1] HLL | [1] HLL | [2] LHLL | [3] LHHL | [3] LHHL |
| 行く | [0] | [0] LHH | [0] LHH | [0] LHHH | [3] LHHL | [2] LHL |
| 書く | [1] | [1] HLL | [1] HLL | [2] LHLL | [3] LHHL | [2] LHL |

The full gold battery lives in `tests/test_accent.py` — run it after any rule change.

## Resolved Discrepancies

1. **た (past tense)**: UniDic's data returns F2@1 but the manual's Table 12
   lists F1. F2@1 wrongly made heiban past forms odaka (行った→[3]).
   Fixed via `AccentEngine.ACON_OVERRIDES` (助動詞-タ → F1 for verbs).

2. **Suffix aModType**: Inflected suffixes (ましょ M1@1, られ M4@1, なかっ M2@2,
   たら M2@1) carry an aModType that adjusts the accent of the combined form
   using its total mora count. The engine now applies it after each F-rule
   combination (fixes 食べましょう[4], 食べられて[3]).

3. **Auxiliary verbs after て**: a verb following て/で (いる, ある, みる, くる…)
   is an auxiliary, not the rear of a noun compound, so its C-type must not
   apply. Unaccented auxiliaries keep the te-form accent (食べている[1]);
   accented ones take N1+M2 (行ってくる[4], 書いてある[4]). Renyokei compound
   verbs (食べ始める) are accented on V2's penultimate mora.

## References

- [UniDic Manual (NINJAL)](https://clrd.ninjal.ac.jp/unidic/UNIDIC_manual.pdf) - Tables 9 and 12
- [Kanshudo Pitch Accent Guide](https://www.kanshudo.com/howto/pitch)

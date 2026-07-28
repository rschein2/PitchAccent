# Notes for flasher (accent API v0.2)

The accent service flasher talks to (Railway, `ACCENT_API_BASE`) got a large
accuracy overhaul in late July 2026. Nothing reaches flasher until the
service is **redeployed**. This doc is the handoff.

## 1. Redeploy checklist (do this first)

- Redeploy from current `master` (v0.2.0). The Dockerfile now copies
  `data/` — earlier Dockerfiles omitted it, which would have silently
  disabled the two new data layers (the engine falls back to rules-only
  without complaint).
- Sanity probe after deploy — these distinguish v0.2 from v0.1:

  | POST /analyze | v0.1 (wrong/absent) | v0.2 (correct) |
  |---|---|---|
  | 行った | accent_type 3 | accent_type **0**, source `dictionary+rules` |
  | 食べましょう | 3 | **4** |
  | 持ち込む | no variants | accent_variants **[0, 3]** |
  | 安全保障 | computed | **5**, source `dictionary` |

  If `source` is `"rules"` for 安全保障, the data/ layer is missing from
  the image.

## 2. Stale persisted pitch_data (action recommended)

flasher persists `/parse` output (`vocab_example_sentences.pitch_data`,
`vocab_items.pitch_accent`). **Anything persisted before the redeploy may
carry systematically wrong accents**, most commonly:

- past tense of flat verbs: 行った/買った/言った were rendered [3]-odaka,
  correct is flat [0] — this affected *every* heiban verb's た/たら form
- 〜ましょう forms (were [3]-style, correct accents on しょ)
- 〜ている forms (were flattened to [0], correct keeps the te-form accent)
- 〜くない/〜くなかった adjective negatives
- numeral+counter phrases (3冊 etc. previously went through compound
  sandhi with no reading sandhi)

Recommendation: backfill — re-run `/parse` for stored `pitch_data` rows
(or lazily re-fetch on next view and overwrite). For a flashcard app this
matters double: users may have memorized the wrong pitch from cached cards.

## 3. New response fields (all additive, nothing breaking)

`/analyze` now also returns:

- `accent_variants`: list of accepted accents, primary first, empty when
  the word has one accent. E.g. 持ち込む → `[0, 3]`.
- `source`: `"dictionary"` (whole-word hit in the 124k-entry Kanjium
  layer) | `"dictionary+rules"` (base verified by dictionary, conjugation
  computed) | `"rules"` (UniDic + F-rules only).
- `corrections`: machine-readable list of corrections that fired
  (e.g. `acon-override:た→F1`, `potential-verb:乗れる[0]`).

`/parse` words now also carry `accent_variants` and `source`
(`"dictionary" | "numeral" | "compound" | "unidic"`). Note flasher's
`_passthrough` tokens already use `source: "latin"/"punct"` — the
conventions compose; treat unknown values as "computed".

Suggested UI use:
- **Variants**: show secondary accents (e.g. small "also [3]") — several
  common words legitimately have two accents. This should also cut down
  false "wrong accent" reports: check reports against `accent_variants`
  before triaging.
- **Source**: badge dictionary-verified accents differently from computed
  ones if you want a confidence signal; `numeral` phrases now carry
  correct sandhi readings (3冊 → さんさつ, 三十分 → さんじゅっぷん).

## 4. Things flasher works around that may have changed

- `pitch_overrides` (segmentation splits like 普段投稿 → 普段+投稿): the
  dictionary layer changes which compounds resolve lexically. Worth
  re-testing the override list against v0.2 — some may be obsolete, and
  accumulated `flasher_pitch_reports` rows may already be fixed.
- する-compound workaround in `cards_pitch.py` (build 410): still fine.
  The re-analyzed compound surfaces (対して etc.) now benefit from the
  dictionary layer themselves.
- `/forms` response shape is unchanged; conjugation accents are computed
  from dictionary-corrected base accents now.

## 5. Verification surface

The service-side test suites (in the PitchAccent repo) now cover 75 hand
gold cases + 3,057 OJAD-mined comparisons + numeral/dictionary suites.
If flasher's report queue surfaces a wrong accent, it can be turned into
a gold case in `tests/test_accent.py` — that's the intended triage path.

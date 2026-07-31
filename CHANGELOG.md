# Changelog

## Unreleased

### Fixed

- **The advertised calibration figures were stale.** The README and
  `docs/calibration.md` quoted 2.12 per 1,000 words over a 47k-word corpus at
  72x separation. The committed results say 2.14 over 67k words at 71x, and
  they reproduce exactly. The quote-parity fix that shipped in 1.1.1 moved the
  numbers after that release note was drafted, and nothing caught the drift.

### Added

- `tests/test_calibration_claims.py` pins every calibration figure quoted in
  the README and the calibration doc to `benchmarks/results/calibration.json`.
  Restoring the old numbers fails three of the new tests.
- A seventh row in the calibration round history, recording what the bug-hunt
  release did to the numbers, plus a note that a parser change is a
  calibration change even when no rule was touched.

### Removed

- `ste_lint/`, a directory of stale bytecode left behind when the aviation-era
  package was deleted.

## 1.1.1 — 2026-07-30

A bug-hunt release. Six defects found by adversarial review, each fixed with
a regression test, plus a robustness suite that fuzzes the linter with
hostile inputs.

### Fixed

- **Misspelled imperatives in suggestions.** `CLARITY-PASSIVE` suggested
  "Disconnecte the …" and "Adjuste the …": the verb-base heuristic restored a
  silent *e* onto almost any stem. Rebuilt around English orthography (words
  do not end in bare v, z, soft c, or u) plus a list of the silent-e verbs
  common in documentation; a test pins 33 verb forms.
- **`AI-BOLDLIST` counted bullets inside code fences.** It scanned the raw
  document; fenced blocks are now stripped first.
- **Specimen masking ate prose between possessives.** The single-quote
  pattern treated apostrophes as quote delimiters, so in "the collector's
  clock and the user's config" everything between the two apostrophes was
  masked — hiding real findings. An apostrophe inside a word is no longer a
  delimiter.
- **An empty baseline quote suppressed a whole rule.** `"quote": ""`
  prefix-matched every finding of its rule in its file. Empty quotes are now
  rejected at load — and the stricter check immediately caught three such
  entries in this repo's own baseline.
- **Document-level findings could not be baselined honestly.** Rate reporters
  (`AI-DASH`, `AI-VOCAB-DENSITY`) have no phrase to quote, which is why those
  empty quotes existed. `"quote": "*"` is now the explicit whole-document
  exemption, scoped to one rule in one file.
- **Links to repeated headings were false positives.** GitHub suffixes
  duplicate headings (`#setup`, `#setup-1`); the anchor checker now generates
  the same suffixes.
- **A terminator inside quotes ended the sentence.** Splitting
  `"Certainly! Here's…"` at the `!` left both fragments with unbalanced
  quotes, which broke specimen masking downstream. The splitter now tracks
  quote parity; a stray unbalanced quote affects only its own paragraph. The
  release gate caught this on CI while a piped local check was reading
  `tail`'s exit code instead of techlint's — the pipeline was right and the
  shell habit was wrong.

### Added

- `tests/test_bughunt.py`: a regression test per bug, named after the failure
  mode.
- `tests/test_robustness.py`: 29 hostile inputs (CRLF, unterminated fences,
  control characters, RTL text, 50k-character words, list bombs) run against
  three configs, asserting no crashes, in-range positions, and bounded
  runtime against regex-backtracking bait.

Calibration: known-good 2.14, separation 71×. (An earlier draft of this entry
said the numbers were unchanged at 2.12/72×. That was written before the
quote-parity fix landed in this same release; correcting sentence splitting
shifts every per-sentence rate a little.)

## 1.1.0 — 2026-07-29

Adds a documentation-conventions battery drawn from the major style guides,
and widens the calibration corpus to cover all four Diátaxis genres.

### New: the `DOC-*` battery

Eleven rules, each citing a named authority:

| rule | catches |
|---|---|
| `DOC-LINKTEXT` | "click here" and other link text that does not say where it goes (Google, Microsoft, WCAG 2.4.4) |
| `DOC-CONDESCEND` | words that minimize the reader's effort — "simply", "obviously", "it is easy to" (Google word list; Microsoft) |
| `DOC-PLEASE` | "please" in instructions (Google: documentation instructs) |
| `DOC-ALLOWS` | "allows you to" → "lets you" (Google word list) |
| `DOC-PERSON` | "the user must" instead of "you" (Google, Microsoft) |
| `DOC-TENSE` | "will return" for present behavior (Google, Microsoft) |
| `DOC-HEADING` | skipped heading levels, multiple level-1 headings (WCAG 1.3.1) |
| `DOC-ALT` | images with no alt text (WCAG 1.1.1) |
| `DOC-ACTION` | procedures that explain for a long time before instructing (Carroll's minimalism; Diátaxis) |
| `DOC-READABILITY` | Flesch-Kincaid grade level, as a metric |
| `DOC-ACRONYM` | abbreviations never expanded (IEEE 1063, ISO/IEC 26514) — **opt-in** |

Calibration reshaped two of these before shipping. `DOC-CONDESCEND`
now splits by grammatical role, because "Simple Mail Transfer Protocol" and
"a simple hash table" describe things rather than the reader's experience;
only adverbs and reader-directed frames are flagged. `DOC-ACRONYM` is off by
default: it ran at 2.79 per 1,000 words on canon and nearly all of it was
wrong, flagging "FILES" and "TOTAL" from headings.

### Calibration corpus now covers all four genres

The corpus was specifications only, which tuned the thresholds for
specifications. It now includes tutorials, how-to guides, and explanation
(Python 3.8 documentation, frozen in 2019). That moved the known-good mean
from 1.38 to 2.12: genres that address the reader directly run warmer than
protocol specs.

Verdict bands were re-anchored so every canon text still lands in `clean`:
`clean` < 5, `light` < 12, `moderate` < 30, `heavy` ≥ 30. They are now
configurable with `bands:`.

### Also

- A fifth score axis, `convention`, for the new battery.
- `CLARITY-THAT` no longer fires on "Check the agent log" — a dropped "that"
  only matters when a clause follows, not a plain object. Found by writing
  the new example and linting it.
- Quoted-specimen masking now covers both batteries, not only the AI one.
- New `examples/` set: a comprehensive 443-word draft scoring 115 across five
  axes, and its rewrite at 396 words scoring zero, with the six pages it
  links to so the reference validator has a real tree to check.
- A release pipeline: pushing a version bump to `main` re-runs the quality
  gate, then creates the tag, the GitHub Release (notes taken from this
  changelog), and the built distributions. PyPI publishing is wired behind
  the `ENABLE_PYPI` repository variable.

## 1.0.0 — 2026-07-29

First public release.

techlint answers one question: how much does this document read like unedited
generated output, and where? It does not claim to detect authorship — nothing
does that reliably — and it does not judge whether writing is good.

### Detection

- **Excess vocabulary, tiered by measured effect size.** Derived from Kobak et
  al. (2025), who tracked word frequencies across 15M PubMed abstracts. Words
  carry a tier from their computed excess ratio: strong (≥5×) is `major`, moderate
  (≥2.5×) is `minor`, mild (≥1.6×) feeds a density signal only, and everything
  below 1.6× is dropped. That last cut is what keeps ordinary technical English
  — "using" at 1.04×, "however" at 1.01× — out of the results.
- **Artifacts** (`blocker`): chat frames, assistant pleasantries, unfilled
  placeholders, appeals to unnamed studies.
- **Constructions** (`AI-PHRASE`): throat-clearing, scene-setting, antithesis
  templates, self-posed Q&A, countdown negation, inflated copulas, participial
  editorializing, essay closers, advertising register.
- **Reference validation** (`AI-LINK`): relative link targets checked against
  the filesystem, heading anchors against real headings. Offline; external URLs
  are deliberately out of scope.
- **Structure and distribution**: em-dash density, rule-of-three, transition
  scaffolding, hedge stacks, intensifier density, listicle skeletons,
  sentence-length uniformity, the copula daisy-chain, scaffolding ratio.
- **Statistics**: adjacent paragraphs restating one idea, long abstract
  sentences carrying few new facts, repeated n-grams (opt-in).

### Clarity

A rule enters this battery only when two or more independent authorities
agree: Google, Microsoft, the Federal Plain Language Guidelines, RFC 2119, and
Gopen & Swan. The checks cover passive voice, graded by whether the missing
actor costs the reader anything. They also cover buried verbs, wordiness,
subject-verb distance, stress position, inclusive language, Latin
abbreviations, normative keywords, and sentence and paragraph budgets.

### Scoring

`blocker` (3.0) · `major` (1.5) · `minor` (0.5) · `info` (0.0), summed per
1,000 words, and split across four axes — fabrication, filler, clarity,
structure — so the number says what kind of editing is needed rather than only
how much.

Verdict bands are anchored to the calibration corpus rather than guessed:
`clean` < 4 · `light` < 10 · `moderate` < 25 · `heavy` ≥ 25.

### Calibration

Thresholds are derived from measurement. The known-good corpus is technical
prose written long before LLMs existed (RFCs 793/1035/1925/2119, PEPs
8/20/257); anything found there is a false positive by construction. Four
calibration rounds each produced an instrument fix rather than a document
finding, most memorably PEP 8 being flagged 19 times for "underscores", which
it uses to mean the `_` character.

Current separation: pre-LLM canon **1.38**/1k against a slop fixture at
**149.8**, roughly 108×. CI fails if that separation collapses below 20×.

### Handling false positives

The detector over-flags by design. A four-category exemption taxonomy (proper
noun, domain vocabulary, literal usage, quoted text) covers most of it; the
rest goes in a suppression baseline that refuses entries without a written
reason.

### Interface

`techlint` CLI with text, JSON, GitHub-annotation, and summary output;
`--gate` for CI; `--explain` for any rule; per-project `techlint.yaml`; a
pre-commit hook. Python ≥ 3.9, no runtime dependencies. 129 tests.

### Prior history

This began as a direct implementation of ASD-STE100 (Simplified Technical
English), which is an excellent standard for aircraft maintenance manuals and
generalizes poorly — its 875-word dictionary wanted "chip" replaced with
"PARTICLE" on a semiconductor page. That layer was removed before 1.0;
`docs/removed-rules.md` records what went and why.

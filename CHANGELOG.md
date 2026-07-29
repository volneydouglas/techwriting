# Changelog

## 1.0.0 — 2026-07-29

First public release.

techlint answers one question: how much does this document read like unedited
generated output, and where? It does not claim to detect authorship — nothing
does that reliably — and it does not judge whether writing is good.

### Detection

- **Excess vocabulary, tiered by measured effect size.** Derived from Kobak et
  al. (2025), who tracked word frequencies across 15M PubMed abstracts. Words
  are tiered by computed excess ratio: strong (≥5×) is `major`, moderate
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

Rules are included only where two or more independent authorities agree
(Google, Microsoft, Federal Plain Language Guidelines, RFC 2119, Gopen & Swan):
passive voice graded by whether the missing actor costs the reader anything,
buried verbs, wordiness, subject-verb distance, stress position, inclusive
language, Latin abbreviations, normative keywords, sentence and paragraph
budgets.

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

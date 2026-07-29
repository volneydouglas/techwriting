# techwriting

**techlint** — a technical-writing linter with AI-tic detection, calibrated
against pre-LLM technical prose. Zero runtime dependencies.

It answers one question: *how much does this document read like unedited
generated output, and where?* Not "is this good", and not "did a machine write
this" — nothing can answer that reliably. What it measures is a defect worth
fixing regardless of authorship.

```
$ techlint examples/before.md
examples/before.md:3:1   major    AI-PHRASE      Stock construction: "In today's fast-paced digital landscape".
examples/before.md:6:40  major    AI-VOCAB       "delve" is 7.91x more frequent in post-LLM text than the pre-LLM trend predicts.
examples/before.md:19:68 blocker  AI-ARTIFACT    Generated-text artifact: "Studies show".
examples/before.md:33:22 minor    DOC-PERSON     "The user must" writes about the reader instead of to them.
examples/before.md:47:34 minor    DOC-LINKTEXT   Link text "click here" does not say where it goes.
examples/before.md:53:1  minor    DOC-ALT        Image "architecture.png" has no alt text.

1 file(s), 443 words: 3 blocker, 20 major, 24 minor, 9 info

  fabrication   30.47  ████████  verify these against reality before shipping
  filler        66.59  █████████████████  cut; the sentences work without them
  clarity        5.64  █  rewrite for the reader's working memory
  convention    12.42  ███  align with the style guides your readers already expect

weighted score 115.12/1k words — heavy
```

`examples/after.md` is the same document rewritten against those findings —
396 words, **zero findings**. Both are in the repo, and CI asserts the
contrast holds.

## Why the numbers mean something

The vocabulary list is **measured, not guessed**. It comes from Kobak et al.
(*Science Advances*, 2025), who tracked word frequencies across 15 million
PubMed abstracts and found which words broke from their pre-LLM trend. Each
word is tiered by its measured excess ratio:

| word | ratio | tier |
|---|---|---|
| delves | 28.2× | strong → `major` |
| underscores | 13.8× | strong → `major` |
| meticulously | 11.3× | strong → `major` |
| encompassing | 4.7× | moderate → `minor` |
| notably | 1.9× | mild → density only |
| using | 1.04× | **dropped — not a signal** |
| however | 1.01× | **dropped — not a signal** |

That last group is why tiering matters. A flat "AI words" list flags ordinary
technical English and buries the signal.

The thresholds are **calibrated against documents that cannot be AI-written**:
RFCs and PEPs from 1981–2001. Anything the detector finds there is a false
positive by construction.

| | weighted score |
|---|---|
| pre-LLM technical canon (47k words, 12 texts) | **2.12** /1k (range 1.18–4.36) |
| deliberately slop-dense fixture | **151.8** /1k |
| **separation** | **72×** |

Every calibration round so far has found an instrument bug rather than a
document defect — including PEP 8 being flagged 19 times for "underscores",
which it uses to mean the `_` character. The corpus covers all four Diátaxis
genres, because genre moves the numbers as much as age does: tutorials and
how-to guides run warmer than specifications. See
[docs/calibration.md](docs/calibration.md).

## Install

```
pip install -e .          # Python >= 3.9, stdlib only
pip install -e .[dev]     # + pytest
```

## Use

```
techlint docs/                        lint a tree
techlint --mode procedure runbook.md  20-word budget, RFC-2119 checks, actor-required
techlint --only ai README.md          AI tics only
techlint --gate 3.0 docs/             CI: fail if the weighted score exceeds 3.0
techlint --explain AI-VOCAB           what a rule means and where it came from
techlint --format json docs/          machine-readable
techlint --baseline-suggest docs/     emit exemption lines for review
cat draft.md | techlint -             stdin
```

Markdown-aware: fenced code, inline code, and tables are skipped; headings are
exempt from prose budgets; each list item is its own sentence.

## What it checks

**Reference validation** — `AI-LINK` checks that relative links resolve and
heading anchors exist. This is the prose form of a hallucinated import: the
target either resolves or it does not. Offline, no network.

**AI tics** ([catalog](docs/ai-tics.md)) — four layers by confidence:
`AI-ARTIFACT` (blocker: chat frames, unfilled placeholders, appeals to unnamed
studies) · `AI-COPULA` (blocker: the copula daisy-chain, zero occurrences in
~1M words of human prose) · `AI-PHRASE` (throat-clearing, scene-setting,
antithesis templates, self-posed Q&A, participial editorializing, essay
closers) · `AI-VOCAB` + `AI-VOCAB-DENSITY` (tiered) · plus em-dash density,
rule-of-three, transition scaffolding, hedge stacks, listicle skeletons, and
sentence-length uniformity.

**Clarity** ([style guide](docs/style-guide.md)) — only rules two independent
authorities agree on: passive voice (mode-aware), buried verbs, wordiness,
subject-verb distance and stress position (Gopen & Swan), inclusive language,
Latin abbreviations, RFC 2119 keyword discipline, sentence and paragraph
budgets.

**Documentation conventions** — link text that says where it goes (Google,
Microsoft, WCAG 2.4.4) · words that minimize the reader's effort (Google
word list) · second person · present tense · heading hierarchy and image alt
text (WCAG) · time-to-first-instruction (Carroll's minimalism) ·
Flesch-Kincaid grade level · undefined acronyms (opt-in).

**Statistics** — adjacent paragraphs restating one idea, long abstract
sentences carrying few new facts, repeated n-grams (opt-in).

## Severity and scoring

`blocker` (3.0) · `major` (1.5) · `minor` (0.5) · `info` (0.0), summed per
1,000 words. Info deliberately weighs zero: audit candidates must never gate a
build.

```
wscore = (3.0*blocker + 1.5*major + 0.5*minor) / words * 1000
```

Bands are anchored to the calibration corpus: `clean` < 5 · `light` < 12 ·
`moderate` < 30 · `heavy` ≥ 30, and are configurable with `bands:`.

The score also splits by **axis**, because one number tells you a document
needs work but not what work:

```
  filler        38.46  ███████████████████████  cut; the sentences work without them
  clarity        8.88  █████  rewrite for the reader's working memory
  structure      2.96  ██  reorganize; the shape is doing the talking
```

`fabrication` means fact-check it · `filler` means cut · `clarity` means
rewrite · `structure` means reorganize.

## Configuration

`techlint.yaml`, discovered by walking up from the working directory:

```yaml
mode: reference          # procedure | reference | narrative
locale: us
budgets:
  sentence_words: 30
  em_dash_per_1k: 10
style:
  contractions: allow    # Google's guide allows them
exclude:                 # on top of vendor/build dirs, always skipped
  - generated-*
domain_vocabulary:       # never flagged as AI vocabulary
  - harness              # the test harness this project documents
  - realm                # Kerberos realm
```

`techlint .` walks directories recursively, skipping `node_modules`, `.venv`,
`build`, `dist`, `target`, and other vendor and build directories by default.
A file named explicitly on the command line is always linted, even inside an
excluded directory.

## Handling false positives

The detector is designed to over-flag slightly; roughly a quarter of `major`
hits should be overruled on review. Record each exemption with a reason in
`.techlint-baseline.jsonl` — techlint refuses entries without a `why`:

```json
{"rule": "AI-VOCAB", "file": "docs/api.md", "quote": "delves",
 "why": "quoted verbatim from the upstream 3.2 changelog"}
```

See [docs/exemptions.md](docs/exemptions.md) for the four-category taxonomy.
The most valuable review verdict is "the rule is wrong" — fix the rule, add a
test, re-run calibration.

## CI

```yaml
- run: pip install .
- run: techlint --format github --gate 5.0 docs/
```

Or as a pre-commit hook:

```yaml
repos:
  - repo: https://github.com/volneydouglas/techwriting
    rev: v1.1.0
    hooks:
      - id: techlint
```

## Layout

```
techlint/            the linter (stdlib only)
  checks_ai.py       AI tic battery, tiered by measured effect size
  checks_clarity.py  clarity rules with multi-authority backing
  checks_docs.py     style-guide and accessibility conventions
  checks_links.py    reference validation + scaffolding ratio
  stats.py           distribution instruments
  config.py          per-project config; the framework ships no domain knowledge
  baseline.py        suppression baseline with mandatory reasons
docs/                style guide, AI tic catalog, research basis,
                     calibration program, exemptions, removed rules
benchmarks/          calibration harness + committed results
tools/               regenerate the vocabulary data from the source study
examples/            before/after pair, wired into CI
```

## History

This started as a direct implementation of **ASD-STE100** (Simplified Technical
English). STE is an excellent standard for aircraft maintenance manuals and
generalizes poorly — its 875-word dictionary wanted "chip" replaced with
"PARTICLE" on a semiconductor page. The aviation-only layer was removed;
[docs/removed-rules.md](docs/removed-rules.md) records exactly what went and
why. The rules that survived did so because other authorities independently
agree with them.

The severity model, suppression baseline, exemption taxonomy, and calibration
discipline are adapted from two sibling projects that apply the same
code-smell framing to fiction. Reference validation, the axis breakdown, and
the scaffolding-ratio check come from
[sloppylint](https://github.com/rsionnach/sloppylint), which does the
equivalent job for Python code. One idea inverts on the way across: in fiction a
repeated distinctive word is a defect, while in technical writing terminology
consistency *requires* repetition — varying your term is the bug.

Full citations: [docs/research-basis.md](docs/research-basis.md).

## License

MIT — see [LICENSE](LICENSE). Third-party attribution for the
excess-vocabulary data, the calibration corpus, and the borrowed ideas is in
[NOTICE](NOTICE). Release notes: [CHANGELOG.md](CHANGELOG.md).

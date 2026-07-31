# Development

Orientation for working on techlint itself. `CONTRIBUTING.md` sets the bar a
new rule has to clear; this page covers how the code fits together and which
mistakes have already cost someone a debugging session.

## Setup

```
pip install -e ".[dev]"
pytest -q
```

The suite runs offline in about seven seconds. Calibration needs the corpus,
which downloads on demand:

```
python benchmarks/fetch.py
python benchmarks/run_calibration.py
```

Run the self-lint gate before you push, because CI runs it on every commit:

```
techlint --no-color --gate 4.0 README.md CONTRIBUTING.md CHANGELOG.md docs/
```

The tool holds its own documentation to the standard it enforces, so an edit
to any of those files can fail the build on its prose alone. Run that command
bare. Piping it into `less` or `tail` gives you the exit status of the pager,
which hides the failure you were checking for.

## How a lint run works

Everything flows through `lint_text` in `engine.py`, in four stages.

First `textmodel.parse` turns the source into a `Document` of paragraphs and
sentences. It strips markdown, skips fenced code and tables, and records the
source line and column of every surviving character. That position map is what
lets a finding point at the exact character that triggered it.

Second, the enabled batteries run. Each check is a function taking
`(doc, config)` and yielding `Finding` objects, and `batteries()` assembles the
list from the config flags.

Third, the baseline partitions the findings into reported and suppressed.

Fourth, scoring turns what survives into a weighted score per 1,000 words, a
per-axis breakdown, and a verdict band.

## The module map

| module | responsibility |
|---|---|
| `textmodel.py` | markdown parsing, sentence splitting, position tracking, specimen masking |
| `finding.py` | the `Finding` record, severity weights, axis assignment |
| `engine.py` | battery assembly, scoring, verdict bands |
| `checks_ai.py` | generated-text tics, tiered by measured effect size |
| `checks_clarity.py` | passive voice, buried verbs, wordiness, Gopen and Swan |
| `checks_docs.py` | style-guide conventions and accessibility |
| `checks_links.py` | offline reference validation |
| `stats.py` | distribution instruments over the whole document |
| `config.py` | project config, including the YAML fallback parser |
| `baseline.py` | suppression entries with mandatory reasons |
| `cli.py` | argument handling, path collection, output formats |

`config.py` carries its own minimal YAML parser so the package keeps zero
runtime dependencies. It handles the subset this tool needs. If you extend the
config schema, check the fallback path as well as the PyYAML path, because a
local machine with PyYAML installed will silently exercise only one of them.

## Adding a rule

Write the check as a generator over `doc.prose_sentences()` and yield findings
with a populated `why`, since that string is the evidence the tool shows the
person whose sentence you flagged. Register it in the battery list for its
area.

Then write both tests. The positive test proves the pattern matches. The
negative test proves the rule declines to match something similar and
legitimate, which is the harder and more valuable half.

Then re-run calibration. Treat a rule as an instrument bug when it fires above
roughly one hit per 1,000 words on the pre-LLM corpus, because that corpus
predates the thing being detected. Fix the rule rather than excusing the corpus.

## Files that are generated

`techlint/data/ai_excess_vocab.json` comes from `tools/build_excess_vocab.py`.
Change the tier cutoffs or the drop list in the script and regenerate, because
the next regeneration overwrites a hand edit without saying so.

`benchmarks/results/calibration.json` is committed and reproducible. Running
the harness against the fetched corpus should leave it unchanged. When it does
change, the instrument moved, and the documented figures have to move with it.

## Traps

**A parser change is a calibration change.** Sentence boundaries are the unit
most rules measure against, so a fix in `textmodel.py` shifts every rate even
when no rule was touched. Re-run calibration after touching the parser. This is
not theoretical: correcting the sentence splitter moved the known-good mean
from 2.12 to 2.14 in a release whose notes claimed the numbers had held.

**Numbers written in prose go stale silently.** The README advertised a corpus
size and a separation figure that the tool no longer produced, and nothing
caught it, because prose does not execute.
`tests/test_calibration_claims.py` now derives those figures from the committed
results and fails when a document disagrees.

**Position maps are load-bearing.** Every finding reports its location by
mapping an offset back through `Sentence.positions`. Changes to parsing or
masking need tests asserting that reported positions stay inside the document.
`tests/test_robustness.py` holds that invariant across 29 hostile inputs.

**Specimen masking exists for a reason.** A page about writing quotes every
pattern it names, and the tic catalog scored 98.7 before masking existed.
Setting `style.quoted_specimens: skip` blanks quoted spans while preserving
offsets. An apostrophe inside a word does not open a quote, which was a bug
once and is now pinned by a test.

**Watch for catastrophic backtracking.** Several patterns use bounded wildcards
that pathological input can punish. `tests/test_robustness.py` carries a bait
corpus with runtime assertions; add to it when you add a pattern of that shape.

## Releasing

Bump `version` in `pyproject.toml` and `__version__` in `techlint/__init__.py`
together, because a test fails when they disagree. Add a matching
`## <version>` section to `CHANGELOG.md`, which the pipeline publishes as the
release notes, then merge to `main`.

The workflow tags the commit, builds the artifacts, and publishes the release.
Re-running it is safe, because a push whose version already carries a tag exits
in seconds. Note that the tag is created server-side during the release rather
than pushed from a clone.

## The suppression baseline

`.techlint-baseline.jsonl` records reviewed exemptions, one JSON object per
line, and every entry needs a written `why`. Quotes match by prefix, so a
baselined hit survives small edits around it but not a rewrite of the phrase.

An empty quote is rejected when the file loads. It used to prefix-match
everything and silence a whole rule for a file, which is a silence rather than
a decision. For a document-level finding that reports a rate and has no phrase
to quote, use `"*"` as an explicit whole-document exemption.

The most valuable review outcome is deciding the rule itself is wrong. When
that happens, fix the rule, add a regression test, and re-run calibration.

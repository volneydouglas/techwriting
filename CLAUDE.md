# techlint — working notes

A technical-writing linter with AI-tic detection, calibrated against pre-LLM
technical prose. It answers one question: *how much does this document read like
unedited generated output, and where?*

It does **not** detect AI authorship. It cannot, the README says so on purpose,
and the predictable misuse of this category of tool is pointing a score at a
student or an employee as an accusation. Keep that line intact.

## Hard constraints

- **Zero runtime dependencies.** Standard library only. `pytest` is dev-only.
- **Python >= 3.9.** CI runs 3.9 and 3.12.
- **No network calls in the linting path.** Linting stays offline and deterministic.
- `techlint/data/ai_excess_vocab.json` is **generated**, not hand-edited. Change
  the cutoffs in `tools/build_excess_vocab.py` and regenerate, or the next
  regeneration silently reverts you.

## Commands

```sh
pip install -e ".[dev]" && pytest -q      # 289 tests, all should pass
techlint docs/                            # lint a tree
techlint --explain AI-VOCAB               # what a rule means and where it came from
techlint --baseline-suggest docs/         # emit exemption lines for review
python benchmarks/fetch.py && python benchmarks/run_calibration.py
```

## What CI enforces

1. `pytest -q` on 3.9 and 3.12.
2. `examples/before.md` must trip a gate of 10; `examples/after.md` must pass it.
   The before/after pair is a contract, so edit both together.
3. **Dogfood:** `techlint --gate 4.0 README.md CONTRIBUTING.md CHANGELOG.md CLAUDE.md docs/`.
   Prose added to this repo has to survive its own linter.
4. Known-good to known-bad separation stays above 20x, and the pre-LLM canon stays
   under 3.0. Below that, the instrument stopped discriminating.

`release.yml` runs the same gates on a version tag and must stay idempotent, so it
exits early when the version is already tagged. A new gate belongs in both
workflows, or carries a stated reason for living in only one.

`.coderabbit.yaml` points automated review at `CONTRIBUTING.md`'s evidence bar
rather than generic taste. Its `path_instructions` are the same standards, so read
them before changing a rule, and keep numbers cited in docs (calibration scores,
separation, test counts) matching the suite and
`benchmarks/results/calibration.json`.

## The bar for a new rule

Full version in `CONTRIBUTING.md`. The short form:

- **Evidence required.** Two independent style authorities for a clarity rule, or
  a measured effect size for an AI-tic rule. Taste is not evidence.
- **It must not fire on the canon.** RFCs and PEPs first published between 1981 and
  2001 predate the models, so anything a rule finds there is a false positive by
  construction. If your rule fires on them, **fix the rule, not the corpus.**

  One caveat to keep in mind before treating a canon hit as proof. RFCs are
  immutable once published, but PEPs are living documents: PEP 8 carries a 2013
  post-date on top of its 2001 original. `benchmarks/fetch.py` pulls the current
  page and caches it without a revision or checksum, so a PEP in the corpus is
  today's text, not a 2001 snapshot. The evidence is strong rather than airtight,
  and pinning revisions would make it airtight.
- **Both test directions**, and the negative test matters more. Anyone can write a
  regex that matches; the engineering is in what it declines to match. `allowing`
  and `ensuring` do real work in a trailing clause and stay unflagged.
- **Regression tests for fixed bugs go in `tests/test_bughunt.py`**, named after
  the failure mode, with the reproduction in the docstring.
  `tests/test_robustness.py` holds the backtracking bait corpus and the
  position-tracking invariants.
- **When torn between two severities, take the lower one.** A noisy linter gets
  turned off, and a linter that is off catches nothing.

## Exemptions and the baseline

Designed to over-flag slightly. About a quarter of `major` hits should be
overruled on review. Four exemption categories: proper noun (automatic), declared
`domain_vocabulary`, literal usage (grammatical-position guard), and quoted text.

Prefer `domain_vocabulary` in `techlint.yaml` over baselining hits one at a time.
It is one line, it carries its reason as a comment, and it covers the project.

`.techlint-baseline.jsonl` entries **require a `why`** and the loader refuses them
without one. Never add an entry without reading the hit in context. The most
valuable review verdict is **"the rule is wrong"** — fix the rule, add a test,
re-run calibration. Never fix a finding by weakening a document that was right.

## Gotchas

- `quoted_specimens: skip` in `techlint.yaml` exists because this repo documents
  AI tics and therefore quotes every one of them. Without it `docs/ai-tics.md`
  scores 98.7 for specimens it names on purpose.
- `benchmarks/known_bad.md` is excluded from linting by config. It is deliberately
  slop-dense, and that is the point.
- Calibration history: every round so far produced an instrument fix rather than a
  document verdict. PEP 8 was flagged 19 times for "underscores", which it uses to
  mean the `_` character. The fix was a grammatical-position guard, not an
  exception for PEP 8.
- **A green local suite does not mean a green CI.** PyYAML is a common transitive
  install, and `_parse_yaml` prefers it, so a machine that has it runs different
  code from CI, which has none. That gap once hid a bug that dropped every list
  item from the fallback parser, emptying `domain_vocabulary` and `exclude` for
  zero-dependency installs. Test `_parse_yaml_fallback` directly, never through
  `_parse_yaml`. Before trusting a local pass on anything config-related, re-run
  with `yaml` blocked from import.

## Writing prose in this repo

The dogfood gate applies, so follow the guide the repo ships
(`docs/style-guide.md`). The parts that bite most often:

- Cut the performance layer: no previews, no recaps, no claims that the topic is
  important. Documentation starts at the point and ends at its last fact.
- Active voice, imperative for procedures, warnings **before** the step with the
  consequence attached.
- Subject next to its verb; payload at the end of the sentence, where the emphasis
  falls.
- `must` for requirements, `can` for options. Avoid `should` and `shall`.
- **Never vary your terminology.** If it is a *panel* in step 1 it is not a *cover*
  in step 4. This is the exact inverse of the sibling fiction project, where a
  repeated distinctive word is the defect.
- Say the number. "significantly faster" is not a measurement.
- Run the bits test: what new fact did that sentence teach? No fact, cut it.

## What a linter cannot check, and what matters most

Verify every factual claim by hand. A model cannot know your system's limits,
failure modes, or version constraints, and those are the parts of a document that
earn their keep. Add the negative space: error cases, constraints, "do not do
this". Prose with no sharp edges means nobody has thought about failure yet.

## Agent safety, inherited from the sibling project

**Never let an agent edit prose open-endedly.** Use agents for read-only analysis
that returns quoted evidence. Make every creative fix yourself, one at a time. Run
mechanical passes only from an enumerated list of exact quotes, each verified to
match exactly once.

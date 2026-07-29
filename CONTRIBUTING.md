# Contributing

```
pip install -e ".[dev]"
pytest -q
```

Bug reports and rule proposals are welcome. The bar for a new rule is higher
than for most linters, for the reason explained below.

## Adding or changing a rule

A rule earns its place by surviving two questions.

**1. What is the evidence?**

Every rule cites either a published style authority or a measurement. "This
phrasing annoys me" is not evidence; neither is "an LLM wrote this once". For
clarity rules the standing bar is **two independent authorities** — Google,
Microsoft, the Federal Plain Language Guidelines, RFC 2119, Gopen & Swan. For
AI-tic rules it is a measured effect size or a corpus-verified rate. Put the
citation in the finding's `why` field and in `docs/research-basis.md`, so the
tool can explain itself to the person whose sentence it flagged.

**2. Does it fire on writing that is known to be good?**

```
python benchmarks/fetch.py
python benchmarks/run_calibration.py
```

The known-good corpus is technical prose written before LLMs existed — RFCs
and PEPs from 1981 to 2001. Anything a rule finds there is a false positive by
construction. A rule firing above roughly 1 per 1,000 words on that corpus is
an instrument bug, not a finding.

If your rule fires on the canon, **fix the rule, not the corpus.** Every
calibration round in this project's history produced an instrument fix rather
than a document verdict. The most instructive: PEP 8 was flagged 19 times for
"underscores", which it uses to mean the `_` character. The fix was a
grammatical-position guard, not an exception for PEP 8.

Then check the other direction: the known-bad fixture
(`benchmarks/known_bad.md`) must still score orders of magnitude worse. CI
fails if the separation drops below 20×.

## Severity

Severity is about **recognition risk and reader cost**, not how much the
pattern bothers you.

| level | weight | bar |
|---|---|---|
| `blocker` | 3.0 | no legitimate use in a technical document. Near-zero false positives. |
| `major` | 1.5 | wrong once confirmed in context — the exemption taxonomy applies |
| `minor` | 0.5 | budgeted: a few are fine, a pattern is not |
| `info` | 0.0 | metric or audit candidate. **Never gates a build.** |

If you are unsure between two levels, take the lower one. A noisy linter gets
turned off, and a linter that is off catches nothing.

## Tests

Every rule needs both directions:

```python
def test_participial_editorial(self):
    assert find("Latency dropped, underscoring the value of caching.", "AI-PHRASE")

def test_working_participle_not_flagged(self):
    # "allowing" does real work; calibration found it in pre-LLM prose.
    assert not find("The lock is released, allowing the client to retry.", "AI-PHRASE")
```

The negative test matters more than the positive one. Anyone can write a regex
that matches; the engineering is in what it declines to match.

## Vocabulary data

`techlint/data/ai_excess_vocab.json` is generated, not hand-edited:

```
python tools/build_excess_vocab.py
```

To change which words appear, change the tier cutoffs or the domain-literal
drop list in that script and regenerate. Hand-editing the JSON means the next
regeneration silently reverts you.

## Things that will be turned down

- Rules based on taste with no citation.
- Anything that implies the tool detects AI authorship. It does not, it cannot,
  and the README says so deliberately. The predictable misuse of this category
  of tool is pointing a score at a student or an employee as an accusation.
- Rules that only make sense inside one house style. Make it a config option.
- Network calls in the linting path. Linting stays offline and deterministic.
- Runtime dependencies. The stdlib-only constraint is a feature.

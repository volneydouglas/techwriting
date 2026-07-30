# The exemption taxonomy

A detector that never over-flags is a detector that misses things. techlint is
designed to over-flag slightly, and this is the machinery that keeps that
usable. Adapted from the prose-smells project, with the categories re-derived
for technical writing.

**Every `major` finding gets a context review against these four exemptions
before anyone "fixes" it.** Roughly a quarter of flags *should* be overruled.
If you are accepting every flag, you are sanding the voice off your docs; if
you are overruling most of them, the instrument needs retuning, not the prose.

## 1. Proper noun

Handled automatically: a capitalized match mid-sentence is skipped. *Delve
Labs*, *Realm* the database, *Harness* the CI product.

## 2. Domain vocabulary — declared once

The big one for technical writing. Your product genuinely has a wiring harness;
your auth system genuinely has a realm; your SRE docs genuinely mean *robust*
in its engineering sense. Declare these in `techlint.yaml`:

```yaml
domain_vocabulary:
  - harness      # the test harness this page documents
  - realm        # Kerberos realm
  - robust       # reliability property, used literally
```

Declared words are never flagged as AI vocabulary. Prefer this over baselining
each hit: it is one line, it carries the reason as a comment, and it applies
across the whole project.

## 3. Literal usage — partly automatic

Several excess-vocabulary words have a common literal sense in technical
writing where the noun is legitimate and only the *verb* is the tell. techlint
detects the grammatical position for a built-in set:

| word | literal (allowed) | tell (flagged) |
|---|---|---|
| underscore | "names may use leading **underscores**" | "this **underscores** the need for retries" |
| realm | "set the **realm** before you authenticate" | "in the **realm** of possibility" |
| harness | "attach the wiring **harness**" | "**harness** the power of your data" |

Calibration found this, not guesswork: PEP 8 (2001) says
"underscores" 19 times, meaning the `_` character.

## 4. Quoted or attributed text

Prose you are quoting is not prose you wrote. techlint already skips fenced
code blocks, inline code, and tables. For quoted prose such as an upstream
changelog, a vendor's wording, or a screenshot transcript, baseline it with
that as the reason.

---

## The suppression baseline

For anything the four categories above do not cover, record the exemption in
`.techlint-baseline.jsonl`:

```json
{"rule": "AI-VOCAB", "file": "docs/api.md", "quote": "delves",
 "why": "quoted verbatim from the upstream 3.2 changelog"}
```

Generate candidate lines, then edit each one:

```
techlint --baseline-suggest docs/ >> .techlint-baseline.jsonl
```

Document-level findings (`AI-DASH`, `AI-VOCAB-DENSITY`, `DOC-READABILITY`,
and the other rate reporters) have no phrase to quote. For those, set
`"quote": "*"`: an explicit whole-document exemption for that rule in that
file. An empty quote is rejected outright; it used to match everything by
accident, and a silence should never be an accident.

Three rules, non-negotiable:

1. **Never add an entry without reading the hit in context.** The baseline is
   where you record a judgment, not where you silence a nuisance.
2. **`why` is required** — techlint refuses to load a baseline entry without
   one. An entry with no reason is not an exemption, it is an unexamined
   suppression.
3. **Quotes match by prefix**, so a baselined hit survives small edits around
   it but not a rewrite of the phrase itself. If you rewrite it, you get to
   decide again.

Once the baseline is clean, wire `--gate` into CI. New hits then fail loudly
and reviewed ones stay quiet.

## Verdicts in a context review

For each `major` hit, record one of:

- **scrub** — a real tic; fix it per the suggestion.
- **baseline** — legitimate, with a written reason.
- **instrument bug** — the rule is wrong. Fix the rule, add a test, and
  re-run `benchmarks/run_calibration.py`. Never fix a finding by weakening a
  document that was right.

The third verdict is the valuable one. Every calibration round in this repo's
history produced at least one, and the instrument is better for it.

# Calibration

> An instrument you never check against known quantities is a random-number
> generator with good production values.

**Prime directive: when the instrument fires hard on work that is known to be
good, suspect the instrument.** A 1981 RFC scoring badly is evidence about the
ruler, not the RFC.

## The two controls

### Known-good: pre-LLM technical canon

`benchmarks/fetch.py` downloads technical prose that is unambiguously human,
unambiguously good, and written long before November 2022 — so any tic found in
it is a false positive by construction. The corpus is **dimension-mapped**:
each text is a fixture for a specific instrument.

The corpus covers all four [Diátaxis](https://diataxis.fr/) genres. Genre
moves the numbers as much as age does, and a corpus of specifications alone
tunes the thresholds for specifications.

| text | genre | calibrates |
|---|---|---|
| RFC 793 (TCP) | reference | dense spec prose; heavy legitimate passive |
| RFC 1035 (DNS) | reference | reference prose mixed with tables |
| RFC 2119 | reference | normative keyword discipline at its source |
| PEP 8 | reference | prescriptive guidance, imperative mood |
| PEP 257 | reference | convention prose |
| Python 3.8 tutorial (intro, control flow) | tutorial | second person, worked examples |
| Python 3.8 HOWTO (logging, argparse) | how-to | task-oriented, imperative |
| Python 3.8 FAQ (design) | explanation | rationale and trade-offs |
| RFC 1925 (*The Twelve Networking Truths*) | control | **the humility fixture** — aphoristic and jokey; it *should* trip the tic detectors and it is canon |
| PEP 20 | control | extreme brevity |

Python 3.8 URLs are used deliberately: that documentation set was frozen in
2019 and cannot have been touched by an LLM.

### What genre diversity changed

Adding tutorials and how-to guides moved the known-good mean from 1.38 to
2.12, and the top of the range from 6.08 to 4.36 spread across more texts.
Tutorials address the reader directly, reassure them, and use second person
throughout — all of which reads warmer to a tic detector than a protocol
specification does.

The verdict bands were re-anchored as a result: `clean` moved from < 4 to < 5
so that every canon text, in every genre, still lands in it. Anchoring on
specifications alone would have made every well-written tutorial look
defective.

The RFC 1925 role is borrowed from Moby-Dick's role in the NQE corpus: a
standing counter-example to the idea that "flagged" means "wrong". Deliberate
aphorism is a legitimate register a narrow signal cannot distinguish from a
defect.

### Known-bad: `benchmarks/known_bad.md`

A committed, deliberately slop-dense fixture. Without it, a rule that fires on
nothing looks identical to a rule that works.

## Running it

```
python benchmarks/fetch.py            # ~46k words, cached, gitignored
python benchmarks/run_calibration.py  # writes benchmarks/results/calibration.json
```

Re-run after **every** detector change. The committed results make the numbers
reviewable without re-fetching.

## Current numbers

| measure | value |
|---|---|
| known-good weighted mean | **2.12** /1k words (12 texts, ~47k words) |
| known-good range | 1.18 (RFC 1035) – 4.36 (RFC 1925, the humility fixture) |
| known-bad fixture | **151.8** |
| **separation** | **72×** |

Verdict bands are anchored to these, not guessed: `clean` < 5, `light` < 12,
`moderate` < 30, `heavy` ≥ 30. Override them per project with `bands:` in
`techlint.yaml`. Real specification prose has to sit comfortably
inside `clean`, and it does.

## The improvement loop

```
calibration finding  ->  fix the instrument  ->  add a regression test
                     ->  re-run calibration  ->  update the bands
```

This is the only sanctioned way a threshold changes. Four rounds ran while
building this tool, and every one found an instrument bug rather than a
document defect:

| round | change | canon wscore | separation |
|---|---|---|---|
| 1 | first run | 7.36 | 20.6× |
| 2 | passive made mode-aware; `STAT-ECHO` opt-in; mild vocab tier demoted to density-only | 4.88 | 29.9× |
| 3 | sentence-length tiers softened; corpus HTML hygiene fixed | 2.04 | 70.5× |
| 4 | homograph guard (`underscores` the character vs the verb); working participles excluded | 1.38 | 108.6× |
| 5 | style-guide battery added; `DOC-CONDESCEND` split by grammatical role; `DOC-ACRONYM` made opt-in | 1.78 | 85.3× |
| 6 | corpus extended to all four Diátaxis genres; bands re-anchored | 2.12 | 71.6× |

Rounds 5 and 6 raise the known-good number, which looks like a regression and
is not. Round 5 added eleven new rules; round 6 added five new texts in genres
the corpus had never covered. A number that stays flat while the instrument
grows is a number that has stopped measuring.

Round 4 is the illustrative one. PEP 8 was flagged 19 times for "underscores" —
which it uses to mean the `_` character. The finding was real, the rule was
wrong, and the fix was a grammatical-position guard plus a test, not a change
to PEP 8.

## Things the corpus taught us

- **Protocol specs are legitimately passive.** "The URG flag is set when urgent
  data is sent" has no useful actor. Passive is only a defect where someone
  must act on it, which is why the rule is now mode-aware.
- **Repetition is correctness, not sloppiness.** Technical documents restate
  field names, state names, and constraints on purpose.
- **Long sentences are a style era.** RFC-era prose runs long. That is a fact
  about 1981, not a defect to gate a build on.
- **Site chrome poisons a corpus.** The first run produced three phantom
  British-spelling findings in PEP 20 that came from the page's dark-mode
  theme-switcher label, hidden inside a nested inline SVG. Check your corpus
  before you trust your numbers.

## Adding your own corpus

The shipped corpus is small and skewed toward specifications. Point
`benchmarks/fetch.py` at your own pre-2022 documentation — that is a better
reference for your house style than any RFC — and re-derive the bands. A rule
that fires on your own good, old docs is a rule to demote.

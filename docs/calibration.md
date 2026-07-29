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

| text | calibrates |
|---|---|
| RFC 1925 (*The Twelve Networking Truths*) | **the humility fixture** — aphoristic and jokey; it *should* trip the tic detectors and it is canon |
| RFC 2119 | normative keyword discipline at its source |
| RFC 793 (TCP) | dense spec prose; heavy legitimate passive |
| RFC 1035 (DNS) | reference prose mixed with tables |
| PEP 8 | prescriptive guidance, imperative mood |
| PEP 20 | extreme brevity |
| PEP 257 | convention prose |

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
| known-good weighted mean | **1.38** /1k words |
| worst known-good text | 6.08 (PEP 8) |
| known-bad fixture | **149.8** |
| **separation** | **108×** |

Verdict bands are anchored to these, not guessed: `clean` < 4, `light` < 10,
`moderate` < 25, `heavy` ≥ 25. Real specification prose has to sit comfortably
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

Round 4 is the illustrative one. PEP 8 was flagged 19 times for "underscores" —
which it uses to mean the `_` character. The finding was real, the rule was
wrong, and the fix was a grammatical-position guard plus a test, not a change
to PEP 8.

## Things the corpus taught us

- **Protocol specs are legitimately passive.** "The URG flag is set when urgent
  data is sent" has no useful actor. Passive is only a defect where a reader
  needs to act on it, which is why the rule is now mode-aware.
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

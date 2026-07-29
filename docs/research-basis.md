# Research basis

Every rule in techlint traces to either a published style authority, an
empirical study, or a calibration measurement made in this repository. This
page records which is which, so you can argue with a rule on its merits.

## AI signal

### The vocabulary list is measured, not guessed

**Kobak D., González-Márquez R., Horvát E.-Á., Lause J. (2025). "Delving into
LLM-assisted writing in biomedical publications through excess vocabulary."
*Science Advances* 11(30).** Data: `github.com/berenslab/llm-excess-vocab` (MIT).

The authors tracked word frequencies across ~15 million PubMed abstracts from
2010 to 2024 and identified words whose 2024 frequency broke sharply from the
pre-LLM trend. They estimate at least 13.5% of 2024 abstracts were LLM-processed,
reaching 40% in some subcorpora. The vocabulary shift exceeded the one caused by
the COVID-19 pandemic.

`tools/build_excess_vocab.py` reproduces their counterfactual — a linear
extrapolation of the 2021→2022 trend into 2024 — and tiers the 407 words they
annotate as *style* (rather than content) words by effect size:

| tier | ratio | severity | examples |
|---|---|---|---|
| strong | ≥ 5.0× | major | delves (28.2×), underscores (13.8×), meticulously (11.3×), showcasing (10.7×), intricacies (10.3×) |
| moderate | ≥ 2.5× | minor | encompassing (4.7×), emphasizing (4.7×), formidable (4.1×), meticulous (3.8×) |
| mild | ≥ 1.6× | *density only* | notably, additionally, potentially |
| — | < 1.6× | dropped | using (1.04×), however (1.01×), analysis (1.01×), were (0.96×) |

That last row is the reason to tier rather than ban. A flat list of "AI words"
flags ordinary technical English and buries the real signal.

**The mild tier is never reported per-instance.** Calibration found mild-tier
words in RFC 793, published in 1981. A word that appears in a document written
four decades before GPT is not evidence of GPT. Mild words feed
`AI-VOCAB-DENSITY` only, where a *concentration* still means something.

### Structural markers

Stylometric surveys of AI-generated text consistently report **more present
participial clauses**, more phrasal coordination, more that-clause subjects,
rigid transition scaffolding, hedging, and lower burstiness (sentence-length
variance) than human writing. techlint implements the checkable subset:

| rule | marker |
|---|---|
| `AI-PHRASE` (participial-editorial) | trailing participial clause that editorializes: ", underscoring the importance of…" |
| `AI-OPENER` | rigid transition scaffolding |
| `AI-HEDGE` | hedge stacking |
| `AI-UNIFORM` | low sentence-length variance |
| `AI-TRIAD` | reflexive rule-of-three |

Relevant reading: *Linguistic Characteristics of AI-Generated Text: A Survey*
(2025); *Benchmark of stylistic variation in LLM-generated texts*
(arXiv:2509.10179); *Explaining Generalization of AI-Generated Text Detectors
Through Linguistic Analysis* (arXiv:2601.07974).

### Reference validation, from sloppylint

[sloppylint](https://github.com/rsionnach/sloppylint) detects AI slop in Python
*code*, and its best idea transfers directly: it validates that imported
packages actually exist, because a
[USENIX study](https://arxiv.org/abs/2406.10279) found roughly a fifth of
AI-suggested imports name packages that do not.

Prose has the same failure mode in a different costume — generated
documentation confidently links to files, sections, and anchors that were never
written. `AI-LINK` checks relative link targets against the filesystem and
heading anchors against the actual headings. Offline, deterministic, no
dependencies. External URLs are deliberately out of scope: checking them needs
the network and turns every CI run into someone else's uptime problem.

Two other ideas came from the same project:

- **Axis breakdown.** sloppylint splits its score into noise / lies / style /
  structure rather than reporting one number. techlint's equivalent —
  fabrication / filler / clarity / structure — says what *kind* of editing a
  document needs, not just how much.
- **`AI-PROSE-RATIO`.** Found by running techlint against sloppylint's own
  README: of 297 lines, only 254 words were prose; the rest was tables, badges,
  and bullets. A document built almost entirely from scaffolding performs
  organization while escaping prose analysis entirely.

### Patterns from the prose-smells project

The copula daisy-chain, countdown negation, self-posed Q&A, inflated copula,
and antithesis templates come from a sibling project applying the same
code-smell framing to fiction, which verified the copula chain at **zero
occurrences in ~1M words of human fiction**. So does the whole
severity/weighted-score/baseline architecture.

## Clarity rules

No rule survives here unless at least two independent authorities agree.

| rule | authorities |
|---|---|
| `CLARITY-PASSIVE` | Google developer documentation style guide (active by default, passive allowed when the actor is irrelevant); Microsoft Writing Style Guide; Federal Plain Language Guidelines |
| `CLARITY-NOMINAL` | Federal Plain Language Guidelines ("use verbs, not hidden verbs"); Gopen & Swan; Williams, *Style* |
| `CLARITY-WORDY` | Federal Plain Language Guidelines; ISO 24495-1:2023 |
| `CLARITY-SVDIST` | Gopen & Swan principle 1: "grammatical subjects should be followed as soon as possible by their verbs" |
| `CLARITY-STRESS` | Gopen & Swan principle 3: "information intended to be emphasized should appear at points of syntactic closure" |
| `CLARITY-PARA` | Gopen & Swan principle 2: "every unit of discourse should serve a single function"; ASD-STE100 6.5–6.6 |
| `CLARITY-INCLUSIVE` | Google, Microsoft, ASD-STE100 GR-7 |
| `CLARITY-LATIN` | Google style guide; plain-language guidance; ASD-STE100 GR-6 |
| `CLARITY-NORMATIVE` | RFC 2119 keyword discipline; ASD-STE100 reaches the same conclusion independently |
| `CLARITY-THAT` | ASD-STE100 GR-1; documented machine-translation aid |
| `CLARITY-LENGTH` | budget only — no authority sets a hard cap outside controlled languages |

**Gopen G. D. & Swan J. A. (1990). "The Science of Scientific Writing."**
*American Scientist* 78(6), 550–558 — the source of the reader-expectation
model behind `CLARITY-SVDIST` and `CLARITY-STRESS`. Readers have fixed
expectations about *where* in a sentence information appears: the topic
position carries context, the stress position carries emphasis.

## Calibration

Thresholds and verdict bands are derived from measurement, not taste. See
[calibration.md](calibration.md). Current numbers: pre-LLM technical canon
scores a weighted mean of **1.38**; the deliberately slop-dense fixture scores
**149.8** — a separation of **108×**.

## What this system cannot do

It cannot tell you whether a machine wrote a document. Nothing can, reliably.
Human marketing prose trips these rules; careful AI-assisted prose does not.
What the score measures is how much a text reads like *unedited* generated
output — which is a defect worth fixing regardless of who or what produced it.

# Rules removed from the ASD-STE100 layer

The first version of this tool implemented ASD-STE100 (Simplified Technical
English) directly. STE is a genuinely good standard — for aircraft maintenance
manuals, which is what it was built for. Much of it does not generalize, and
applying it to ordinary technical documentation produced confident nonsense.

This page records what was removed and why. Rules that survived did so because
Google, Microsoft, the Federal Plain Language Guidelines, Gopen & Swan, or
RFC 2119 independently say the same thing — see
[research-basis.md](research-basis.md).

## Removed

### The approved-word dictionary (`STE-DICT`) — rules 1.1–1.13

STE permits 875 approved words plus project-declared technical nouns. Everything
else is an error with a prescribed replacement. Outside aviation this produces:

| flagged word | STE's prescribed replacement | in context |
|---|---|---|
| chip | PARTICLE (n) | on a semiconductor document |
| security | "make sure … correctly attached" | on a security page |
| profile | CONTOUR (n) | on a user-profile API |
| great | LARGE (adj) | anywhere |
| real | AGREE (v) | anywhere |
| choice | SELECTION (n) | anywhere |

The mapping is correct *per the standard* and wrong for every document that is
not an aircraft manual. The whole dictionary layer is gone, along with the
extraction tooling and the recurring-errors list built on it.

A small, defensible remnant survives as `CLARITY-WORDY`: multi-word phrases
with a genuine one-word equivalent ("in order to" → "to", "utilize" → "use"),
each backed by plain-language guidance rather than by STE's vocabulary.

### The semicolon ban — rule 8.1

STE forbids the semicolon outright. Google, Microsoft, and Chicago all permit
it. Removed entirely.

### Blanket bans on perfect and progressive tenses — rules 3.2, 3.4

STE permits only simple present, simple past, simple future, infinitive,
imperative, and the past participle as an adjective. "The operator **has
adjusted** the linkage" is an error under STE. In general technical writing it
is ordinary correct English. Removed.

What survives is narrower and defensible: **agentless obligation**
("the value must be configured" — by whom?) still fires, but only in
`procedure` mode, where a reader genuinely needs to know who acts.

### The 20-word sentence cap — rule 5.1

A hard cap is workable only alongside a controlled vocabulary that keeps
sentences simple. Without it the cap fights normal syntax. Replaced by a
per-mode **budget** (`procedure` 20, `reference` 30, `narrative` 40) that emits
`info` at the budget and `minor` only past 1.5× it — a calibration decision, see
below.

### The STE word count — rules 8.4–8.7

STE counts a parenthetical, a number-plus-unit, an abbreviation, or a
hyphenated word as one word each. These exist to make the 20-word cap workable.
With the cap gone they are just a confusing word count. techlint counts plainly:
one token, one word.

### Three-word compound-noun limit — rules 2.1–2.2

"engine fuel filter housing retaining bolt" is a real aviation problem. In
software documentation, `AuthenticationTokenValidationService` is a class name.
Removed.

### Contractions — rule 4.2

STE forbids them. Google's developer documentation style guide explicitly
*allows* them. Now off by default, available via `style.contractions: flag`.

### -ing forms — rule 3.5

STE permits "-ing" only inside technical nouns. Too broad for general prose.
The valuable part was kept and sharpened by research: the **trailing
participial clause that editorializes** (", underscoring the importance of…")
is both a clarity problem and one of the most consistent LLM syntactic markers.
It now lives in `AI-PHRASE` as `participial-editorial`, and verbs that do real
work in that position (`allowing`, `enabling`, `ensuring`) are deliberately
excluded after calibration found them in pre-LLM prose.

## Demoted by calibration, not by principle

These fired too often on human pre-LLM technical writing. The fix went into the
instrument, never into the finding.

| rule | before | after | evidence |
|---|---|---|---|
| `CLARITY-PASSIVE` | fired on all passives | mode-aware; only named-agent passives outside `procedure` mode | 14.8 → 0.77 hits/1k on canon. RFC 793 is legitimately full of "is set", "is sent" — in a protocol spec the actor genuinely does not matter |
| `STAT-ECHO` | on by default | opt-in (`budgets.echo_ngrams`) | 14.1/1k on canon — the worst in the battery. Technical documents repeat long phrases on purpose |
| `AI-VOCAB` mild tier | reported individually | density signal only | mild-tier words appear in RFC 793 (1981) |
| `CLARITY-LENGTH` | minor / major | info / minor | 213 over-budget vs 30 well-over hits on canon; specs run long, and that is a style-era fact |

## The inversion worth knowing

The prose-smells project treats a repeated distinctive word as a defect: in
fiction, the reader starts hearing it. **Technical writing is the opposite** —
terminology consistency *requires* repetition, and varying your term for the
same thing is the bug. That is why rare-word-reuse was not ported and why
`STAT-ECHO` is off by default.

# The AI tic catalog

Patterns characteristic of unedited LLM output in technical writing — the prose
equivalent of code smells. Rule IDs in parentheses are checked automatically;
the rest belong in review.

**A tic is not proof a machine wrote something,** and it is not automatically
wrong. Human marketing copy trips most of these. That is the point: they mark
writing that optimizes for *sounding* informed over *being* informative, which
is a defect in documentation regardless of authorship.

Two properties make a tic worth listing. It has to be **recognizable** — once a
reader notices the pattern, every later instance costs — and it has to be
**cheap to fix**. Severity is about recognition risk, not literary merit.

## Layer 1 — Artifacts (`AI-ARTIFACT`, blocker)

Text with no legitimate place in a technical document at all.

- **Chat frame**: "As an AI language model…", "My knowledge cutoff is…"
- **Assistant pleasantries**: "I hope this helps", "Great question!",
  "Certainly! Here's…", "Let me know if you'd like…"
- **Unfilled placeholders**: `[Your Company Name]`, `{{product}}`, lorem ipsum
- **Appeals to unnamed studies**: "Studies show that…" with no citation — the
  characteristic shape of a fabricated reference

These are blockers because the false-positive rate is near zero and the cost of
shipping one is a credibility hit.

## Layer 2 — Constructions (`AI-PHRASE`)

### Throat-clearing (major)
"It's important to note that…", "It should be noted that…", "It's worth
mentioning…" → delete and state the point. If it weren't important you wouldn't
be writing it.

### Scene-setting (major)
"In today's fast-paced digital landscape…", "In an era where…" → delete the
clause. No document was ever improved by it.

### Importance claims (major)
"X plays a crucial role in Y", "the importance of X cannot be overstated" →
say what X *does*, or what breaks without it.

### The antithesis template (major)
"It's not just X — it's Y." "This isn't merely a cache; it is a coordination
layer." "It's more than just a linter."

A strawman erected to be knocked down. One is rhetoric; three is a generator's
rhythm. State the one thing that is true.

The narrower figure **"X, not Y"** ("This is a map, not a verdict") is `minor`
and budgeted — it is a legitimate move used once.

### Self-posed Q&A (major)
"The result? Latency halved." "The catch? It only works on Linux." → state the
answer as a sentence.

### Countdown negation (major)
"Not fast. Not cheap. Just correct." → one sentence saying what it is.

### Participial editorializing (major)
"Latency dropped, **underscoring** the value of caching."

The single most consistent *syntactic* marker — stylometric research finds
present participial clauses elevated in AI text, and this is the editorializing
variant. Make it its own sentence, or delete the editorial.

Note the deliberate exclusion: `allowing`, `enabling`, `ensuring`, `causing` do
real work in a trailing clause ("the lock is released, allowing the client to
retry") and calibration found them throughout pre-LLM prose. They are not
flagged.

### Inflated copula (major)
"serves as a", "functions as a", "stands as a", "is a testament to" → `is`, or
the concrete verb.

### False suspense (major)
"Here's the thing…", "But here's the catch…" → manufactured tension in a
document the reader is scanning. Delete.

### Listicle preview and essay closer (major)
"In this article, we'll explore…" → that is what headings are for.
"In conclusion…", "At the end of the day…" → documentation ends at its last
fact, not with a summary of itself.

### Advertising register (major)
"unlock the full potential of", "take X to the next level", "supercharge",
"game-changer", "let's dive in", "without further ado", "buckle up".

### Minor patterns
Vague quantifiers ("a wide range of", "a myriad of"), empty transitions ("when
it comes to", "in the realm of"), consensus claims ("few would disagree"),
authority-by-assertion ("best practices", "industry-standard"), and elaboration
that promises specifics and never delivers ("each with its own").

## Layer 3 — Vocabulary (`AI-VOCAB`, tiered)

Measured, not guessed. Words are tiered by how far their post-LLM frequency
exceeded the pre-LLM trend across 15M abstracts (Kobak et al. 2025 — see
[research-basis.md](research-basis.md)).

**Strong (≥5×, major):** delves · underscores · meticulously · showcasing ·
intricacies · intricate · surpassing · commendable · excels · grappling ·
renowned · realm · garnered · revolutionize · escalating · expediting ·
pioneers

**Moderate (≥2.5×, minor):** encompassing · emphasizing · formidable ·
groundbreaking · meticulous · swift · adept · heightened · bolstering ·
advancements · uncharted · poised · unveiled · notable · fostering · necessitating

**Mild (≥1.6×):** never reported individually — they appear in documents from
1981. They feed `AI-VOCAB-DENSITY` only.

**The test for any of them:** replace the word with a plain synonym or a
concrete fact. If the sentence loses nothing, the word was filler. "Robust
error handling" → *which* failure does it survive? "Seamless integration" →
*which* manual step disappears?

## Layer 4 — Structure and distribution

| rule | signal |
|---|---|
| `AI-DASH` | em-dash density above budget — sustained interruption is a current-model rhythm |
| `AI-TRIAD` | three-item lists in a large share of sentences; items 2–3 are usually padding |
| `AI-OPENER` | sentences opening with *Moreover, Furthermore, Additionally* instead of content |
| `AI-HEDGE` | three or more hedges in one sentence — the confidence goes to zero |
| `AI-INTENSIFY` | intensifier density; emphasis substituting for evidence |
| `AI-BOLDLIST` | runs of `**Term:** one clause.` — performs organization while each item stays too thin to use |
| `AI-UNIFORM` | low sentence-length variance (burstiness) |
| `AI-COPULA` | the copula daisy-chain — zero occurrences in ~1M words of human prose |
| `AI-PROSE-RATIO` | most of the document is tables and bullets rather than prose |
| `STAT-STALL` | adjacent paragraphs restating one idea |
| `STAT-ABSTRACT` | long, abstract sentences carrying few new facts |

## Layer 4b — References that do not exist (`AI-LINK`)

The one part of the semantic layer that *is* checkable. Generated
documentation links confidently to files and sections nobody wrote:

- a relative link to `setup.md` when no such file exists
- an anchor `#configuration` when the document has no such heading
- a cross-file anchor where the file is real and the section is not

This is the prose form of a hallucinated import, and it is worth more than any
vocabulary check because it is unambiguous: the target either resolves or it
does not. External URLs are not checked — that needs the network.

## Layer 5 — Semantic (manual; the ones that matter most)

No linter catches these. They are the difference between text that sounds right
and text that *is* right.

- **Confident hallucination.** Precise-sounding claims with no source: API
  parameters that do not exist, version numbers, benchmark figures. *Every
  factual claim in AI-drafted text needs verification before it ships.* Run the
  commands. Click the links.
- **The bits test.** After every sentence: *what new fact did the reader just
  learn?* Count facts, divide by words. A long sentence carrying one fact — or
  none — is inflation. If you cannot state the fact in plain English, the
  sentence has no fact; cut it.
- **Symmetric both-sidesing.** "While X offers advantages, it also presents
  challenges." Applied to everything, it says nothing. Which one, and when?
- **Vacuous elaboration.** A sentence restating the previous one in fancier
  words. If it adds no fact, constraint, or instruction, cut it.
- **Generic examples.** `foo`, `John Doe`, "Acme Corp" presented as real.
- **Missing negative space.** AI drafts describe the happy path. Real docs earn
  their keep at the edges: error cases, limits, version constraints, "do not do
  this". Prose with no sharp edges means nobody has thought about failure yet.

## The review protocol

1. `techlint docs/` — clear the mechanical tics. The weighted score tells you
   how deep the edit needs to go (canon: ~1.4; unedited generated draft: 100+).
2. **Verify every fact** — names, numbers, APIs, commands, versions, quotes.
3. **Cut the performance layer** — previews, recaps, importance claims,
   audience flattery. Technical docs start at the point.
4. **Add the negative space** — limits, failure modes, prerequisites. The
   things a model could not know because they live in your system.
5. **Read it aloud once.** If you can hear the cadence, so can your reader.

And the process rule the prose-smells project learned the hard way:
**never let an agent edit prose open-endedly.** Use agents for read-only
analysis that returns quoted evidence. Make every creative fix yourself, one at
a time. Mechanical passes only from an enumerated list of exact quotes, each
verified to match exactly once.

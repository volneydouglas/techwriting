# Technical Writing Style Guide

A working style guide for technical documentation: READMEs, API reference,
runbooks, design docs, release notes. Synthesized from the Google developer
documentation style guide, the Microsoft Writing Style Guide, the Federal Plain
Language Guidelines, Gopen & Swan's reader-expectation model, and the parts of
ASD-STE100 that generalize beyond aviation.

What techlint can check is marked with its rule ID. The rest is for your
self-edit.

## 1. Write for the action

Decide what you need the reader to **do** or **know**, then write that.

- **Procedures**: imperative, one instruction per step, condition first.
  - ✗ "The retaining bolts should then be removed after ensuring power has been
    disconnected." *(who removes them?)* — `CLARITY-PASSIVE`
  - ✓ "Disconnect the power. Remove the four retaining bolts."
- **Reference**: state what the thing is, then what it does, then the
  constraints. The reader arrives mid-scan; they will not read your intro.
- **Warnings before the step, never after**, with the consequence attached:
  - ✓ "**Warning:** Do not run this against production. It drops the table."

Cut the performance layer entirely: no previews of what the document will
cover, no recaps of what it covered, no claims that the topic is important.
Headings do the first job, the reader does the second, and their presence here
does the third.

## 2. Put information where readers look for it

This is Gopen & Swan's contribution, and it is the least-known high-leverage
idea in technical writing. Readers have fixed structural expectations:

- **Subjects want their verbs immediately.** Every word between them is held in
  working memory. — `CLARITY-SVDIST`
  - ✗ "The configuration file, which the installer writes on first run and
    which several later steps depend on, is stored in `/etc`."
  - ✓ "The installer writes the configuration file to `/etc` on first run.
    Several later steps depend on it."
- **The end of a sentence is the emphatic position.** Put the payload there,
  not a trailing qualifier. — `CLARITY-STRESS`
  - ✗ "The service retries three times before giving up, in most cases."
  - ✓ "In most cases the service retries three times, then gives up."
- **The start of a sentence carries context.** Open with something the reader
  already knows; that is what links it to the previous sentence.
- **One unit, one point.** One topic per paragraph, one idea per sentence. —
  `CLARITY-PARA`

## 3. Prefer plain, active constructions

- **Active voice by default.** Passive is fine when the actor genuinely does not
  matter — protocol specs are full of legitimate passive — but not when a
  reader has to act. "The value must be configured" raises the question *by
  whom?* — `CLARITY-PASSIVE`
- **Verbs, not buried verbs.** "Calculate the checksum", not "perform a
  calculation of the checksum". — `CLARITY-NOMINAL`
- **One word, not four.** "to" not "in order to"; "because" not "due to the
  fact that"; "can" not "has the ability to". — `CLARITY-WORDY`
- **Say the number.** "significantly faster" is not a measurement; "40% faster
  on the 99th percentile" is.

## 4. One term, one meaning

- **Never vary your terminology.** If it is a *panel* in step 1 it is not a
  *cover* in step 4. Elegant variation is a bug — this is the exact inverse of
  fiction, where repetition is the defect.
- **`must` for requirements, `can` for options.** Avoid `should` and `shall` in
  procedures: both leave the reader unsure whether they have a choice. —
  `CLARITY-NORMATIVE`, following RFC 2119.
- **Gender-neutral, always.** "they", "you", or repeat the noun. Replace
  `whitelist`/`blacklist` with `allowlist`/`denylist`. — `CLARITY-INCLUSIVE`
- **English, not Latin.** "for example" not "e.g." — it translates poorly and is
  routinely confused with "i.e." — `CLARITY-LATIN`
- **Keep "that" after `make sure`, `verify`, `confirm`.** It marks where the
  clause starts and helps both readers and translators. — `CLARITY-THAT`

## 5. Budgets, not rules

techlint sets sentence and paragraph budgets per mode rather than hard caps,
because no authority outside controlled languages sets a hard cap:

| mode | sentence budget | use for |
|---|---|---|
| `procedure` | 20 words | runbooks, installation steps, work instructions |
| `reference` | 30 words | API docs, specifications, explanatory prose |
| `narrative` | 40 words | design docs, release narratives, blog posts |

Going over is `info`. Going 1.5× over is `minor`. Pre-LLM specification prose
runs long and that is a fact about the genre, not a defect.

## 6. If a machine helped write it

Run the [AI tic review](ai-tics.md) before anything else, then verify every
factual claim by hand. A model cannot know your system's limits, failure modes,
or version constraints — and those are the parts of a document that earn their
keep.

## Editing workflow

1. **Draft** freely. Do not lint while drafting.
2. **`techlint <file>`** — fix blockers and majors; treat minors as defects
   unless you can say why not.
3. **Self-edit** for what no linter sees: terminology consistency, condition-
   first ordering, ambiguous pronouns, and whether each paragraph earns its
   place.
4. **Verify facts** — run the commands, click the links, check the versions.
5. **Read it aloud.** Any sentence you have to re-read is a rewrite candidate.

## Quick reference

| Write | Not |
|---|---|
| Remove the cover. | The cover should be removed. |
| Make sure that the valve is open. | Ensure the valve is open. |
| If the light is on, stop the test. | Stop the test if the light happens to be on. |
| The pump supplies fuel to the engine. | Fuel is supplied to the engine by the pump. |
| Calculate the checksum. | Perform a calculation of the checksum. |
| To proceed, restart the service. | In order to proceed, restart the service. |
| The cache holds 100 entries. | The cache is designed to hold a wide range of entries. |
| Latency dropped 40%. | Latency dropped, underscoring the value of caching. |
| This guide covers the retry API. | In this guide, we'll dive into the retry API. |
| **Warning:** This drops the table. | Be careful when running this. |

## Out of scope

Terminology management (keep a project glossary), document architecture
(S1000D, DITA, Diátaxis), and illustration style. Keep your glossary beside
this guide and treat it as the authority techlint's `domain_vocabulary` points at.

"""Clarity checks for technical writing.

Every rule here is supported by at least two independent authorities, and none
of them are specific to aviation maintenance manuals. Where a rule came from
ASD-STE100 it survived only because Google, Microsoft, the Federal Plain
Language Guidelines, or Gopen & Swan say the same thing. Rules that existed
only to serve the STE controlled vocabulary (the 875-word dictionary, the
semicolon ban, the three-word compound-noun cap, the blanket ban on perfect
and progressive tenses) are gone -- see docs/removed-rules.md for the list and
the reasoning.

Sources are recorded per-check in the `why` field and collected in
docs/research-basis.md.
"""

import re

from .finding import Finding, Severity

# -- passive voice ---------------------------------------------------------
IRREGULAR_PP = (
    "been|begun|bent|blown|broken|brought|built|caught|chosen|cut|done|drawn|"
    "driven|fallen|fed|felt|found|frozen|given|gone|ground|grown|held|hidden|"
    "hit|hung|kept|known|laid|led|left|lost|made|meant|met|put|read|run|said|"
    "seen|sent|set|shaken|shown|shut|sold|spoken|spun|stolen|stuck|swung|taken|"
    "taught|thought|thrown|told|torn|understood|withdrawn|won|worn|written"
)
PP = rf"(?:\w+ed|{IRREGULAR_PP})"
ADV = r"(?:\w+ly\s+|not\s+|also\s+)?"

PASSIVE_BY_RE = re.compile(rf"\b(?:am|is|are|was|were|been|being)\s+{ADV}({PP})\s+by\b", re.I)
MODAL_PASSIVE_RE = re.compile(
    rf"\b(must|should|shall|can|will|would|may|might)\s+{ADV}be\s+{ADV}({PP})\b", re.I)
PASSIVE_RE = re.compile(rf"\b(?:is|are|was|were)\s+{ADV}({PP})\b(?!\s+by\b)", re.I)

# Past participles that are ordinary adjectives after a copula -- "is required",
# "is supported", "is deprecated" describe a state, not an action done to
# something. Flagging these is the classic passive-detector false positive.
STATE_ADJECTIVES = {
    "required", "supported", "deprecated", "enabled", "disabled", "allowed",
    "permitted", "available", "expected", "recommended", "installed",
    "configured", "documented", "supported", "limited", "restricted",
    "reserved", "encoded", "signed", "unsigned", "sorted", "nested",
    "connected", "authenticated", "authorized", "cached", "compressed",
    "escaped", "qualified", "scoped", "typed", "versioned", "located",
    "based", "related", "associated", "intended", "designed", "known",
    "closed", "open", "opened", "done", "finished", "complete", "completed",
}

# -- nominalization --------------------------------------------------------
# Plain-language authorities and Gopen & Swan agree: a verb buried inside a
# noun costs the reader an extra step. "Perform a calculation of" -> "calculate".
NOMINAL_VERBS = r"(?:perform|performs|performed|make|makes|made|do|does|did|" \
                r"conduct|conducts|conducted|carry out|carries out|carried out|" \
                r"provide|provides|provided|give|gives|gave|undertake|take)"
NOMINALIZATION_RE = re.compile(
    rf"\b{NOMINAL_VERBS}\s+(?:an?|the)\s+(\w+(?:tion|ment|ance|ence|sis|ing|al))\b",
    re.I)
NOMINAL_FIX = {
    "calculation": "calculate", "adjustment": "adjust", "installation": "install",
    "modification": "modify", "configuration": "configure", "evaluation": "evaluate",
    "examination": "examine", "inspection": "inspect", "verification": "verify",
    "validation": "validate", "comparison": "compare", "measurement": "measure",
    "assessment": "assess", "analysis": "analyze", "decision": "decide",
    "selection": "select", "connection": "connect", "replacement": "replace",
    "removal": "remove", "deployment": "deploy", "migration": "migrate",
    "conversion": "convert", "reduction": "reduce", "improvement": "improve",
    "determination": "determine", "recommendation": "recommend",
    "description": "describe", "definition": "define", "review": "review",
    "backup": "back up", "update": "update", "upgrade": "upgrade",
}

# -- subject-verb distance (Gopen & Swan) ----------------------------------
# "Grammatical subjects should be followed as soon as possible by their verbs."
# We approximate: an opening noun phrase interrupted by a long modifier before
# the first finite verb.
SV_INTERRUPT_RE = re.compile(
    r"^((?:The|This|These|Those|A|An|Each|Every|Any)\s+\w+(?:\s+\w+){0,2})"
    r"((?:,|\s+(?:which|that|who|whose|where|when))\s+.{25,}?)"
    r"(\s+(?:is|are|was|were|has|have|had|will|can|must|should|does|do|"
    r"provides?|returns?|contains?|requires?|allows?|causes?|uses?)\b)", re.I)

# -- weak stress position (Gopen & Swan) -----------------------------------
# "Information intended to be emphasized should appear at points of syntactic
# closure." A sentence that trails off into a hedge or a throwaway prepositional
# tail wastes its most emphatic slot.
WEAK_ENDING_RE = re.compile(
    r"(?:,\s*(?:however|though|as well|too|of course|if any|in general|"
    r"among others|for example|for instance|in most cases|by default))\s*[.!?]?\s*$",
    re.I)

# -- other generalizable rules ---------------------------------------------
LATIN_ABBREVS = {
    "e.g.": "for example", "i.e.": "that is", "etc.": "and so on (or finish the list)",
    "et al.": "and others", "cf.": "compare with", "viz.": "namely",
    "n.b.": "note", "ca.": "approximately",
}
LATIN_RE = re.compile(
    r"(?<![\w.])(e\.g\.|i\.e\.|etc\.?(?=[\s,;)]|$)|et al\.|cf\.|viz\.|n\.b\.)", re.I)

GENDERED_RE = re.compile(r"\b(he|she|him|her|his|hers|himself|herself|he/she|s/he)\b", re.I)
GENDERED_COMPOUNDS = {
    "manpower": "staffing, workforce", "man-hours": "person-hours",
    "manhours": "person-hours", "mankind": "people", "manned": "crewed, staffed",
    "unmanned": "uncrewed, automatic", "man-made": "manufactured, artificial",
    "chairman": "chair", "workmanlike": "skillful", "tradesman": "technician",
    "workman": "worker", "middleman": "intermediary", "layman": "non-specialist",
    "layman's": "plain-language", "master/slave": "primary/replica",
    "blacklist": "denylist, blocklist", "whitelist": "allowlist",
}
GENDERED_COMPOUND_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, GENDERED_COMPOUNDS), key=len, reverse=True))
    + r")\b", re.I)

# RFC 2119 keyword discipline: in normative technical text "should" and "shall"
# are not interchangeable with "must".
RFC2119_RE = re.compile(r"\b(shall|should)\b(?!\s+not\s+be\s+construed)", re.I)

BRITISH = {
    "colour": "color", "behaviour": "behavior", "flavour": "flavor",
    "labour": "labor", "neighbour": "neighbor", "vapour": "vapor",
    "centre": "center", "metre": "meter", "litre": "liter", "fibre": "fiber",
    "analyse": "analyze", "analysed": "analyzed", "analysing": "analyzing",
    "catalogue": "catalog", "dialogue": "dialog", "organise": "organize",
    "organised": "organized", "organisation": "organization",
    "recognise": "recognize", "utilise": "utilize", "minimise": "minimize",
    "maximise": "maximize", "optimise": "optimize", "initialise": "initialize",
    "customise": "customize", "authorised": "authorized", "licence": "license",
    "defence": "defense", "grey": "gray", "programme": "program",
    "travelled": "traveled", "modelling": "modeling", "labelled": "labeled",
    "cancelled": "canceled", "signalling": "signaling", "fulfil": "fulfill",
    "enrol": "enroll", "aluminium": "aluminum",
}
BRITISH_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, BRITISH), key=len, reverse=True)) + r")\b",
    re.I)
US_TO_GB = {v: k for k, v in BRITISH.items()}
US_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, US_TO_GB), key=len, reverse=True)) + r")\b",
    re.I)

CONTRACTION_RE = re.compile(
    r"\b\w+[’'](?:t|re|ve|ll|d|m)\b|\b(?:it|he|she|that|there|what|who|let)[’']s\b", re.I)

# A dropped "that" only matters when a *clause* follows: "make sure the valve
# is open". "Check the agent log at /var/log" is an imperative with a plain
# object and needs no "that" — requiring a following finite verb separates the
# two. (Found by dogfooding: the rule fired on examples/after.md.)
MAKE_SURE_RE = re.compile(
    r"\b(make[s]?\s+sure|verify|confirm|ensure|check)\s+"
    r"(?!that\b|of\b|to\b|for\b|whether\b|if\b)"
    r"((?:the|a|an|all|each|every|no|it|you|there)\b"
    r"(?:\s+\w+){0,3}?\s+"
    r"(?:is|are|was|were|has|have|had|does|do|did|can|will|should|must)\b)",
    re.I)

WORDY = {
    "in order to": "to", "in order for": "for", "due to the fact that": "because",
    "for the purpose of": "to", "in the event that": "if",
    "at this point in time": "now", "at the present time": "now",
    "in the near future": "soon", "a large number of": "many",
    "a majority of": "most", "in spite of the fact that": "although",
    "with regard to": "about", "with respect to": "about",
    "in relation to": "about", "prior to": "before", "subsequent to": "after",
    "in the process of": "(delete)", "it is possible that": "may",
    "has the ability to": "can", "is able to": "can", "are able to": "can",
    "make use of": "use", "utilize": "use", "utilise": "use",
    "in conjunction with": "with", "on a regular basis": "regularly",
    "in a timely manner": "promptly", "the reason why is that": "because",
}
WORDY_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, WORDY), key=len, reverse=True)) + r")\b",
    re.I)


# -- checks ----------------------------------------------------------------

def check_sentence_length(doc, config):
    """Budget, not a ban. Long sentences are a reading-cost signal.

    Calibration (2026-07-29): the over-budget tier fired 213 times across
    pre-LLM technical canon versus 30 for the well-over tier. Specifications
    genuinely run long and that is a style-era fact, not a defect, so the first
    tier is INFO (zero weight) and only sentences past 1.5x the budget carry
    any score.
    """
    limit = config.sentence_words
    for s in doc.prose_sentences():
        n = len(s.words)
        if n > limit * 1.5:
            sev, note = Severity.MINOR, "well over"
        elif n > limit:
            sev, note = Severity.INFO, "over"
        else:
            continue
        yield Finding(
            rule="CLARITY-LENGTH", severity=sev,
            message=f"Sentence is {n} words ({note} the {limit}-word "
                    f"{config.mode} budget).",
            line=s.line, col=s.col, extract=_clip(s.text),
            suggestion="split it, or move the list into a vertical list",
            why="reading cost rises sharply with clause count (plain-language guidance)")


def check_paragraph_length(doc, config):
    limit = config.paragraph_sentences
    for p in doc.paragraphs:
        if p.kind != "prose" or len(p.sentences) <= limit:
            continue
        s = p.sentences[0]
        yield Finding(
            rule="CLARITY-PARA", severity=Severity.INFO,
            message=f"Paragraph has {len(p.sentences)} sentences (budget {limit}).",
            line=s.line, col=s.col,
            suggestion="one topic per paragraph; split at the topic shift",
            why="Gopen & Swan: every unit of discourse should serve a single point")


def check_passive_voice(doc, config):
    """Passive voice, graded by how much the missing actor actually costs.

    Calibration (2026-07-29) fired this at 14.8/1k on pre-LLM technical canon
    -- RFC 793 is full of "is set", "is sent", "MUST be transmitted", and that
    prose is correct: in a protocol specification the actor genuinely does not
    matter. So the rule is now mode-aware:

      procedure mode  -- a reader must know who acts. Agentless obligation is
                         MINOR; bare passive is INFO.
      other modes     -- only passive with a *named* agent ("X is done by Y")
                         is reported, because that one is always rewritable
                         and always shorter active.
    """
    procedural = config.mode == "procedure"
    for s in doc.prose_sentences():
        spans = []
        for m in PASSIVE_BY_RE.finditer(s.text):
            spans.append(m.span())
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-PASSIVE", severity=Severity.MINOR,
                message=f"Passive with a named agent: \"{_clip(m.group(0))} …\".",
                line=line, col=col, extract=m.group(0),
                suggestion="make the agent the subject — always shorter",
                why="Google and Microsoft style guides both default to active voice")
        if not procedural:
            continue
        for m in MODAL_PASSIVE_RE.finditer(s.text):
            # STATE_ADJECTIVES deliberately does NOT apply here: "must be
            # configured" is an obligation even though "is configured" is a
            # state. The modal is what makes it an instruction.
            if any(m.start() >= a and m.end() <= b for a, b in spans):
                continue
            spans.append(m.span())
            line, col = s.pos_at(m.start())
            verb = _verb_base(m.group(2))
            yield Finding(
                rule="CLARITY-PASSIVE", severity=Severity.MINOR,
                message=f"Obligation with no actor: \"{_clip(m.group(0))}\" — "
                        "who does this?",
                line=line, col=col, extract=m.group(0),
                suggestion=f"use the imperative (\"{verb.capitalize()} the …\") "
                           "or name the actor",
                why="in a procedure the reader must know who acts; "
                    "agentless obligation is the main source of unactionable steps")
        for m in PASSIVE_RE.finditer(s.text):
            if any(m.start() >= a and m.end() <= b for a, b in spans):
                continue
            if m.group(1).lower() in STATE_ADJECTIVES:
                continue
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-PASSIVE", severity=Severity.INFO,
                message=f"Possible passive: \"{_clip(m.group(0))}\".",
                line=line, col=col, extract=m.group(0),
                suggestion="active voice unless the actor is unknown or irrelevant",
                why="Google style guide: prefer active; passive is fine when the actor does not matter")


def check_nominalizations(doc, config):
    for s in doc.prose_sentences():
        for m in NOMINALIZATION_RE.finditer(s.text):
            noun = m.group(1).lower()
            verb = NOMINAL_FIX.get(noun)
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-NOMINAL", severity=Severity.MINOR,
                message=f"Buried verb: \"{_clip(m.group(0))}\".",
                line=line, col=col, extract=m.group(0),
                suggestion=f"use the verb: \"{verb}\"" if verb
                           else "use the verb form directly",
                why="Federal Plain Language Guidelines: use verbs, not hidden verbs")


def check_wordiness(doc, config):
    for s in doc.prose_sentences():
        for m in WORDY_RE.finditer(s.text):
            fix = WORDY.get(m.group(0).lower(), "")
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-WORDY", severity=Severity.MINOR,
                message=f"Wordy phrase: \"{m.group(0)}\".",
                line=line, col=col, extract=m.group(0),
                suggestion=f"\"{fix}\"" if fix else "shorten",
                why="Federal Plain Language Guidelines: omit unnecessary words")


def check_subject_verb_distance(doc, config):
    """Gopen & Swan principle 1: subjects want their verbs quickly."""
    for s in doc.prose_sentences():
        m = SV_INTERRUPT_RE.match(s.text)
        if not m:
            continue
        gap = len(m.group(2).split())
        if gap < 8:
            continue
        yield Finding(
            rule="CLARITY-SVDIST", severity=Severity.INFO,
            message=f"{gap} words separate \"{m.group(1).strip()}\" from its verb "
                    f"\"{m.group(3).strip()}\".",
            line=s.line, col=s.col, extract=_clip(s.text),
            suggestion="move the interrupting clause to its own sentence, "
                       "or after the verb",
            why="Gopen & Swan: readers hold the subject in memory until the verb arrives")


def check_stress_position(doc, config):
    """Gopen & Swan principle 3: the end of the sentence is the emphatic slot."""
    for s in doc.prose_sentences():
        if len(s.words) < 12:
            continue
        m = WEAK_ENDING_RE.search(s.text)
        if not m:
            continue
        line, col = s.pos_at(m.start())
        yield Finding(
            rule="CLARITY-STRESS", severity=Severity.INFO,
            message=f"Sentence trails off into \"{m.group(0).strip(' .')}\".",
            line=line, col=col, extract=_clip(s.text),
            suggestion="end on the information that matters; move the qualifier earlier",
            why="Gopen & Swan: the stress position is where readers place emphasis")


def check_latin_abbreviations(doc, config):
    if not config.flags("latin_abbreviations"):
        return
    for s in doc.prose_sentences():
        for m in LATIN_RE.finditer(s.text):
            key = m.group(0).lower()
            fix = LATIN_ABBREVS.get(key) or LATIN_ABBREVS.get(key + ".", "")
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-LATIN", severity=Severity.INFO,
                message=f"Latin abbreviation \"{m.group(0)}\".",
                line=line, col=col, extract=m.group(0), suggestion=fix,
                why="Google style guide and plain-language guidance: use English; "
                    "translates poorly and is often misused")


def check_inclusive_language(doc, config):
    for s in doc.prose_sentences():
        for m in GENDERED_RE.finditer(s.text):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-INCLUSIVE", severity=Severity.MINOR,
                message=f"Gendered pronoun \"{m.group(0)}\" for a generic person.",
                line=line, col=col, extract=m.group(0),
                suggestion="\"they\", \"you\", or repeat the noun",
                why="Google, Microsoft, and ASD-STE100 all require gender-neutral text")
        for m in GENDERED_COMPOUND_RE.finditer(s.text):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-INCLUSIVE", severity=Severity.MINOR,
                message=f"Non-inclusive term \"{m.group(0)}\".",
                line=line, col=col, extract=m.group(0),
                suggestion=GENDERED_COMPOUNDS.get(m.group(0).lower(), ""),
                why="industry style guides list these as replaceable")


def check_normative_keywords(doc, config):
    """RFC 2119 discipline: "should" and "shall" are ambiguous obligations."""
    if config.mode != "procedure":
        return
    for s in doc.prose_sentences():
        for m in RFC2119_RE.finditer(s.text):
            word = m.group(0).lower()
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-NORMATIVE", severity=Severity.INFO,
                message=f"\"{m.group(0)}\" leaves the obligation ambiguous.",
                line=line, col=col, extract=m.group(0),
                suggestion="\"must\" if it is required, \"can\" if it is optional"
                           if word == "shall" else
                           "\"must\" if required; if genuinely advisory, say why",
                why="RFC 2119 keyword discipline; ASD-STE100 reaches the same conclusion")


def check_spelling_locale(doc, config):
    rx, table, label = ((BRITISH_RE, BRITISH, "British") if config.locale == "us"
                        else (US_RE, US_TO_GB, "American"))
    for s in doc.prose_sentences():
        for m in rx.finditer(s.text):
            fix = table.get(m.group(0).lower())
            if not fix:
                continue
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-LOCALE", severity=Severity.INFO,
                message=f"{label} spelling \"{m.group(0)}\" "
                        f"(locale is {config.locale}).",
                line=line, col=col, extract=m.group(0), suggestion=fix,
                why="internal consistency; set `locale` in techlint.yaml")


def check_contractions(doc, config):
    if not config.flags("contractions"):
        return
    for s in doc.prose_sentences():
        for m in CONTRACTION_RE.finditer(s.text):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-CONTRACTION", severity=Severity.INFO,
                message=f"Contraction \"{m.group(0)}\".",
                line=line, col=col, extract=m.group(0),
                suggestion="write the words in full",
                why="house style (`style.contractions`); note Google's guide allows contractions")


def check_that_conjunction(doc, config):
    for s in doc.prose_sentences():
        for m in MAKE_SURE_RE.finditer(s.text):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="CLARITY-THAT", severity=Severity.INFO,
                message=f"\"{m.group(0)} …\": the dropped \"that\" hides the "
                        "clause boundary.",
                line=line, col=col, extract=m.group(0),
                suggestion=f"{m.group(1)} that {m.group(2)}",
                why="ASD-STE100 GR-1; also a documented machine-translation aid")


IRREGULAR_BASE = {
    "been": "be", "built": "build", "brought": "bring", "caught": "catch",
    "chosen": "choose", "done": "do", "drawn": "draw", "driven": "drive",
    "found": "find", "given": "give", "gone": "go", "held": "hold",
    "kept": "keep", "known": "know", "laid": "lay", "left": "leave",
    "lost": "lose", "made": "make", "meant": "mean", "met": "meet",
    "run": "run", "said": "say", "seen": "see", "sent": "send", "set": "set",
    "shown": "show", "sold": "sell", "spoken": "speak", "taken": "take",
    "taught": "teach", "thought": "think", "thrown": "throw", "told": "tell",
    "torn": "tear", "understood": "understand", "won": "win", "worn": "wear",
    "written": "write", "put": "put", "read": "read", "cut": "cut",
    "hit": "hit", "shut": "shut", "hidden": "hide", "frozen": "freeze",
}
# Bases ending in silent-e whose -ed stem gives no orthographic clue.
# "created" -> "creat" and "edited" -> "edit" look identical in shape, so the
# ambiguous ones live in a list. The bug-hunt found the previous heuristic
# producing "Disconnecte the ..." and "Adjuste the ..." in suggestions.
_E_BASES = {
    "create", "update", "delete", "validate", "invalidate", "generate",
    "migrate", "integrate", "iterate", "calculate", "calibrate", "allocate",
    "deallocate", "duplicate", "replicate", "terminate", "eliminate",
    "evaluate", "escalate", "populate", "simulate", "translate", "isolate",
    "enumerate", "authenticate", "communicate", "indicate", "initiate",
    "associate", "activate", "deactivate", "rotate", "annotate", "propagate",
    "configure", "ensure", "measure", "restore", "store", "ignore", "require",
    "acquire", "compare", "declare", "share", "prepare", "capture", "secure",
    "structure", "restructure", "expire", "retire",
    "cache", "place", "replace", "trace", "reduce", "produce", "introduce",
    "notice", "service", "release", "increase", "decrease", "parse", "reverse",
    "traverse", "merge", "purge", "charge", "change", "exchange", "manage",
    "stage", "encode", "decode", "upgrade", "downgrade", "include", "exclude",
    "provide", "divide", "close", "expose", "dispose", "compose", "pause",
    "complete", "execute", "compute", "route", "distribute", "contribute",
    "rotate", "mute", "define", "combine", "examine", "determine", "refine",
    "tune", "invoke", "revoke", "promote", "demote", "note", "quote",
    "name", "rename", "file", "compile", "profile", "resolve", "solve",
    "involve", "reserve", "observe", "serve", "preserve", "save", "type",
    "escape", "use", "reuse", "invite", "recite", "delegate", "aggregate",
}


def _verb_base(pp: str) -> str:
    """Best-effort base form of a past participle, for imperative suggestions.

    Order matters:
      irregulars -> doubled consonant ("stopped") -> -ied ("applied") ->
      endings English never leaves bare (v, z, soft c, u, consonant+l) ->
      the silent-e list -> the bare stem.
    "adjust", "disconnect", "install", "monitor", and "edit" fall through to
    the bare stem, which is the correct base for all of them.
    """
    w = pp.lower()
    if w in IRREGULAR_BASE:
        return IRREGULAR_BASE[w]
    if not w.endswith("ed"):
        return w
    stem = w[:-2]
    if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiouls":
        return stem[:-1]                      # stopped -> stop
    if stem.endswith("i"):
        return stem[:-1] + "y"                # applied -> apply
    # English orthography does not end words in bare v, z, soft c, u, or a
    # consonant+l cluster (other than ll): remove, analyze, produce, argue,
    # enable. "install" (ll) and "fail" (vowel+l) are excluded on purpose.
    if re.search(r"(?:[vzcu]|qu|[^aeioul]l)$", stem):
        return stem + "e"
    if stem + "e" in _E_BASES:
        return stem + "e"                     # created -> create, cached -> cache
    return stem


def _clip(t: str, n: int = 78) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1] + "…"


CLARITY_CHECKS = [
    check_sentence_length,
    check_paragraph_length,
    check_passive_voice,
    check_nominalizations,
    check_wordiness,
    check_subject_verb_distance,
    check_stress_position,
    check_latin_abbreviations,
    check_inclusive_language,
    check_normative_keywords,
    check_spelling_locale,
    check_contractions,
    check_that_conjunction,
]

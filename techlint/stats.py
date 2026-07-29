"""Statistical layer: distribution tells that per-instance regex cannot see.

Adapted from the prose-smells project's `stat_tells.py`, with one important
inversion for technical writing:

    In fiction, a repeated distinctive word is a defect. In technical writing,
    a repeated term is *correct* -- terminology consistency requires it. So
    rare-word-reuse is NOT ported. What survives is the instrument that catches
    repetition of *ideas* rather than terms.

Everything here emits AUDIT CANDIDATES at INFO severity. They never gate a
build and they are never scrub lists.
"""

import re
from collections import defaultdict

from .finding import Finding, Severity

STOP = set("""the a an and or but of to in on at for with from by as is was were are be
been being it its this that these those you your we our they them their not no so if
then than when while what which who whom had has have do did does would could should
will shall may might must there here out up down over under again once very just also
too only own same such about into through during before after above below all any both
each few more most other some can cannot only per via using use used
""".split())


def _content_words(text: str):
    return {w for w in re.sub(r"[^a-z0-9' -]", " ", text.lower()).split()
            if len(w) >= 4 and w not in STOP}


def check_stall_pairs(doc, config, threshold=0.32):
    """Adjacent paragraphs restating one idea -- prose clone detection.

    The fiction project calibrated its threshold at the human-corpus p99
    (0.115) over narrative paragraphs. Technical prose legitimately shares far
    more vocabulary between adjacent paragraphs (the same API, the same
    subsystem), so the default here is much higher and this stays INFO-only.
    Tune `stall_jaccard` in techlint.yaml against your own corpus before
    trusting it.
    """
    threshold = float(config.budgets.get("stall_jaccard", threshold))
    paras = [p for p in doc.paragraphs if p.kind == "prose"]
    for a, b in zip(paras, paras[1:]):
        ta = " ".join(s.text for s in a.sentences)
        tb = " ".join(s.text for s in b.sentences)
        if len(ta.split()) < 30 or len(tb.split()) < 30:
            continue
        wa, wb = _content_words(ta), _content_words(tb)
        if not wa or not wb:
            continue
        j = len(wa & wb) / len(wa | wb)
        if j >= threshold:
            yield Finding(
                rule="STAT-STALL", severity=Severity.INFO,
                message=f"Adjacent paragraphs share {j:.0%} of their content "
                        "words — the second may restate the first.",
                line=b.sentences[0].line, col=b.sentences[0].col,
                extract=_clip(tb),
                suggestion="if the second adds no new fact, cut it or merge",
                why="vacuous elaboration: many words, no new information",
                meta={"jaccard": round(j, 3)})


def check_echo_ngrams(doc, config, n=12):
    """Repeated n-grams within a document: copy-paste or generated boilerplate.

    OFF BY DEFAULT. Calibration verdict (2026-07-29): this instrument fired at
    14.1/1k on pre-LLM technical canon -- the worst false-positive rate in the
    battery. Technical documents repeat long phrases on purpose: state-machine
    enumerations, repeated field descriptions, page headers in converted text.
    Ported from fiction, where sentence reuse is a genuine defect; in technical
    writing it is usually correctness. Enable with `stats.echo: true` once you
    have measured your own corpus.
    """
    if not config.budgets.get("echo_ngrams", False):
        return
    sents = doc.prose_sentences()
    toks, origin = [], []
    for s in sents:
        for w in re.sub(r"[^a-z0-9' -]", " ", s.text.lower()).split():
            toks.append(w)
            origin.append(s)
    seen = defaultdict(list)
    for i in range(len(toks) - n + 1):
        gram = " ".join(toks[i:i + n])
        if sum(1 for w in gram.split() if w not in STOP) < 4:
            continue
        seen[gram].append(origin[i])
    for gram, where in seen.items():
        if len(where) < 2:
            continue
        lines = sorted({s.line for s in where})
        if len(lines) < 2:
            continue
        yield Finding(
            rule="STAT-ECHO", severity=Severity.INFO,
            message=f"{len(lines)}x repeated phrase across lines "
                    f"{', '.join(map(str, lines[:5]))}.",
            line=lines[1], col=1, extract=_clip(gram),
            suggestion="intentional boilerplate is fine; accidental reuse is not — "
                       "link to one canonical statement instead",
            why="repeated long n-grams are copy-paste or generated filler")


def check_empty_abstraction(doc, config):
    """Sentences that are long, abstract, and add few new content words.

    The deterministic half of the "bits test" from the prose-smells project:
    *what new fact did the reader just learn?* This ranks candidates; only a
    human (or an LLM pass) can answer the semantic question.
    """
    ABSTRACT_SUFFIX = ("tion", "ness", "ity", "ence", "ance", "ism", "ment", "ility")
    ABSTRACT = {"approach", "solution", "framework", "paradigm", "ecosystem",
                "landscape", "synergy", "value", "impact", "insight", "journey",
                "experience", "capability", "potential", "opportunity",
                "challenge", "innovation", "transformation", "strategy"}
    recent = []
    for s in doc.prose_sentences():
        cw = _content_words(s.text)
        if len(s.words) < 18:
            recent = (recent + [cw])[-3:]
            continue
        seen = set().union(*recent) if recent else set()
        novel = cw - seen
        abstract = {w for w in cw
                    if w in ABSTRACT or (len(w) > 6 and w.endswith(ABSTRACT_SUFFIX))}
        ratio = len(abstract) / max(len(cw), 1)
        # Two independent routes: a sentence that repeats what came before
        # while sounding abstract, OR one that is abstract enough on its own.
        # Without the second clause a standalone bloated sentence never fires,
        # because every content word in it counts as novel.
        if (len(novel) <= 4 and ratio >= 0.35) or ratio >= 0.55:
            yield Finding(
                rule="STAT-ABSTRACT", severity=Severity.INFO,
                message=f"{len(s.words)} words, {len(novel)} new content words, "
                        f"{ratio:.0%} abstract nouns.",
                line=s.line, col=s.col, extract=_clip(s.text),
                suggestion="state the fact in plain words first; if there is no "
                           "fact, cut the sentence",
                why="the bits test: long sentence, little new information",
                meta={"novel": len(novel), "abstract_ratio": round(ratio, 2)})
        recent = (recent + [cw])[-3:]


def _clip(t: str, n: int = 78) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1] + "…"


STAT_CHECKS = [
    check_stall_pairs,
    check_echo_ngrams,
    check_empty_abstraction,
]

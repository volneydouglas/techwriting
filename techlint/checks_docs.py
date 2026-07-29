"""Documentation conventions: rules from the major style guides and standards.

Where `checks_clarity` covers sentence-level craft, this module covers the
conventions that documentation standards agree on — link text, acronyms,
heading structure, addressing the reader, and the words that make a reader
feel small.

Sources per rule are in the `why` field and collected in
docs/research-basis.md. The heaviest hitters:

  Google developer documentation style guide  developers.google.com/style
  Microsoft Writing Style Guide               learn.microsoft.com/style-guide
  WCAG 2.1                                    w3.org/TR/WCAG21
  Carroll, J. (1990). The Nurnberg Funnel     (minimalism / action-orientation)
  Diátaxis                                    diataxis.fr
"""

import re

from .finding import Finding, Severity
from .textmodel import scan_text

# -- link text (Google, Microsoft, WCAG 2.4.4) -----------------------------
LINK_TEXT_RE = re.compile(r"\[([^\]\n]{1,80})\]\(\s*[^)\s]+[^)]*\)")
VAGUE_LINK_TEXT = {
    "click here", "here", "this link", "link", "this", "read more",
    "learn more", "more", "see here", "this page", "this article",
    "this document", "click", "go here", "download", "read this",
    "find out more", "check it out", "this guide",
}
BARE_URL_TEXT_RE = re.compile(r"^(?:https?://|www\.)")

# -- condescension (Google word list, Microsoft top-10 tips) ---------------
# Split by what the word does. Calibration (2026-07-29) found this rule at
# 1.34/1k on pre-LLM canon, almost all of it "simple" and "easy" used as
# ordinary adjectives -- RFC 821 is the *Simple* Mail Transfer Protocol, and
# "a simple algorithm" describes the algorithm, not the reader's experience.
#
# ALWAYS: adverbs and phrases that minimize the reader's effort. There is no
#         legitimate technical sense of "obviously" or "simply run this".
CONDESCENDING_ALWAYS = {
    "simply": "delete; if the step is short the reader will notice",
    "easily": "delete",
    "obviously": "delete; if it were obvious you would not be writing it",
    "clearly": "delete",
    "of course": "delete",
    "trivially": "delete, or give the actual effort",
    "painless": "delete",
    "effortless": "delete",
    "merely": "delete",
    "simply put": "delete",
    "needless to say": "delete",
    "everyone knows": "delete",
    "as you know": "delete; you cannot know what the reader knows",
    "it goes without saying": "delete",
}
# READER-DIRECTED ONLY: adjectives that are fine describing a thing and
# condescending when describing the reader's task. Flagged only in frames like
# "it is easy to", "this is simple", "very straightforward".
CONDESCENDING_ADJ = {
    "easy": "delete; what is easy for you may not be easy for the reader",
    "easier": "say than what, and by how much",
    "simple": "delete, or say what makes it short",
    "straightforward": "delete, or describe the steps",
    "trivial": "delete, or give the actual effort",
    "quick": "give the actual time",
    "quickly": "give the actual time",
}
CONDESCENDING_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, CONDESCENDING_ALWAYS), key=len,
                              reverse=True)) + r")\b", re.I)
# "it's easy to", "this is simple", "should be straightforward", "very easy"
READER_DIRECTED_RE = re.compile(
    r"\b(?:it(?:'s|’s| is| was)|that(?:'s|’s| is)|this (?:is|was)|"
    r"(?:should|will|can) be|are|is|very|quite|really|pretty|fairly|"
    r"makes? it|find(?:s|ing)? (?:it|this))\s+"
    r"(" + "|".join(sorted(map(re.escape, CONDESCENDING_ADJ), key=len,
                           reverse=True)) + r")\b"
    r"|\b(" + "|".join(sorted(map(re.escape, CONDESCENDING_ADJ), key=len,
                              reverse=True)) + r")\s+to\s+\w+", re.I)

# "just" is a genuine word in these senses; do not flag them.
JUST_LEGITIMATE = re.compile(
    r"\bjust\s+(?:in\s+time|now|about|as\b|before|after|then|cause|so|when)\b|"
    r"\b(?:is|are|was|were|be)\s+just\b(?=\s*[.,;])", re.I)
JUST_RE = re.compile(r"\bjust\b", re.I)

# -- politeness and permission phrasing (Google word list) ------------------
POLITENESS_RE = re.compile(
    r"\bplease\s+(?:note|see|refer|be\s+aware|remember|ensure|make\s+sure|"
    r"run|use|enter|click|select|check|contact|do|try|read|follow|install)\b"
    r"|\bplease\s+note\s+that\b", re.I)

ALLOWS_RE = re.compile(
    r"\ballows?\s+(?:you|users?|the\s+user|developers?|clients?)\s+to\b"
    r"|\benables?\s+(?:you|users?|the\s+user)\s+to\b"
    r"|\bgives?\s+(?:you|the\s+user)\s+the\s+ability\s+to\b", re.I)

# -- addressing the reader (Google, Microsoft: use second person) -----------
THIRD_PERSON_RE = re.compile(
    r"\b(?:the|a|an)\s+(user|developer|customer|administrator|admin|operator|"
    r"reader|client|programmer)\s+(?:should|must|can|may|will|needs?\s+to|"
    r"has\s+to|is\s+able\s+to|wants?\s+to)\b", re.I)

# -- tense (Google, Microsoft: present tense for behavior) ------------------
FUTURE_TENSE_RE = re.compile(
    r"\bwill\s+(?:then\s+)?(?:be\s+)?"
    r"(return|returns|display|show|create|delete|send|receive|contain|call|"
    r"produce|generate|raise|throw|emit|write|read|open|close|start|stop|"
    r"appear|output|print|fail|succeed|retry|log|store|set|update)\b", re.I)

# -- acronyms (IEEE 1063, ISO/IEC 26514, Microsoft, Google) -----------------
ACRONYM_RE = re.compile(r"(?<![A-Za-z0-9_/\-.])([A-Z][A-Z0-9]{1,5})(?![A-Za-z0-9_/\-])")
# Acronyms a technical reader is assumed to know; expanding them is noise.
WELL_KNOWN = {
    "API", "HTTP", "HTTPS", "URL", "URI", "JSON", "XML", "YAML", "HTML", "CSS",
    "SQL", "TCP", "UDP", "IP", "DNS", "SSH", "TLS", "SSL", "FTP", "SMTP",
    "CPU", "GPU", "RAM", "ROM", "SSD", "USB", "PDF", "CSV", "TSV", "ZIP",
    "OS", "ID", "UI", "UX", "CLI", "GUI", "SDK", "IDE", "REST", "CRUD",
    "JWT", "UUID", "GUID", "CDN", "VPN", "LAN", "WAN", "DHCP", "NAT",
    "CI", "CD", "VM", "PR", "MR", "SHA", "MD5", "AES", "RSA", "PEM",
    "ASCII", "UTF", "BOM", "EOF", "EOL", "MIME", "CORS", "CSRF", "XSS",
    "FAQ", "TODO", "NOTE", "WARNING", "CAUTION", "OK", "US", "UK", "EU",
    "AM", "PM", "UTC", "GMT", "ISO", "RFC", "IEEE", "ANSI", "W3C", "IETF",
    "MIT", "BSD", "GPL", "GNU", "PEP", "PYPI", "NPM", "AWS", "GCP",
    "IOPS", "SLA", "SLO", "SLI", "TTL", "QPS", "RPS", "P50", "P95", "P99",
    "AI", "ML", "LLM", "NLP", "OCR", "PDF", "SVG", "PNG", "JPEG", "GIF",
    "I", "A", "AND", "OR", "NOT", "IF", "THEN", "ELSE", "TRUE", "FALSE",
    "GET", "PUT", "POST", "HEAD", "PATCH", "DELETE", "OPTIONS", "TRACE",
    "MUST", "SHOULD", "MAY", "SHALL", "REQUIRED", "OPTIONAL", "RECOMMENDED",
}

# Ordinary English words that appear in capitals as headings, table columns,
# log levels, and emphasis. A consonant-density test does not separate "FILES"
# (2 vowels in 5) from "FQDN" (0 in 4), so they are listed.
COMMON_CAPS_WORDS = {
    "FILES", "FILE", "TOTAL", "NOTE", "NOTES", "ERROR", "ERRORS", "DEBUG",
    "TRACE", "FATAL", "TRUE", "FALSE", "NULL", "NONE", "ALL", "ANY", "NEW",
    "OLD", "SET", "GET", "ADD", "PIPE", "AREA", "NAME", "NAMES", "TYPE",
    "TYPES", "SIZE", "DATE", "TIME", "TEXT", "DATA", "PATH", "PORT", "HOST",
    "USER", "USERS", "ROOT", "MAIN", "TEST", "TESTS", "EXAMPLE", "EXAMPLES",
    "DEFAULT", "VALUE", "VALUES", "KEY", "KEYS", "LIST", "ITEM", "ITEMS",
    "INPUT", "OUTPUT", "START", "STOP", "END", "BEGIN", "OPEN", "CLOSE",
    "READ", "WRITE", "SEND", "RECV", "COPY", "MOVE", "LINK", "SYNC",
    "STATUS", "STATE", "FLAGS", "FLAG", "MODE", "SEE", "ALSO", "USAGE",
    "SYNOPSIS", "DESCRIPTION", "OPTIONS", "ARGUMENTS", "RETURN", "RETURNS",
    "TODO", "FIXME", "DONE", "YES", "NO", "ON", "OFF", "UP", "DOWN",
    "LOW", "HIGH", "MIN", "MAX", "SUM", "AVG", "COUNT", "TITLE", "BODY",
}

# -- headings (WCAG 1.3.1, every style guide) ------------------------------
HEADING_LINE_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
FENCE_BLOCK_RE = re.compile(r"(?ms)^\s*(```|~~~).*?^\s*\1")

# -- images (WCAG 1.1.1) ---------------------------------------------------
IMAGE_NO_ALT_RE = re.compile(r"!\[\s*\]\(\s*([^)\s]+)")

# -- minimalism (Carroll 1990): get to the action ---------------------------
IMPERATIVE_START_RE = re.compile(
    r"^(?:Run|Open|Close|Set|Add|Remove|Delete|Create|Install|Configure|Copy|"
    r"Move|Edit|Click|Select|Choose|Enter|Type|Press|Push|Pull|Start|Stop|"
    r"Restart|Check|Verify|Make|Build|Deploy|Download|Upload|Import|Export|"
    r"Connect|Disconnect|Enable|Disable|Update|Upgrade|Replace|Turn|Go|Use|"
    r"Call|Send|Save|Load|Apply|Attach|Mount|Extract|Clone|Navigate|Find)\b")


def check_link_text(doc, config):
    """Google, Microsoft, WCAG 2.4.4: link text must make sense alone."""
    body = FENCE_BLOCK_RE.sub(lambda m: "\n" * m.group(0).count("\n"), doc.raw)
    for m in LINK_TEXT_RE.finditer(body):
        text = m.group(1).strip()
        low = re.sub(r"[*_`~]", "", text).strip().lower().rstrip(".!?,:;")
        line = body[: m.start()].count("\n") + 1
        col = m.start() - (body.rfind("\n", 0, m.start()) + 1) + 1
        if low in VAGUE_LINK_TEXT:
            yield Finding(
                rule="DOC-LINKTEXT", severity=Severity.MINOR,
                message=f"Link text \"{text}\" does not say where it goes.",
                line=line, col=col, extract=text,
                suggestion="use the title of the target page",
                why="Google and Microsoft style guides; WCAG 2.4.4 — screen "
                    "readers list links out of context")
        elif BARE_URL_TEXT_RE.match(low) and len(low) > 40:
            yield Finding(
                rule="DOC-LINKTEXT", severity=Severity.INFO,
                message="A bare URL is being used as link text.",
                line=line, col=col, extract=text[:60],
                suggestion="use the page title instead",
                why="unreadable when a screen reader announces it character by character")


def check_condescension(doc, config):
    """Google word list; Microsoft: the reader must never feel condescended to."""
    why = ("Google word list; Microsoft: if we say something is easy and the "
           "reader finds it hard, we have alienated them")

    def emit(s, start, text, fix):
        line, col = s.pos_at(start)
        return Finding(
            rule="DOC-CONDESCEND", severity=Severity.MINOR,
            message=f"\"{text}\" tells the reader how they should find this.",
            line=line, col=col, extract=text, suggestion=fix, why=why)

    for s in doc.prose_sentences():
        text = scan_text(s, config)
        for m in CONDESCENDING_RE.finditer(text):
            yield emit(s, m.start(), m.group(0),
                       CONDESCENDING_ALWAYS[m.group(0).lower()])

        for m in READER_DIRECTED_RE.finditer(text):
            word = (m.group(1) or m.group(2))
            # A capitalized adjective followed by another capitalized word is a
            # proper noun: "Simple Mail Transfer Protocol".
            after = text[m.end(0):m.end(0) + 12].lstrip()
            if word[:1].isupper() and after[:1].isupper():
                continue
            yield emit(s, m.start(0), m.group(0).strip(),
                       CONDESCENDING_ADJ[word.lower()])

        for m in JUST_RE.finditer(text):
            if JUST_LEGITIMATE.search(text[max(0, m.start() - 14):m.end() + 14]):
                continue
            yield emit(s, m.start(), m.group(0),
                       "delete; Google's word list calls it a filler word")


def check_politeness(doc, config):
    """Google: do not use "please" when explaining how to use a product."""
    for s in doc.prose_sentences():
        for m in POLITENESS_RE.finditer(scan_text(s, config)):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="DOC-PLEASE", severity=Severity.INFO,
                message=f"\"{m.group(0)}\" — documentation instructs, it does "
                        "not ask.",
                line=line, col=col, extract=m.group(0),
                suggestion="drop \"please\"; keep the imperative",
                why="Google word list: don't use please in the normal course "
                    "of explaining how to use a product")


def check_allows_you_to(doc, config):
    """Google: "allows you to" -> "lets you"."""
    for s in doc.prose_sentences():
        for m in ALLOWS_RE.finditer(scan_text(s, config)):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="DOC-ALLOWS", severity=Severity.INFO,
                message=f"\"{m.group(0)}\" is a long way to say what the thing does.",
                line=line, col=col, extract=m.group(0),
                suggestion="\"lets you\", or name the action directly",
                why="Google word list: don't use \"allows you to\"; use \"lets you\"")


def check_second_person(doc, config):
    """Google and Microsoft both require second person."""
    for s in doc.prose_sentences():
        for m in THIRD_PERSON_RE.finditer(scan_text(s, config)):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="DOC-PERSON", severity=Severity.INFO,
                message=f"\"{m.group(0)}\" writes about the reader instead of "
                        "to them.",
                line=line, col=col, extract=m.group(0),
                suggestion="address the reader as \"you\"",
                why="Google and Microsoft style guides both specify second person")


def check_tense(doc, config):
    """Google and Microsoft: describe behavior in the present tense."""
    if config.mode == "narrative":
        return
    for s in doc.prose_sentences():
        for m in FUTURE_TENSE_RE.finditer(scan_text(s, config)):
            line, col = s.pos_at(m.start())
            verb = m.group(1)
            present = verb if verb.endswith("s") else verb + "s"
            yield Finding(
                rule="DOC-TENSE", severity=Severity.INFO,
                message=f"\"{m.group(0)}\" — describe behavior in the present tense.",
                line=line, col=col, extract=m.group(0),
                suggestion=f"\"{present}\"",
                why="Google and Microsoft style guides: present tense; the "
                    "software behaves this way now, not later")


def check_undefined_acronyms(doc, config):
    """IEEE 1063 / ISO IEC 26514: expand an abbreviation at first use.

    OFF BY DEFAULT. Calibration (2026-07-29) ran this at 2.79/1k on pre-LLM
    canon, and nearly all of it was wrong: it flagged "FILES", "OF", "TOTAL"
    and "PIPE" from headings and tables, plus place names from RFC mastheads.
    Distinguishing an acronym from an emphasized word needs a dictionary this
    tool does not carry, so the honest default is off. Teams whose house style
    requires expansion can enable it and curate `budgets.known_acronyms`.

    Enable with `budgets.check_acronyms: true`.
    """
    if not config.budgets.get("check_acronyms", False):
        return
    known = set(WELL_KNOWN) | set(COMMON_CAPS_WORDS)
    known |= {w.upper() for w in config.domain_vocabulary}
    known |= {str(a).upper() for a in config.budgets.get("known_acronyms", [])}
    raw = doc.raw
    # Count occurrences across prose only; a token appearing once is far more
    # likely a heading word or a label than a term the reader must learn.
    freq = {}
    for s in doc.prose_sentences():
        for m in ACRONYM_RE.finditer(s.text):
            freq[m.group(1)] = freq.get(m.group(1), 0) + 1

    seen = set()
    for s in doc.prose_sentences():
        if s.kind == "heading":
            continue
        for m in ACRONYM_RE.finditer(s.text):
            acr = m.group(1)
            if acr in known or acr in seen or len(acr) < 3:
                continue
            if freq.get(acr, 0) < 2:
                continue
            # Real acronyms are consonant-dense; ordinary words in caps are not.
            vowels = sum(c in "AEIOU" for c in acr)
            if vowels > len(acr) / 2:
                continue
            seen.add(acr)
            expanded = re.search(
                rf"\b(?:\w+[ -]){{1,6}}\(\s*{re.escape(acr)}s?\s*\)"
                rf"|{re.escape(acr)}\s*\(\s*[A-Za-z][^)]{{3,60}}\)", raw)
            if expanded:
                continue
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="DOC-ACRONYM", severity=Severity.INFO,
                message=f"\"{acr}\" is used {freq[acr]} times and never expanded.",
                line=line, col=col, extract=acr,
                suggestion=f"write it out at first use: Full Name ({acr})",
                why="IEEE 1063 and ISO/IEC 26514: define an abbreviation at "
                    "first use; add it to `budgets.known_acronyms` if your "
                    "audience already knows it")


def check_heading_structure(doc, config):
    """WCAG 1.3.1: heading levels convey structure, so they must not skip."""
    body = FENCE_BLOCK_RE.sub(lambda m: "\n" * m.group(0).count("\n"), doc.raw)
    headings = [(m.start(), len(m.group(1)), m.group(2))
                for m in HEADING_LINE_RE.finditer(body)]
    if len(headings) < 2:
        return
    top = [h for h in headings if h[1] == 1]
    if len(top) > 1:
        pos = top[1][0]
        yield Finding(
            rule="DOC-HEADING", severity=Severity.INFO,
            message=f"{len(top)} level-1 headings; a document has one title.",
            line=body[:pos].count("\n") + 1, col=1, extract=top[1][2][:60],
            suggestion="demote the extras to level 2",
            why="WCAG 1.3.1: headings are the document's outline")
    prev = None
    for pos, level, text in headings:
        if prev is not None and level > prev + 1:
            yield Finding(
                rule="DOC-HEADING", severity=Severity.INFO,
                message=f"Heading jumps from level {prev} to level {level}.",
                line=body[:pos].count("\n") + 1, col=1, extract=text[:60],
                suggestion=f"use level {prev + 1}",
                why="WCAG 1.3.1: a skipped level breaks screen-reader navigation")
        prev = level


def check_image_alt_text(doc, config):
    """WCAG 1.1.1: every image needs a text alternative."""
    body = FENCE_BLOCK_RE.sub(lambda m: "\n" * m.group(0).count("\n"), doc.raw)
    for m in IMAGE_NO_ALT_RE.finditer(body):
        yield Finding(
            rule="DOC-ALT", severity=Severity.MINOR,
            message=f"Image \"{m.group(1)}\" has no alt text.",
            line=body[: m.start()].count("\n") + 1, col=1,
            extract=m.group(1)[:60],
            suggestion="describe what the image shows, not that it is an image",
            why="WCAG 1.1.1; also the only thing a reader gets when the image "
                "fails to load")


def check_time_to_action(doc, config):
    """Carroll's minimalism: procedures should start acting, not explaining."""
    if config.mode != "procedure":
        return
    budget = int(config.budgets.get("words_before_first_step", 120))
    words = 0
    for s in doc.prose_sentences():
        if IMPERATIVE_START_RE.match(s.text):
            return
        words += len(s.words)
        if words > budget:
            yield Finding(
                rule="DOC-ACTION", severity=Severity.INFO,
                message=f"{words} words before the first instruction.",
                line=s.line, col=s.col,
                suggestion="move the background after the steps, or into a "
                           "separate explanation page",
                why="Carroll (1990), minimalism: readers act first and read "
                    "only when stuck; Diátaxis separates how-to from explanation")
            return


VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(VOWEL_GROUP_RE.findall(w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(1, n)


def check_readability(doc, config):
    """Flesch-Kincaid grade level, reported as a metric.

    INFO by design. A grade level is a proxy, it is easy to game, and dense
    subject matter legitimately raises it. It is here because a number the
    whole team can see moves prose more reliably than an argument about tone.
    """
    sents = doc.prose_sentences()
    if len(sents) < 15:
        return
    words = [w for s in sents for w in s.words if re.search(r"[A-Za-z]", w)]
    if len(words) < 200:
        return
    syl = sum(_syllables(w) for w in words)
    wps = len(words) / len(sents)
    spw = syl / len(words)
    grade = 0.39 * wps + 11.8 * spw - 15.59
    ceiling = float(config.budgets.get("grade_level", 14))
    if grade > ceiling:
        yield Finding(
            rule="DOC-READABILITY", severity=Severity.INFO,
            message=f"Flesch-Kincaid grade level {grade:.1f} "
                    f"(target {ceiling:.0f}); {wps:.0f} words/sentence, "
                    f"{spw:.2f} syllables/word.",
            line=sents[0].line, col=sents[0].col,
            suggestion="shorter sentences move this faster than shorter words",
            why="a proxy, not a verdict — dense subject matter raises it "
                "legitimately; tune with `budgets.grade_level`")


DOC_CHECKS = [
    check_link_text,
    check_condescension,
    check_politeness,
    check_allows_you_to,
    check_second_person,
    check_tense,
    check_undefined_acronyms,
    check_heading_structure,
    check_image_alt_text,
    check_time_to_action,
    check_readability,
]

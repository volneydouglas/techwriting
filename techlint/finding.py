"""Findings and the severity model.

Severity is about **recognition risk and reader cost**, not abstract badness --
the code-smell framing borrowed from the prose-smells project:

  BLOCKER  no legitimate use in a technical document; scrub on sight.
  MAJOR    scrub once confirmed in context (the exemption taxonomy applies).
  MINOR    budgeted; a few are fine, a pattern is not.
  INFO     metric or audit candidate; never a verdict.

The weighted score (per 1,000 words) is the single number for CI gating:

    wscore = (3.0*BLOCKER + 1.5*MAJOR + 0.5*MINOR) / words * 1000

INFO deliberately contributes zero -- audit candidates must never gate a build.
"""

from dataclasses import dataclass, field


class Severity:
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"

    ORDER = {BLOCKER: 4, MAJOR: 3, MINOR: 2, INFO: 1}
    WEIGHT = {BLOCKER: 3.0, MAJOR: 1.5, MINOR: 0.5, INFO: 0.0}
    ALL = [BLOCKER, MAJOR, MINOR, INFO]


class Axis:
    """What *kind* of editing a finding calls for.

    One total score tells you a document needs work; it does not tell you what
    work. Splitting the score by axis does: a document heavy on FABRICATION
    needs fact-checking, one heavy on FILLER needs cutting, one heavy on
    STRUCTURE needs reorganizing. (Idea borrowed from the sloppylint project,
    which splits its code-slop score into noise/lies/style/structure.)
    """

    FABRICATION = "fabrication"   # claims and references that may not be real
    FILLER = "filler"             # words that carry no information
    CLARITY = "clarity"           # constructions that cost the reader
    STRUCTURE = "structure"       # shape and rhythm of the document
    CONVENTION = "convention"     # documentation conventions and accessibility

    ALL = [FABRICATION, FILLER, CLARITY, STRUCTURE, CONVENTION]

    BY_RULE = {
        "AI-ARTIFACT": FABRICATION,
        "AI-LINK": FABRICATION,
        "AI-VOCAB": FILLER,
        "AI-VOCAB-DENSITY": FILLER,
        "AI-PHRASE": FILLER,
        "AI-HEDGE": FILLER,
        "AI-INTENSIFY": FILLER,
        "STAT-STALL": FILLER,
        "STAT-ECHO": FILLER,
        "STAT-ABSTRACT": FILLER,
        "AI-COPULA": STRUCTURE,
        "AI-DASH": STRUCTURE,
        "AI-TRIAD": STRUCTURE,
        "AI-OPENER": STRUCTURE,
        "AI-BOLDLIST": STRUCTURE,
        "AI-UNIFORM": STRUCTURE,
        "AI-EMOJI": STRUCTURE,
        "AI-PROSE-RATIO": STRUCTURE,
        "DOC-LINKTEXT": CONVENTION,
        "DOC-CONDESCEND": CONVENTION,
        "DOC-PLEASE": CONVENTION,
        "DOC-ALLOWS": CONVENTION,
        "DOC-PERSON": CONVENTION,
        "DOC-TENSE": CONVENTION,
        "DOC-ACRONYM": CONVENTION,
        "DOC-HEADING": CONVENTION,
        "DOC-ALT": CONVENTION,
        "DOC-ACTION": STRUCTURE,
        "DOC-READABILITY": CLARITY,
    }

    ADVICE = {
        FABRICATION: "verify these against reality before shipping",
        FILLER: "cut; the sentences work without them",
        CLARITY: "rewrite for the reader's working memory",
        STRUCTURE: "reorganize; the shape is doing the talking",
        CONVENTION: "align with the style guides your readers already expect",
    }

    @classmethod
    def of(cls, rule: str) -> str:
        if rule in cls.BY_RULE:
            return cls.BY_RULE[rule]
        if rule.startswith("CLARITY-"):
            return cls.CLARITY
        return cls.CONVENTION if rule.startswith("DOC-") else cls.STRUCTURE


@dataclass
class Finding:
    rule: str            # e.g. "AI-VOCAB", "CLARITY-NOMINAL"
    severity: str
    message: str
    line: int            # 1-based
    col: int             # 1-based
    extract: str = ""    # the offending text (also the baseline match key)
    suggestion: str = ""
    path: str = ""
    why: str = ""        # evidence: why this is a signal (citation or rate)
    meta: dict = field(default_factory=dict)

    @property
    def axis(self) -> str:
        return Axis.of(self.rule)

    def baseline_key(self):
        """Identity used by the suppression baseline: rule + file + quote."""
        return (self.rule, self.path, self.extract)

    def to_dict(self) -> dict:
        d = {
            "rule": self.rule,
            "severity": self.severity,
            "axis": self.axis,
            "message": self.message,
            "line": self.line,
            "col": self.col,
        }
        for k in ("path", "extract", "suggestion", "why"):
            v = getattr(self, k)
            if v:
                d[k] = v
        if self.meta:
            d["meta"] = self.meta
        return d


def weighted_score(findings, words: int) -> float:
    """Severity-weighted findings per 1,000 words."""
    if words <= 0:
        return 0.0
    total = sum(Severity.WEIGHT[f.severity] for f in findings)
    return round(total / words * 1000, 2)


def counts(findings) -> dict:
    out = {s: 0 for s in Severity.ALL}
    for f in findings:
        out[f.severity] += 1
    return out


def axis_scores(findings, words: int) -> dict:
    """Weighted score per axis, so the number says what kind of edit is needed."""
    out = {a: 0.0 for a in Axis.ALL}
    if words <= 0:
        return out
    for f in findings:
        out[f.axis] += Severity.WEIGHT[f.severity]
    return {a: round(v / words * 1000, 2) for a, v in out.items()}

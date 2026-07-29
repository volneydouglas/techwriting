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

    def baseline_key(self):
        """Identity used by the suppression baseline: rule + file + quote."""
        return (self.rule, self.path, self.extract)

    def to_dict(self) -> dict:
        d = {
            "rule": self.rule,
            "severity": self.severity,
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

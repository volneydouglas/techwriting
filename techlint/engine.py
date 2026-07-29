"""Lint engine: run the check batteries, apply the baseline, score the result."""

from pathlib import Path

from .baseline import Baseline
from .checks_ai import AI_CHECKS
from .checks_clarity import CLARITY_CHECKS
from .checks_links import LINK_CHECKS
from .config import Config
from .finding import Axis, Severity, axis_scores, counts, weighted_score
from .stats import STAT_CHECKS
from .textmodel import parse


def batteries(config: Config):
    checks = []
    if config.enable_clarity:
        checks += CLARITY_CHECKS
    if config.enable_ai:
        checks += AI_CHECKS + LINK_CHECKS
    if config.enable_stats:
        checks += STAT_CHECKS
    return checks


def lint_text(text: str, path: str = "", config: Config = None,
              baseline: Baseline = None):
    """Lint a string. Returns (findings, suppressed, report)."""
    config = config or Config()
    baseline = baseline or Baseline()
    doc = parse(text, path=path)

    raw = []
    for check in batteries(config):
        for f in check(doc, config):
            if f.rule in config.disable:
                continue
            f.path = path
            raw.append(f)

    findings, suppressed = baseline.partition(raw)
    findings.sort(key=lambda f: (f.line, f.col, -Severity.ORDER[f.severity]))

    words = doc.word_count()
    report = {
        "path": path,
        "words": words,
        "counts": counts(findings),
        "wscore": weighted_score(findings, words),
        "axes": axis_scores(findings, words),
        "suppressed": len(suppressed),
        "verdict": verdict(weighted_score(findings, words)),
    }
    return findings, suppressed, report


def lint_file(path, config: Config = None, baseline: Baseline = None):
    p = Path(path)
    return lint_text(p.read_text(encoding="utf-8", errors="replace"),
                     path=str(p), config=config, baseline=baseline)


def verdict(wscore: float) -> str:
    """Bands anchored to the calibration corpus, not guessed.

    Pre-LLM human technical canon (RFCs, PEPs) runs a weighted mean of **2.0**
    with the worst single text at 6.1; the deliberately slop-dense fixture runs
    **144**. So "clean" has to comfortably contain real specification prose,
    and the interesting range is well above it. Re-derive these after any
    detector change: `python benchmarks/run_calibration.py`.

    These are reference points. They are not a verdict on a document, and they
    are certainly not a claim about who wrote it.
    """
    if wscore >= 25.0:
        return "heavy"
    if wscore >= 10.0:
        return "moderate"
    if wscore >= 4.0:
        return "light"
    return "clean"


def aggregate(reports) -> dict:
    words = sum(r["words"] for r in reports)
    total = {s: sum(r["counts"][s] for r in reports) for s in Severity.ALL}
    weight = sum(Severity.WEIGHT[s] * n for s, n in total.items())
    wscore = round(weight / words * 1000, 2) if words else 0.0
    axes = {a: 0.0 for a in Axis.ALL}
    for r in reports:
        for a, v in r.get("axes", {}).items():
            axes[a] += v * r["words"]
    axes = {a: round(v / words, 2) if words else 0.0 for a, v in axes.items()}
    return {
        "files": len(reports),
        "words": words,
        "counts": total,
        "wscore": wscore,
        "axes": axes,
        "verdict": verdict(wscore),
        "suppressed": sum(r["suppressed"] for r in reports),
    }

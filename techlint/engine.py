"""Lint engine: run the check batteries, apply the baseline, score the result."""

from pathlib import Path

from .baseline import Baseline
from .checks_ai import AI_CHECKS
from .checks_clarity import CLARITY_CHECKS
from .checks_docs import DOC_CHECKS
from .checks_links import LINK_CHECKS
from .config import Config
from .finding import Axis, Severity, axis_scores, counts, weighted_score
from .stats import STAT_CHECKS
from .textmodel import parse


def batteries(config: Config):
    checks = []
    if config.enable_clarity:
        checks += CLARITY_CHECKS
    if config.enable_docs:
        checks += DOC_CHECKS
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
        "verdict": verdict(weighted_score(findings, words), config.bands),
    }
    return findings, suppressed, report


def lint_file(path, config: Config = None, baseline: Baseline = None):
    p = Path(path)
    return lint_text(p.read_text(encoding="utf-8", errors="replace"),
                     path=str(p), config=config, baseline=baseline)


DEFAULT_BANDS = {"light": 5.0, "moderate": 12.0, "heavy": 30.0}


def verdict(wscore: float, bands: dict = None) -> str:
    """Bands anchored to the calibration corpus, not guessed.

    Pre-LLM human technical canon spans **1.18 to 4.36** with a weighted mean
    of **2.14** across twelve texts covering all four Diátaxis genres; the
    deliberately slop-dense fixture runs **152**. "Clean" therefore has to
    contain every one of those canon texts, which is why the boundary sits at
    5 rather than somewhere tighter that would look more impressive.

    An earlier version anchored on specifications alone and put the boundary
    at 4. Adding tutorials and how-to guides moved the canon range up: those
    genres address the reader directly and run warmer. Genre matters as much
    as age, which is the argument for re-deriving these against your own
    documentation:

        python benchmarks/run_calibration.py

    Override in techlint.yaml with `bands: {light: 5, moderate: 12, heavy: 30}`.

    These are reference points. They are not a verdict on a document, and they
    are certainly not a claim about who wrote it.
    """
    b = {**DEFAULT_BANDS, **(bands or {})}
    if wscore >= b["heavy"]:
        return "heavy"
    if wscore >= b["moderate"]:
        return "moderate"
    if wscore >= b["light"]:
        return "light"
    return "clean"


def aggregate(reports, bands: dict = None) -> dict:
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
        "verdict": verdict(wscore, bands),
        "suppressed": sum(r["suppressed"] for r in reports),
    }

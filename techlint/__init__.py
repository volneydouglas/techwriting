"""techlint — a technical-writing linter with AI-tic detection.

Two batteries over the same document model:

  * **clarity** — rules every major style authority agrees on (active voice,
    buried verbs, wordiness, subject-verb distance, stress position, inclusive
    language). Nothing aviation-specific.
  * **ai** — tics of unedited LLM output, tiered by measured effect size from
    the Kobak et al. excess-vocabulary study plus structural patterns from
    stylometric research and the prose-smells project.

Findings are severity-classed (blocker/major/minor/info) and reduced to one
weighted score per 1,000 words for CI gating. Nothing here is a verdict on
whether a text is good, or on who wrote it.
"""

from .baseline import Baseline
from .config import Config
from .engine import aggregate, lint_file, lint_text
from .finding import Finding, Severity

__version__ = "0.2.0"

__all__ = [
    "Baseline", "Config", "Finding", "Severity",
    "lint_text", "lint_file", "aggregate", "__version__",
]

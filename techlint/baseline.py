"""Suppression baseline: context-reviewed exemptions, with written reasons.

Borrowed wholesale from the prose-smells project, because it is the mechanism
that makes an over-flagging detector usable. The detector is *designed* to
over-flag; the baseline is where a human records "I read this one, it is fine,
and here is why." The gate then stays quiet on reviewed hits and loud on
everything new.

Format -- one JSON object per line (`.techlint-baseline.jsonl`):

    {"rule": "AI-VOCAB", "file": "docs/api.md", "quote": "harness",
     "why": "literal: the wiring harness this page documents"}

Rules of use (non-negotiable, learned the hard way in the source project):
  1. Never add an entry without reading the hit in context.
  2. `why` is required. An entry without a reason is not an exemption, it is
     an unexamined suppression.
  3. `quote` matches by prefix, so a baselined hit survives small edits around
     it but not a rewrite of the phrase itself.
"""

import json
from pathlib import Path

DEFAULT_NAME = ".techlint-baseline.jsonl"


class Baseline:
    def __init__(self, entries=()):
        self.entries = list(entries)

    @classmethod
    def load(cls, path=None):
        p = Path(path or DEFAULT_NAME)
        if not p.exists():
            return cls()
        entries = []
        for n, line in enumerate(p.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{p}:{n}: invalid JSON ({exc})") from exc
            missing = {"rule", "file", "quote", "why"} - set(e)
            if missing:
                raise ValueError(
                    f"{p}:{n}: baseline entry missing {sorted(missing)}. "
                    "Every exemption needs a written reason.")
            entries.append(e)
        return cls(entries)

    def suppresses(self, finding) -> bool:
        for e in self.entries:
            if (e["rule"] == finding.rule
                    and _same_file(e["file"], finding.path)
                    and finding.extract.startswith(e["quote"])):
                return True
        return False

    def partition(self, findings):
        """Split into (reported, suppressed)."""
        kept, sup = [], []
        for f in findings:
            (sup if self.suppresses(f) else kept).append(f)
        return kept, sup

    @staticmethod
    def entry(finding, why: str) -> str:
        return json.dumps({
            "rule": finding.rule,
            "file": finding.path,
            "quote": finding.extract,
            "why": why,
        })


def _same_file(entry_file: str, finding_path: str) -> bool:
    if entry_file == finding_path:
        return True
    # Tolerate relative/absolute mismatch on the tail of the path.
    return (finding_path.endswith("/" + entry_file)
            or entry_file.endswith("/" + finding_path))

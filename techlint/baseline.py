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
  4. Document-level findings (AI-DASH, AI-VOCAB-DENSITY, DOC-READABILITY, ...)
     report a rate, not a phrase, so they have nothing to quote. For those,
     set `"quote": "*"` -- an explicit whole-document exemption for that rule
     in that file. An *empty* quote is rejected: it used to prefix-match
     everything by accident, which is a silence, not a decision.
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
            empty = [k for k in ("rule", "file", "quote", "why") if not e[k]]
            if empty:
                raise ValueError(
                    f"{p}:{n}: baseline entry has empty {empty}. An empty "
                    "quote matches by prefix against everything and would "
                    "suppress the whole rule for that file. For a "
                    "document-level finding with no extract, make the intent "
                    "explicit with \"quote\": \"*\".")
            entries.append(e)
        return cls(entries)

    def suppresses(self, finding) -> bool:
        for e in self.entries:
            quote = e.get("quote")
            if not quote:
                continue      # prefix-match against "" would suppress everything
            if e["rule"] != finding.rule or not _same_file(e["file"], finding.path):
                continue
            # "*" is the explicit whole-document exemption for findings that
            # report a rate rather than a phrase and so have no extract.
            if quote == "*" or finding.extract.startswith(quote):
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

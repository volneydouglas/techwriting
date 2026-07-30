#!/usr/bin/env python3
"""Extract one version's section from CHANGELOG.md.

Used by the release workflow to turn the changelog into GitHub Release notes,
so the changelog stays the single source of truth and the release page never
drifts from it.

Usage:
    python tools/release_notes.py 1.1.0            # print the 1.1.0 section
    python tools/release_notes.py 1.1.0 out.md     # write it to a file

Exits non-zero if the version has no section — a release without notes is a
release that skipped its changelog entry, and the workflow should fail loudly
rather than publish an empty page.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def extract(version: str, text: str) -> str:
    # Headers look like "## 1.1.0 — 2026-07-29"; tolerate any dash or none.
    pattern = rf"(?ms)^## {re.escape(version)}\b[^\n]*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(
            f"CHANGELOG.md has no section for {version}. "
            "Add one before releasing.")
    return m.group(1).strip() + "\n"


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    notes = extract(sys.argv[1], CHANGELOG.read_text())
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(notes)
    else:
        print(notes, end="")


if __name__ == "__main__":
    main()

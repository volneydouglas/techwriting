#!/usr/bin/env python3
"""Fetch the calibration corpus: technical prose written before LLMs existed.

The prime directive, borrowed from the sibling fiction projects:

    When the instrument fires hard on acclaimed work, suspect the instrument.

For fiction that means Chekhov and Austen. For technical writing it means
documents that are (a) unambiguously human, (b) unambiguously good, and
(c) written well before November 2022 — so any tic the detector finds in them
is a false positive by construction.

The corpus is **dimension-mapped**: each text calibrates a specific instrument
rather than being a generic "good document".

    RFC 1925    aphorism/humor control — SHOULD trip the tic detectors and is
                canon. The humility fixture: if the tone ever implies
                "flagged == wrong", RFC 1925 is the standing counter-example.
    RFC 2119    normative keyword discipline (must/should/shall) at its source
    RFC 793     dense protocol specification; long sentences, heavy passive
    PEP 8       prescriptive style guidance, imperative mood
    PEP 20      extreme brevity control
    Autoconf    long-form GNU reference prose
    Make        tutorial + reference mixed register

Texts are cached under benchmarks/corpus/ (gitignored); results are committed
so the numbers are reviewable without re-fetching.
"""

import sys
import urllib.request
from pathlib import Path

CORPUS = Path(__file__).parent / "corpus"

SOURCES = {
    "rfc1925_humor.txt": ("https://www.rfc-editor.org/rfc/rfc1925.txt",
                          "humor/aphorism control (expected to trip detectors)"),
    "rfc2119_keywords.txt": ("https://www.rfc-editor.org/rfc/rfc2119.txt",
                             "normative keyword discipline"),
    "rfc793_tcp.txt": ("https://www.rfc-editor.org/rfc/rfc793.txt",
                       "dense protocol spec; passive-heavy"),
    "rfc1035_dns.txt": ("https://www.rfc-editor.org/rfc/rfc1035.txt",
                        "reference prose + tables"),
    "pep8_style.txt": ("https://peps.python.org/pep-0008/",
                       "prescriptive style guidance"),
    "pep20_zen.txt": ("https://peps.python.org/pep-0020/",
                      "extreme brevity control"),
    "pep257_docstrings.txt": ("https://peps.python.org/pep-0257/",
                              "convention prose"),
}


def strip_html(s: str) -> str:
    """Extract article prose. Site chrome (theme switchers, nav, TOC) must not
    reach the corpus -- it polluted the first run with "Following system colour
    scheme" and produced three phantom British-spelling findings in PEP 20."""
    import html
    import re
    # Prefer the semantic article body when the page has one.
    for tag in ("article", "main"):
        m = re.search(rf"(?is)<{tag}[^>]*>(.*)</{tag}>", s)
        if m:
            s = m.group(1)
            break
    # <title>/<symbol> carry icon labels inside inline SVG sprites; peps.python.org
    # hides its theme-switcher text there, and because those SVGs are *nested*
    # a non-greedy <svg>...</svg> strip leaves the tail behind. Remove them by name.
    s = re.sub(r"(?is)<(title|symbol|desc)[^>]*>.*?</\1>", " ", s)
    s = re.sub(
        r"(?is)<(script|style|nav|header|footer|aside|form|button|select|"
        r"option|label|template|svg|noscript)[^>]*>.*?</\1>", " ", s)
    # Any element whose class/id marks it as chrome (theme switchers, skip
    # links, breadcrumbs) — peps.python.org puts its colour-scheme labels here.
    s = re.sub(
        r"(?is)<(\w+)[^>]*(?:class|id)=\"[^\"]*"
        r"(?:theme|switch|skip|breadcrumb|sidebar|toc|menu)[^\"]*\"[^>]*>.*?</\1>",
        " ", s)
    s = re.sub(r"(?is)<(details|summary)[^>]*>", " ", s)
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>|</tr>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s)


def main() -> int:
    CORPUS.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name, (url, purpose) in SOURCES.items():
        dest = CORPUS / name
        if dest.exists():
            print(f"  cached  {name}")
            ok += 1
            continue
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "techlint-calibration/0.2"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
        except Exception as e:                       # noqa: BLE001
            print(f"  FAILED  {name}: {e}", file=sys.stderr)
            continue
        if "<html" in body[:2000].lower():
            body = strip_html(body)
        dest.write_text(body)
        print(f"  fetched {name}  ({len(body.split())} words) — {purpose}")
        ok += 1
    print(f"\n{ok}/{len(SOURCES)} texts in {CORPUS}")
    print("next: python benchmarks/run_calibration.py")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

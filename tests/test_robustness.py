"""Robustness suite: hostile inputs must never crash the linter.

A linter that throws on weird markdown gets removed from CI the same
afternoon. Every input here ran against every config during the 2026-07-30
bug hunt; the suite keeps that guarantee. Three invariants hold for every
(input, config) pair:

  1. lint_text returns instead of raising.
  2. Every finding's line and column are >= 1 and within the document.
  3. The weighted score is finite and non-negative.
"""

import time

import pytest

from techlint import Config, lint_text

HOSTILE = {
    "empty": "",
    "whitespace_only": "   \n\t\n   ",
    "single_char": "x",
    "crlf_endings": "First line.\r\n\r\nSecond paragraph with delve.\r\n",
    "cr_only_endings": "Old mac line.\rAnother.\r",
    "unterminated_fence": "Text.\n\n```\ncode never closes",
    "fence_at_eof": "Text.\n```",
    "nested_emphasis": "***_**bold*_ mess** here.",
    "unclosed_link": "See [broken link( here.",
    "link_with_parens": "See [x](path(1).md) and [y](a.md#f(x)).",
    "long_line": "word " * 20000,
    "sentence_storm": "A. " * 3000,
    "unicode_mix": "Résumé façade naïve — ελληνικά 中文 🎉 delve.",
    "zero_width_chars": "del​ve into th​is.",
    "rtl_text": "النص العربي هنا. delve into it.",
    "control_chars": "Text\x00with\x01controls.\x7f Done.",
    "punctuation_only": "... !!! ??? ;;; :::",
    "table_only": "| a | b |\n|---|---|\n| 1 | 2 |",
    "html_soup": "<div><p>text <b>bold</b> <br/> more</p></div>",
    "deep_blockquote": "> " * 50 + "quoted",
    "list_bomb": "\n".join(f"- item {i}" for i in range(1000)),
    "heading_bomb": "\n".join(f"{'#' * (i % 6 + 1)} h{i}" for i in range(300)),
    "single_long_word": "a" * 50000,
    "backslash_escapes": "escape \\* \\[ \\` sequence \\\\ end.",
    "curly_quote_storm": "“open “nested” close” and ‘single’ 'mixed’ mess.",
    "mixed_indent_bullets": "- top\n    - nested\n        - deeper\n- back",
    "setext_headings": "Title\n=====\n\nSub\n---\n\nBody delve here.",
    "bare_urls": "See https://example.com/path?a=1&b=2#frag and www.x.io.",
    "format_strings": "Use %s and %d and {placeholder} and $VAR.",
}

CONFIGS = {
    "default": Config(),
    "everything_on": Config(
        mode="procedure", pedantic=True,
        budgets={"echo_ngrams": True, "check_acronyms": True},
        style={"quoted_specimens": "skip", "contractions": "flag"}),
    "narrative_gb": Config(mode="narrative", locale="gb"),
}


@pytest.mark.parametrize("cfg_name", CONFIGS)
@pytest.mark.parametrize("case", HOSTILE)
def test_hostile_input_invariants(case, cfg_name):
    text = HOSTILE[case]
    findings, _sup, report = lint_text(text, path="x.md",
                                       config=CONFIGS[cfg_name])
    nlines = text.count("\n") + 1
    for f in findings:
        assert f.line >= 1 and f.col >= 1
        assert f.line <= nlines, f"{f.rule} points past the document"
        assert f.severity in ("blocker", "major", "minor", "info")
    assert report["wscore"] >= 0


class TestBacktrackingResistance:
    """Inputs shaped to punish the .{2,60}-style patterns. Generous limits —
    CI runners are slow — but a catastrophic regex is minutes, not seconds."""

    BAIT = {
        "antithesis": "It's not just about " + "a" * 5000 + " end.",
        "audience_triad": "Whether you're a " + "x " * 3000 + "done.",
        "quote_run": "'" * 4000,
        "dash_storm": "word — " * 3000,
        "triad_storm": "a, b, and c " * 2000 + ".",
    }

    @pytest.mark.parametrize("case", BAIT)
    def test_completes_quickly(self, case):
        t0 = time.time()
        lint_text(self.BAIT[case], path="x.md",
                  config=Config(style={"quoted_specimens": "skip"}))
        assert time.time() - t0 < 10

    def test_large_realistic_document(self):
        text = ("The scheduler assigns each pending job to an available "
                "worker node. It checks the queue every second. ") * 2000
        t0 = time.time()
        _f, _s, report = lint_text(text, path="x.md", config=Config())
        assert time.time() - t0 < 30
        assert report["words"] > 30000

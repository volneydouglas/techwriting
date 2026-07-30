"""Regression tests from the 2026-07-30 bug hunt.

Each class pins one bug that shipped past the existing suite. The pattern to
copy when adding here: reproduce the bug as a failing assertion first, fix the
code second, and keep the test named after the failure mode rather than the
fix.
"""

import pytest

from techlint import Baseline, Config, lint_text
from techlint.checks_clarity import _verb_base
from techlint.checks_links import _anchors_of
from techlint.finding import Finding, Severity
from techlint.textmodel import parse, scan_text


class TestVerbBaseSuggestions:
    """Bug 1: suggestions said "Disconnecte the …" and "Adjuste the …".

    The e-restoration heuristic matched any stem whose +e form ended in
    consonant+e, which is most of them. Suggestions are user-facing text; a
    misspelled imperative makes the whole tool look unserious.
    """

    CASES = {
        # bare-stem class (the ones the old heuristic mangled)
        "disconnected": "disconnect", "adjusted": "adjust",
        "installed": "install", "processed": "process", "edited": "edit",
        "monitored": "monitor", "started": "start", "loaded": "load",
        "failed": "fail", "exported": "export", "returned": "return",
        # silent-e class
        "ensured": "ensure", "configured": "configure", "created": "create",
        "updated": "update", "deleted": "delete", "cached": "cache",
        "used": "use", "restored": "restore", "validated": "validate",
        "merged": "merge", "parsed": "parse", "released": "release",
        # orthography rules
        "removed": "remove", "analyzed": "analyze", "produced": "produce",
        "enabled": "enable", "deployed": "deploy",
        # doubling and -ied
        "stopped": "stop", "applied": "apply",
        # irregulars
        "written": "write", "sent": "send", "held": "hold",
    }

    def test_common_documentation_verbs(self):
        wrong = {pp: (_verb_base(pp), want)
                 for pp, want in self.CASES.items() if _verb_base(pp) != want}
        assert not wrong, wrong

    def test_end_to_end_suggestion_is_spelled_correctly(self):
        findings, _s, _r = lint_text(
            "The power should be disconnected first.",
            config=Config(mode="procedure"))
        hits = [f for f in findings if f.rule == "CLARITY-PASSIVE"]
        assert hits and "Disconnect the" in hits[0].suggestion
        assert "Disconnecte" not in hits[0].suggestion


class TestBoldListIgnoresCodeFences:
    """Bug 2: AI-BOLDLIST scanned doc.raw, counting bullets inside fences."""

    FENCED = "Text here.\n\n```\n- **a:** x\n- **b:** y\n- **c:** z\n- **d:** w\n```\n"

    def test_fenced_bullets_not_counted(self):
        findings, _s, _r = lint_text(self.FENCED, config=Config())
        assert not [f for f in findings if f.rule == "AI-BOLDLIST"]

    def test_real_bold_list_still_fires(self):
        text = "- **a:** x\n- **b:** y\n- **c:** z\n- **d:** w\n"
        findings, _s, _r = lint_text(text, config=Config())
        assert [f for f in findings if f.rule == "AI-BOLDLIST"]


class TestApostropheIsNotAQuote:
    """Bug 3: specimen masking treated possessive apostrophes as quote
    delimiters and blanked the prose between two of them."""

    CFG = Config(style={"quoted_specimens": "skip"})

    def test_prose_between_possessives_survives(self):
        doc = parse("The collector's clock and the user's config drift apart.")
        masked = scan_text(doc.prose_sentences()[0], self.CFG)
        assert "clock and the user" in masked

    def test_finding_between_possessives_not_hidden(self):
        findings, _s, _r = lint_text(
            "The collector's delves and the user's patience run out.",
            path="d.md", config=self.CFG)
        assert [f for f in findings if f.rule == "AI-VOCAB"]

    def test_standalone_single_quotes_still_masked(self):
        doc = parse("Read 'the quoted specimen text' aloud.")
        masked = scan_text(doc.prose_sentences()[0], self.CFG)
        assert "quoted specimen" not in masked


class TestBaselineEmptyQuote:
    """Bug 4: an entry with quote "" prefix-matched every finding of its rule
    in its file — a one-character typo away from silencing a whole rule."""

    def test_load_rejects_empty_quote(self, tmp_path):
        bl = tmp_path / "b.jsonl"
        bl.write_text('{"rule": "AI-VOCAB", "file": "d.md", "quote": "", '
                      '"why": "typo"}\n')
        with pytest.raises(ValueError, match="empty"):
            Baseline.load(bl)

    def test_programmatic_empty_quote_matches_nothing(self):
        bl = Baseline([{"rule": "AI-VOCAB", "file": "d.md", "quote": "",
                        "why": "x"}])
        f = Finding("AI-VOCAB", Severity.MAJOR, "m", 1, 1,
                    extract="delves", path="d.md")
        assert not bl.suppresses(f)


class TestDuplicateHeadingAnchors:
    """Bug 5: GitHub suffixes repeated headings (-1, -2); the anchor set did
    not, so a correct link to the second "Setup" section was flagged."""

    def test_suffixed_anchors_generated(self):
        anchors = _anchors_of("# D\n\n## Setup\n\n## Setup\n\n## Setup\n")
        assert {"setup", "setup-1", "setup-2"} <= anchors

    def test_link_to_second_occurrence_not_flagged(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("# D\n\n## Setup\n\nFirst.\n\n## Setup\n\nSecond — "
                     "see [above](#setup) or [this one](#setup-1).\n")
        from techlint import lint_file
        findings, _s, _r = lint_file(d, Config())
        assert not [f for f in findings if f.rule == "AI-LINK"]

    def test_wrong_suffix_still_flagged(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("# D\n\n## Setup\n\nSee [ghost](#setup-3).\n")
        from techlint import lint_file
        findings, _s, _r = lint_file(d, Config())
        assert [f for f in findings if f.rule == "AI-LINK"]


class TestBaselineWildcard:
    """Companion to the empty-quote fix: document-level findings (AI-DASH,
    AI-VOCAB-DENSITY) report a rate, not a phrase, so they have no extract to
    quote. "*" is the explicit whole-document exemption; "" stays rejected."""

    def test_wildcard_suppresses_extractless_finding(self):
        bl = Baseline([{"rule": "AI-DASH", "file": "d.md", "quote": "*",
                        "why": "the page quotes em-dash specimens"}])
        f = Finding("AI-DASH", Severity.MINOR, "m", 1, 1, extract="", path="d.md")
        assert bl.suppresses(f)

    def test_wildcard_is_rule_and_file_scoped(self):
        bl = Baseline([{"rule": "AI-DASH", "file": "d.md", "quote": "*",
                        "why": "x"}])
        other_rule = Finding("AI-VOCAB", Severity.MAJOR, "m", 1, 1,
                             extract="delves", path="d.md")
        other_file = Finding("AI-DASH", Severity.MINOR, "m", 1, 1,
                             extract="", path="e.md")
        assert not bl.suppresses(other_rule)
        assert not bl.suppresses(other_file)

    def test_wildcard_loads(self, tmp_path):
        p = tmp_path / "b.jsonl"
        p.write_text('{"rule": "AI-DASH", "file": "d.md", "quote": "*", '
                     '"why": "reviewed"}\n')
        assert len(Baseline.load(p).entries) == 1

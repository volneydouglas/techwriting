"""Reference validation and the axis breakdown."""

from techlint import Config, lint_file, lint_text
from techlint.engine import aggregate
from techlint.finding import Axis, Finding, Severity, axis_scores


class TestLinkValidation:
    def test_missing_relative_link_flagged(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("See the [setup guide](setup.md) for details.\n")
        findings, _s, _r = lint_file(d, Config())
        hits = [f for f in findings if f.rule == "AI-LINK"]
        assert hits and "setup.md" in hits[0].message
        assert hits[0].severity == Severity.MAJOR

    def test_existing_relative_link_ok(self, tmp_path):
        (tmp_path / "setup.md").write_text("# Setup\n")
        d = tmp_path / "doc.md"
        d.write_text("See the [setup guide](setup.md) for details.\n")
        findings, _s, _r = lint_file(d, Config())
        assert not [f for f in findings if f.rule == "AI-LINK"]

    def test_external_urls_not_checked(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("See [the spec](https://example.invalid/nope) for details.\n")
        findings, _s, _r = lint_file(d, Config())
        assert not [f for f in findings if f.rule == "AI-LINK"]

    def test_missing_own_anchor_flagged(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("# Title\n\nJump to [the details](#the-details) below.\n")
        findings, _s, _r = lint_file(d, Config())
        assert [f for f in findings if f.rule == "AI-LINK"]

    def test_present_own_anchor_ok(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("# Title\n\nJump to [the details](#the-details).\n\n"
                     "## The Details\n\nHere they are.\n")
        findings, _s, _r = lint_file(d, Config())
        assert not [f for f in findings if f.rule == "AI-LINK"]

    def test_cross_file_anchor_checked(self, tmp_path):
        (tmp_path / "other.md").write_text("# Other\n\n## Real Section\n")
        d = tmp_path / "doc.md"
        d.write_text("See [there](other.md#imaginary-section).\n")
        findings, _s, _r = lint_file(d, Config())
        hits = [f for f in findings if f.rule == "AI-LINK"]
        assert hits and hits[0].severity == Severity.MINOR

    def test_links_in_code_blocks_ignored(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("```\n[example](nonexistent.md)\n```\n")
        findings, _s, _r = lint_file(d, Config())
        assert not [f for f in findings if f.rule == "AI-LINK"]

    def test_can_be_disabled(self, tmp_path):
        d = tmp_path / "doc.md"
        d.write_text("See the [setup guide](setup.md).\n")
        findings, _s, _r = lint_file(d, Config(budgets={"check_links": False}))
        assert not [f for f in findings if f.rule == "AI-LINK"]

    def test_stdin_skipped(self):
        findings, _s, _r = lint_text("See [x](nope.md).", path="<stdin>",
                                     config=Config())
        assert not [f for f in findings if f.rule == "AI-LINK"]


class TestProseRatio:
    def test_table_heavy_document_flagged(self):
        rows = "\n".join(f"| item{i} | value{i} | note{i} |" for i in range(40))
        text = f"# Reference\n\n| a | b | c |\n|---|---|---|\n{rows}\n"
        findings, _s, _r = lint_text(text, config=Config())
        assert [f for f in findings if f.rule == "AI-PROSE-RATIO"]

    def test_prose_document_not_flagged(self):
        text = "\n\n".join(
            [f"The scheduler assigns job {i} to a worker node based on current "
             f"utilization and the declared requirements." for i in range(40)])
        findings, _s, _r = lint_text(text, config=Config())
        assert not [f for f in findings if f.rule == "AI-PROSE-RATIO"]

    def test_short_document_skipped(self):
        text = "| a | b |\n|---|---|\n| 1 | 2 |\n"
        findings, _s, _r = lint_text(text, config=Config())
        assert not [f for f in findings if f.rule == "AI-PROSE-RATIO"]


class TestAxes:
    def test_rule_to_axis_mapping(self):
        assert Axis.of("AI-ARTIFACT") == Axis.FABRICATION
        assert Axis.of("AI-LINK") == Axis.FABRICATION
        assert Axis.of("AI-VOCAB") == Axis.FILLER
        assert Axis.of("STAT-STALL") == Axis.FILLER
        assert Axis.of("CLARITY-PASSIVE") == Axis.CLARITY
        assert Axis.of("AI-BOLDLIST") == Axis.STRUCTURE

    def test_unknown_clarity_rule_defaults_to_clarity(self):
        assert Axis.of("CLARITY-SOMETHING-NEW") == Axis.CLARITY

    def test_axis_scores_split_the_total(self):
        fs = [Finding("AI-VOCAB", Severity.MAJOR, "m", 1, 1),
              Finding("CLARITY-PASSIVE", Severity.MINOR, "m", 1, 1)]
        scores = axis_scores(fs, 1000)
        assert scores[Axis.FILLER] == 1.5
        assert scores[Axis.CLARITY] == 0.5
        assert scores[Axis.FABRICATION] == 0.0

    def test_report_carries_axes(self):
        _f, _s, rep = lint_text("This guide delves into the intricacies.",
                                config=Config())
        assert rep["axes"][Axis.FILLER] > 0

    def test_aggregate_averages_axes_by_words(self):
        reports = [
            {"words": 500, "counts": {s: 0 for s in Severity.ALL}, "suppressed": 0,
             "axes": {Axis.FILLER: 4.0, Axis.CLARITY: 0.0,
                      Axis.FABRICATION: 0.0, Axis.STRUCTURE: 0.0}},
            {"words": 500, "counts": {s: 0 for s in Severity.ALL}, "suppressed": 0,
             "axes": {Axis.FILLER: 0.0, Axis.CLARITY: 2.0,
                      Axis.FABRICATION: 0.0, Axis.STRUCTURE: 0.0}},
        ]
        agg = aggregate(reports)
        assert agg["axes"][Axis.FILLER] == 2.0
        assert agg["axes"][Axis.CLARITY] == 1.0

    def test_findings_serialize_axis(self):
        _f, _s, _r = lint_text("x", config=Config())
        f = Finding("AI-VOCAB", Severity.MAJOR, "m", 1, 1)
        assert f.to_dict()["axis"] == Axis.FILLER

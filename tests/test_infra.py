"""Tests for the severity model, baseline, config, stats, and CLI."""

import json
import subprocess
import sys

import pytest
from pathlib import Path

from techlint import Baseline, Config, lint_text
from techlint.config import _parse_yaml
from techlint.engine import aggregate, verdict
from techlint.finding import Finding, Severity, weighted_score


class TestSeverityModel:
    def test_weighted_score_formula(self):
        fs = [Finding("R", Severity.BLOCKER, "m", 1, 1),
              Finding("R", Severity.MAJOR, "m", 1, 1),
              Finding("R", Severity.MINOR, "m", 1, 1),
              Finding("R", Severity.INFO, "m", 1, 1)]
        # (3.0 + 1.5 + 0.5 + 0.0) / 1000 * 1000
        assert weighted_score(fs, 1000) == 5.0

    def test_info_has_zero_weight(self):
        fs = [Finding("R", Severity.INFO, "m", 1, 1)] * 50
        assert weighted_score(fs, 1000) == 0.0

    def test_verdict_bands_put_canon_in_clean(self):
        assert verdict(1.38) == "clean"      # calibration corpus mean
        assert verdict(6.08) == "light"      # worst canon text
        assert verdict(137.65) == "heavy"    # known-bad fixture

    def test_aggregate_across_files(self):
        reports = [
            {"words": 100, "counts": {Severity.BLOCKER: 1, Severity.MAJOR: 0,
                                      Severity.MINOR: 0, Severity.INFO: 0},
             "suppressed": 0},
            {"words": 900, "counts": {Severity.BLOCKER: 0, Severity.MAJOR: 0,
                                      Severity.MINOR: 0, Severity.INFO: 5},
             "suppressed": 1},
        ]
        agg = aggregate(reports)
        assert agg["words"] == 1000
        assert agg["wscore"] == 3.0
        assert agg["suppressed"] == 1


class TestBaseline:
    def test_suppresses_matching_finding(self, tmp_path):
        bl = tmp_path / "b.jsonl"
        bl.write_text(json.dumps({
            "rule": "AI-VOCAB", "file": "d.md", "quote": "delves",
            "why": "quoted verbatim from an upstream changelog"}) + "\n")
        baseline = Baseline.load(bl)
        findings, sup, _rep = lint_text("This guide delves into the API.",
                                        path="d.md", config=Config(),
                                        baseline=baseline)
        assert not [f for f in findings if f.rule == "AI-VOCAB"]
        assert len(sup) == 1

    def test_reason_is_required(self, tmp_path):
        bl = tmp_path / "b.jsonl"
        bl.write_text('{"rule": "AI-VOCAB", "file": "d.md", "quote": "x"}\n')
        with pytest.raises(ValueError, match="written reason"):
            Baseline.load(bl)

    def test_missing_file_is_empty(self, tmp_path):
        assert Baseline.load(tmp_path / "nope.jsonl").entries == []

    def test_entry_roundtrip(self):
        f = Finding("AI-VOCAB", Severity.MAJOR, "m", 1, 1, extract="delve",
                    path="a.md")
        e = json.loads(Baseline.entry(f, why="quoting a source"))
        assert e["rule"] == "AI-VOCAB" and e["why"] == "quoting a source"


class TestConfig:
    def test_mode_sets_budgets(self):
        assert Config(mode="procedure").sentence_words == 20
        assert Config(mode="reference").sentence_words == 30
        assert Config(mode="narrative").sentence_words == 40

    def test_explicit_budget_wins(self):
        assert Config(mode="procedure", budgets={"sentence_words": 12}).sentence_words == 12

    def test_domain_vocabulary_is_lowercased(self):
        assert Config(domain_vocabulary={"Harness"}).is_domain_word("harness")

    def test_unknown_key_rejected(self, tmp_path):
        p = tmp_path / "techlint.json"
        p.write_text('{"nonsense": 1}')
        with pytest.raises(ValueError, match="unknown config keys"):
            Config.load(p)

    def test_yaml_subset_parser(self):
        data = _parse_yaml(
            "mode: procedure\n"
            "locale: us\n"
            "budgets:\n"
            "  sentence_words: 18\n"
            "domain_vocabulary:\n"
            "  - harness\n"
            "  - realm\n")
        assert data["mode"] == "procedure"
        assert data["budgets"]["sentence_words"] == 18
        assert data["domain_vocabulary"] == ["harness", "realm"]

    def test_yaml_file_load(self, tmp_path):
        p = tmp_path / "techlint.yaml"
        p.write_text("mode: procedure\ndomain_vocabulary:\n  - harness\n")
        cfg = Config.load(p)
        assert cfg.mode == "procedure" and cfg.is_domain_word("harness")

    def test_disable_rule(self):
        findings, _s, _r = lint_text("This guide delves into it.",
                                     config=Config(disable={"AI-VOCAB"}))
        assert not [f for f in findings if f.rule == "AI-VOCAB"]


class TestStats:
    def test_stall_pair(self):
        para = ("The scheduler assigns each pending job to an available worker "
                "node based on the current resource utilization of the cluster "
                "and on the declared resource requirements of the job itself, "
                "which the submitter provides.")
        echo = ("The scheduler places every waiting job onto some free worker "
                "node according to the cluster resource utilization at the time "
                "and according to the resource requirements the job declared "
                "when the submitter provided them.")
        findings, _s, _r = lint_text(f"{para}\n\n{echo}", config=Config())
        assert [f for f in findings if f.rule == "STAT-STALL"]

    def test_echo_is_off_by_default(self):
        text = "\n\n".join(
            ["The quick brown fox jumps over the lazy sleeping dog again today."] * 3)
        findings, _s, _r = lint_text(text, config=Config())
        assert not [f for f in findings if f.rule == "STAT-ECHO"]

    def test_echo_can_be_enabled(self):
        text = "\n\n".join(
            ["The quick brown fox jumps over the lazy sleeping dog again today."] * 3)
        findings, _s, _r = lint_text(
            text, config=Config(budgets={"echo_ngrams": True}))
        assert [f for f in findings if f.rule == "STAT-ECHO"]

    def test_empty_abstraction(self):
        text = ("The transformation of the organizational capability landscape "
                "requires an alignment of strategy with the fundamental "
                "principles of operational excellence and innovation.")
        findings, _s, _r = lint_text(text, config=Config())
        assert [f for f in findings if f.rule == "STAT-ABSTRACT"]


def run(*args, stdin=""):
    return subprocess.run([sys.executable, "-m", "techlint", *args],
                          input=stdin, capture_output=True, text=True)


class TestCli:
    def test_clean_file_exits_zero(self, tmp_path):
        f = tmp_path / "ok.md"
        f.write_text("Remove the four bolts. Install the new panel.\n")
        r = run(str(f), "--no-config", "--no-baseline")
        assert r.returncode == 0, r.stdout + r.stderr

    def test_blocker_fails(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("As an AI language model, I cannot verify this.\n")
        r = run(str(f), "--no-config", "--no-baseline")
        assert r.returncode == 1 and "AI-ARTIFACT" in r.stdout

    def test_gate_on_wscore(self, tmp_path):
        f = tmp_path / "slop.md"
        f.write_text("This guide delves into the intricacies of the platform, "
                     "showcasing its meticulously crafted realm.\n")
        assert run(str(f), "--no-config", "--no-baseline",
                   "--gate", "1000").returncode == 0
        assert run(str(f), "--no-config", "--no-baseline",
                   "--gate", "1").returncode == 1

    def test_json_output(self, tmp_path):
        f = tmp_path / "d.md"
        f.write_text("This guide delves into the API.\n")
        r = run(str(f), "--no-config", "--no-baseline",
                "--format", "json", "--fail-on", "never")
        data = json.loads(r.stdout)
        assert "AI-VOCAB" in {x["rule"] for x in data["findings"]}
        assert data["summary"]["wscore"] > 0

    def test_github_format(self, tmp_path):
        f = tmp_path / "d.md"
        f.write_text("This guide delves into the API.\n")
        r = run(str(f), "--no-config", "--no-baseline", "--format", "github",
                "--fail-on", "never")
        assert "::error file=" in r.stdout

    def test_only_battery(self, tmp_path):
        f = tmp_path / "d.md"
        f.write_text("In order to proceed, utilize the delve command.\n")
        r = run(str(f), "--no-config", "--no-baseline", "--only", "ai",
                "--format", "json", "--fail-on", "never")
        rules = {x["rule"] for x in json.loads(r.stdout)["findings"]}
        assert not any(r.startswith("CLARITY-") for r in rules)

    def test_stdin(self):
        r = run("-", "--no-config", "--no-baseline", "--fail-on", "never",
                stdin="This guide delves into the API.\n")
        assert "AI-VOCAB" in r.stdout

    def test_explain(self):
        r = run("--explain", "AI-VOCAB")
        assert r.returncode == 0 and "Kobak" in r.stdout

    def test_list_rules(self):
        r = run("--list-rules")
        assert r.returncode == 0 and "CLARITY-PASSIVE" in r.stdout

    def test_baseline_suggest(self, tmp_path):
        f = tmp_path / "d.md"
        f.write_text("This guide delves into the API.\n")
        r = run(str(f), "--no-config", "--no-baseline", "--baseline-suggest")
        line = json.loads(r.stdout.strip().splitlines()[0])
        assert line["rule"] and line["why"].startswith("TODO")

    def test_directory_walk(self, tmp_path):
        (tmp_path / "a.md").write_text("This guide delves into the API.\n")
        (tmp_path / "b.md").write_text("Plain text here.\n")
        r = run(str(tmp_path), "--no-config", "--no-baseline",
                "--format", "json", "--fail-on", "never")
        assert json.loads(r.stdout)["summary"]["files"] == 2


class TestPathCollection:
    """`techlint .` must not walk into vendor and build directories."""

    def _tree(self, tmp_path):
        for rel in ("README.md",
                    "docs/guide.md",
                    "node_modules/pkg/README.md",
                    ".venv/lib/doc.md",
                    "build/out.md",
                    "dist/x.md",
                    "target/y.md",
                    "__pycache__/z.md",
                    "vendor/v.md"):
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# heading\n")
        return tmp_path

    def test_vendor_dirs_skipped(self, tmp_path):
        from techlint.cli import collect
        root = self._tree(tmp_path)
        found = {str(Path(f).relative_to(root)) for f in collect([str(root)], Config())}
        assert found == {"README.md", "docs/guide.md"}

    def test_without_config_nothing_is_skipped(self, tmp_path):
        from techlint.cli import collect
        root = self._tree(tmp_path)
        assert len(collect([str(root)])) > 2

    def test_custom_exclude_pattern(self, tmp_path):
        from techlint.cli import collect
        root = self._tree(tmp_path)
        found = collect([str(root)], Config(exclude=["docs"]))
        assert all("docs" not in f for f in found)

    def test_glob_exclude_pattern(self, tmp_path):
        from techlint.cli import collect
        (tmp_path / "generated-api.md").write_text("# x\n")
        (tmp_path / "handwritten.md").write_text("# x\n")
        found = collect([str(tmp_path)], Config(exclude=["generated-*"]))
        assert len(found) == 1 and found[0].endswith("handwritten.md")

    def test_explicit_file_beats_exclude(self, tmp_path):
        from techlint.cli import collect
        root = self._tree(tmp_path)
        target = str(root / "node_modules" / "pkg" / "README.md")
        assert collect([target], Config()) == [target]

    def test_no_duplicates_across_globs(self, tmp_path):
        from techlint.cli import collect
        (tmp_path / "a.md").write_text("# x\n")
        (tmp_path / "b.txt").write_text("x\n")
        found = collect([str(tmp_path)], Config())
        assert len(found) == len(set(found)) == 2


class TestReleaseTooling:
    """The release pipeline trusts these two invariants."""

    def test_changelog_has_section_for_current_version(self):
        import techlint
        sys.path.insert(0, "tools")
        from release_notes import extract
        text = Path("CHANGELOG.md").read_text()
        notes = extract(techlint.__version__, text)
        assert len(notes.split()) > 20  # a real entry, not a stub

    def test_extract_unknown_version_fails_loudly(self):
        sys.path.insert(0, "tools")
        from release_notes import extract
        with pytest.raises(SystemExit, match="no section"):
            extract("99.99.99", "# Changelog\n\n## 1.0.0\n\nnotes\n")

    def test_extract_takes_only_its_own_section(self):
        sys.path.insert(0, "tools")
        from release_notes import extract
        log = "# Changelog\n\n## 2.0.0 — 2026-01-01\n\nnew\n\n## 1.0.0\n\nold\n"
        assert extract("2.0.0", log) == "new\n"
        assert extract("1.0.0", log) == "old\n"

    def test_package_version_matches_pyproject(self):
        import techlint
        try:
            import tomllib
        except ImportError:      # Python 3.9/3.10
            pytest.skip("tomllib requires Python 3.11+; CI covers this on 3.12")
        with open("pyproject.toml", "rb") as f:
            assert tomllib.load(f)["project"]["version"] == techlint.__version__

"""The numbers quoted in the docs must match the committed calibration run.

Every prose claim about how well this tool separates canon from slop is a
measurement, and a measurement that drifts from its source is just a number
someone liked. This suite makes `benchmarks/results/calibration.json` the
single source of truth and fails when the README or the calibration doc
disagrees with it.

It exists because they did disagree: the docs advertised 2.12/1k over "47k
words" at 72x separation for several releases after the real figures had moved
to 2.14 over 67k words at 71x. Nothing caught it, because prose is not code.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "benchmarks" / "results" / "calibration.json"


@pytest.fixture(scope="module")
def truth():
    """The figures of record, derived from the committed calibration run."""
    d = json.loads(RESULTS.read_text())
    good = d["known_good"]
    mean = d["known_good_wscore"]
    bad = d["known_bad"][0]["wscore"]
    scores = [t["wscore"] for t in good]
    return {
        "mean": mean,
        "bad": round(bad, 1),
        "separation": round(bad / mean),
        "texts": len(good),
        "kwords": sum(t["words"] for t in good) // 1000,
        "low": min(scores),
        "high": max(scores),
    }


def _on_line(doc: str, anchor: str, pattern: str) -> str:
    """The first `pattern` capture on the first line containing `anchor`."""
    for line in doc.splitlines():
        if anchor in line:
            m = re.search(pattern, line)
            if m:
                return m.group(1)
            raise AssertionError(
                f"line with {anchor!r} no longer matches {pattern!r}: {line!r}")
    raise AssertionError(f"no line containing {anchor!r}")


class TestReadmeMatchesCalibration:
    @staticmethod
    @pytest.fixture(scope="class")
    def doc():
        return (ROOT / "README.md").read_text()

    def test_known_good_mean(self, doc, truth):
        claimed = _on_line(doc, "pre-LLM technical canon", r"\*\*([\d.]+)\*\*")
        assert float(claimed) == truth["mean"]

    def test_corpus_size(self, doc, truth):
        anchor = "pre-LLM technical canon"
        assert int(_on_line(doc, anchor, r"\((\d+)k words")) == truth["kwords"]
        assert int(_on_line(doc, anchor, r"(\d+) texts")) == truth["texts"]

    def test_known_good_range(self, doc, truth):
        anchor = "pre-LLM technical canon"
        assert float(_on_line(doc, anchor, r"range ([\d.]+)")) == truth["low"]
        assert float(_on_line(doc, anchor, r"range [\d.]+.([\d.]+)")) == truth["high"]

    def test_known_bad_fixture(self, doc, truth):
        claimed = _on_line(doc, "slop-dense fixture", r"\*\*([\d.]+)\*\*")
        assert float(claimed) == truth["bad"]

    def test_separation(self, doc, truth):
        claimed = _on_line(doc, "| **separation**", r"\*\*(\d+)×\*\*")
        assert int(claimed) == truth["separation"]


class TestCalibrationDocMatchesCalibration:
    @staticmethod
    @pytest.fixture(scope="class")
    def doc():
        return (ROOT / "docs" / "calibration.md").read_text()

    def test_known_good_mean(self, doc, truth):
        claimed = _on_line(doc, "known-good weighted mean", r"\*\*([\d.]+)\*\*")
        assert float(claimed) == truth["mean"]

    def test_corpus_size(self, doc, truth):
        anchor = "known-good weighted mean"
        assert int(_on_line(doc, anchor, r"\((\d+) texts")) == truth["texts"]
        assert int(_on_line(doc, anchor, r"~(\d+)k words")) == truth["kwords"]

    def test_known_good_range(self, doc, truth):
        anchor = "| known-good range"
        assert float(_on_line(doc, anchor, r"([\d.]+) \(")) == truth["low"]
        assert float(_on_line(doc, anchor, r"[\d.]+ \(.*?.\s*([\d.]+) \(")) == truth["high"]

    def test_known_bad_fixture(self, doc, truth):
        claimed = _on_line(doc, "| known-bad fixture", r"\*\*([\d.]+)\*\*")
        assert float(claimed) == truth["bad"]

    def test_separation(self, doc, truth):
        claimed = _on_line(doc, "| **separation**", r"\*\*(\d+)×\*\*")
        assert int(claimed) == truth["separation"]

    def test_latest_round_row_is_current_state(self, doc, truth):
        """The last row of the round-history table is the state we ship."""
        rows = [ln for ln in doc.splitlines()
                if re.match(r"\|\s*\d+\s*\|", ln.strip())]
        assert rows, "round-history table not found"
        cells = [c.strip() for c in rows[-1].strip().strip("|").split("|")]
        assert float(cells[2]) == truth["mean"]
        assert float(cells[3].rstrip("×")) == pytest.approx(
            truth["bad"] / truth["mean"], abs=0.1)


class TestSeparationFloor:
    """The floor CI enforces; pinned here so a local run catches it first."""

    def test_separation_exceeds_ci_gate(self, truth):
        assert truth["bad"] / truth["mean"] >= 20

    def test_committed_results_are_not_empty(self, truth):
        assert truth["texts"] >= 10
        assert truth["kwords"] >= 40

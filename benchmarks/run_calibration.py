#!/usr/bin/env python3
"""Run techlint over the calibration corpus and report per-rule firing rates.

Two controls, following the calibration program of the sibling projects:

  known-good  pre-LLM human technical writing (benchmarks/corpus/). Any rule
              that fires often here is an instrument bug, not a finding about
              the document. Fix the rule or demote it to a budget.
  known-bad   a committed, deliberately slop-dense fixture
              (benchmarks/known_bad.md). The separation between the two sets
              is the only evidence the instrument measures anything.

Writes benchmarks/results/calibration.json and prints a summary table.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from techlint import Config, lint_file, lint_text          # noqa: E402
from techlint.finding import Severity                      # noqa: E402

HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
RESULTS = HERE / "results"
KNOWN_BAD = HERE / "known_bad.md"


def profile(name, text, config):
    findings, _sup, report = lint_text(text, path=name, config=config)
    per_1k = Counter()
    words = max(report["words"], 1)
    for f in findings:
        per_1k[f.rule] += 1
    return {
        "name": name,
        "words": report["words"],
        "wscore": report["wscore"],
        "counts": report["counts"],
        "rules_per_1k": {r: round(n / words * 1000, 2)
                         for r, n in sorted(per_1k.items(), key=lambda kv: -kv[1])},
    }


def main() -> int:
    config = Config(mode="reference")
    texts = sorted(CORPUS.glob("*.txt"))
    if not texts:
        print("no corpus; run: python benchmarks/fetch.py", file=sys.stderr)
        return 1

    good = [profile(p.name, p.read_text(errors="replace"), config) for p in texts]
    bad = []
    if KNOWN_BAD.exists():
        bad = [profile(KNOWN_BAD.name, KNOWN_BAD.read_text(), config)]

    gw = sum(g["words"] for g in good)
    gscore = round(sum(g["wscore"] * g["words"] for g in good) / max(gw, 1), 2)

    agg = Counter()
    for g in good:
        for rule, rate in g["rules_per_1k"].items():
            agg[rule] += rate * g["words"]
    corpus_rates = {r: round(v / gw, 2) for r, v in agg.most_common()}

    print(f"{'text':28s} {'words':>7s} {'wscore':>7s}  top rules (per 1k)")
    for g in good:
        top = ", ".join(f"{r}={v}" for r, v in list(g["rules_per_1k"].items())[:3])
        print(f"{g['name']:28s} {g['words']:7d} {g['wscore']:7.2f}  {top}")
    for b in bad:
        top = ", ".join(f"{r}={v}" for r, v in list(b["rules_per_1k"].items())[:3])
        print(f"{'[KNOWN BAD] ' + b['name']:28s} {b['words']:7d} {b['wscore']:7.2f}  {top}")

    print(f"\nknown-good weighted mean wscore: {gscore}")
    if bad:
        sep = round(bad[0]["wscore"] / max(gscore, 0.01), 1)
        print(f"known-bad wscore:                {bad[0]['wscore']}  "
              f"(separation {sep}x)")
        if sep < 5:
            print("  WARNING: separation under 5x. The instrument is not "
                  "discriminating; tighten rules or strengthen the fixture.")

    print("\nrules firing on human pre-LLM technical writing "
          "(candidates for demotion):")
    for rule, rate in corpus_rates.items():
        flag = "  <-- review" if rate >= 1.0 else ""
        print(f"  {rule:22s} {rate:6.2f}/1k{flag}")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "calibration.json"
    out.write_text(json.dumps({
        "known_good": good,
        "known_bad": bad,
        "known_good_wscore": gscore,
        "corpus_rule_rates_per_1k": corpus_rates,
    }, indent=1) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

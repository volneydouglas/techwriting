#!/usr/bin/env python3
"""Build the tiered AI excess-vocabulary list from the Kobak et al. dataset.

Source
------
Kobak D., González-Márquez R., Horvát E.-Á., Lause J. (2025).
"Delving into LLM-assisted writing in biomedical publications through excess
vocabulary." Science Advances 11(30). Data: github.com/berenslab/llm-excess-vocab
(MIT). The study tracked word frequencies across 15M PubMed abstracts
(2010-2024) and identified words whose 2024 frequency far exceeded the
pre-LLM trend.

Why tiers instead of a flat list
--------------------------------
Of the 407 words the authors annotate as "style" words, the excess ratio spans
28x (delves) down to 0.4x (verifies). Words at the bottom -- "using", "however",
"analysis", "research", "were", "based" -- are ordinary technical English and
flagging them would drown the signal. We tier by measured effect size:

    ratio >= 5.0   STRONG   a genuine tell; ~1 in 5 uses is LLM residue
    ratio >= 2.5   MODERATE worth a look in context
    ratio >= 1.6   MILD     budgeted; only flagged in bulk
    ratio <  1.6   dropped  not a signal

Method
------
The paper's counterfactual for 2024 is a linear extrapolation of the 2021->2022
trend (the last two pre-ChatGPT years). We reproduce that:

    expected_2024 = f2022 + 2 * (f2022 - f2021)
    ratio         = f2024 / expected_2024

Usage
-----
    python tools/build_excess_vocab.py            # downloads both inputs
    python tools/build_excess_vocab.py <words.csv> <yearly-counts.csv.gz>
"""

import csv
import gzip
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/berenslab/llm-excess-vocab/main/results"
WORDS_URL = f"{BASE}/excess_words.csv"
COUNTS_URL = f"{BASE}/yearly-counts.csv.gz"

OUT = Path(__file__).resolve().parent.parent / "techlint" / "data" / "ai_excess_vocab.json"

TIERS = [(5.0, "strong"), (2.5, "moderate"), (1.6, "mild")]

# Words the study flags that are load-bearing in technical prose. Technical
# writing legitimately says "the API exposes", "the daemon holds a lock". We
# drop these regardless of ratio -- domain literal usage is exemption #2 of the
# exemption taxonomy, applied here at build time.
DOMAIN_LITERAL = {
    "address", "addresses", "addressing", "assess", "assessed", "assessing",
    "based", "conducted", "demonstrated", "demonstrates", "exhibit", "exhibits",
    "exhibited", "hold", "holds", "identified", "involves", "involving",
    "linked", "maintaining", "need", "observed", "offer", "offers", "persist",
    "presents", "remains", "using", "were", "this", "their", "between",
    "during", "however", "analysis", "research", "findings", "outcomes",
    "conditions", "limitations", "impact", "role", "approach", "primary",
    "potential", "various", "specifically", "typically", "initially",
    "subsequently", "particularly", "predominantly", "effectively", "within",
    "challenge", "challenges", "complex", "distinct", "precise", "substantial",
    "integration", "techniques", "strategies", "capabilities", "individuals",
    "declare", "declared", "verifies", "align", "aligns", "aligning",
}


def fetch(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, dest)
    return dest


def load_counts(path: Path):
    rows, years = {}, None
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        r = csv.reader(f)
        years = next(r)[1:]
        for row in r:
            rows[row[0]] = [int(x) for x in row[1:]]
    return rows, {y: i for i, y in enumerate(years)}


def build(words_csv: Path, counts_path: Path) -> dict:
    rows, iy = load_counts(counts_path)
    totals = rows[""]                      # final row: abstracts per year

    def freq(word, year):
        c = rows.get(word)
        return None if c is None else c[iy[year]] / totals[iy[year]]

    out = {}
    for rec in csv.DictReader(open(words_csv)):
        if rec["type"] != "style":
            continue
        w = rec["word"].lower()
        if w in DOMAIN_LITERAL or len(w) < 4:
            continue
        f21, f22, f24 = freq(w, "2021"), freq(w, "2022"), freq(w, "2024")
        if not f21 or not f22 or f24 is None:
            continue
        expected = f22 + 2 * (f22 - f21)
        if expected <= 0:
            expected = f22
        ratio = f24 / expected
        tier = next((t for cut, t in TIERS if ratio >= cut), None)
        if tier is None:
            continue
        out[w] = {"ratio": round(ratio, 2), "tier": tier,
                  "pos": rec["part_of_speech"]}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["ratio"]))


def main() -> None:
    tmp = Path(__file__).resolve().parent.parent / ".cache"
    tmp.mkdir(exist_ok=True)
    if len(sys.argv) == 3:
        words_csv, counts = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        words_csv = fetch(WORDS_URL, tmp / "excess_words.csv")
        counts = fetch(COUNTS_URL, tmp / "yearly-counts.csv.gz")

    vocab = build(words_csv, counts)
    payload = {
        "_source": "Kobak et al. 2025, Science Advances 11(30); "
                   "data github.com/berenslab/llm-excess-vocab (MIT)",
        "_method": "ratio = f2024 / (f2022 + 2*(f2022 - f2021)); "
                   "tiers strong>=5.0, moderate>=2.5, mild>=1.6",
        "words": vocab,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n")
    tiers = {}
    for v in vocab.values():
        tiers[v["tier"]] = tiers.get(v["tier"], 0) + 1
    print(f"wrote {OUT} — {len(vocab)} words {tiers}")


if __name__ == "__main__":
    main()

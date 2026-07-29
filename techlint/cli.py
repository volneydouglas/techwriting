"""techlint command line.

    techlint docs/*.md                       lint
    techlint --mode procedure runbook.md     20-word budget, RFC-2119 checks
    techlint --gate 3.0 docs/                CI: fail if wscore exceeds 3.0
    techlint --only ai README.md             AI tics only
    techlint --explain AI-VOCAB              what a rule means and where it came from
    techlint --baseline-suggest docs/        emit baseline lines for review
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .baseline import DEFAULT_NAME, Baseline
from .config import Config
from .engine import aggregate, lint_file, lint_text
from .finding import Axis, Severity

COLORS = {
    Severity.BLOCKER: "\033[1;31m",
    Severity.MAJOR: "\033[31m",
    Severity.MINOR: "\033[33m",
    Severity.INFO: "\033[36m",
}
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"

RULE_DOCS = {
    "AI-ARTIFACT": "Chat-assistant text left in the document (chat frame, "
                   "pleasantries, unfilled placeholders, appeals to unnamed studies). "
                   "No legitimate use in a technical document.",
    "AI-COPULA": "The copula daisy-chain (\"was the X, and the X was\"). "
                 "Zero occurrences in ~1M words of human prose (prose-smells calibration).",
    "AI-PHRASE": "Stock phrasal and syntactic templates: throat-clearing, scene-setting, "
                 "antithesis, self-posed Q&A, participial editorializing, essay closers.",
    "AI-VOCAB": "Words whose post-LLM frequency exceeds the pre-LLM trend. Tiered by "
                "measured ratio: strong (>=5x) major, moderate (>=2.5x) minor, "
                "mild (>=1.6x) info. Source: Kobak et al. 2025, 15M PubMed abstracts.",
    "AI-DASH": "Em-dash density above budget. Sustained interruption is a current-model rhythm.",
    "AI-TRIAD": "Three-item lists in a large share of sentences.",
    "AI-OPENER": "Sentences opening with stock transitions instead of content.",
    "AI-HEDGE": "Three or more hedges in one sentence.",
    "AI-INTENSIFY": "Intensifier density; emphasis substituting for evidence.",
    "AI-BOLDLIST": "Runs of '**Term:** explanation' bullets — the listicle skeleton.",
    "AI-UNIFORM": "Low sentence-length variance (burstiness).",
    "AI-EMOJI": "Decorative emoji in technical prose.",
    "CLARITY-LENGTH": "Sentence over the mode's word budget. A budget, not a ban.",
    "CLARITY-PARA": "Paragraph over the sentence budget; likely more than one topic.",
    "CLARITY-PASSIVE": "Passive voice. Agentless obligation (\"must be configured\") is "
                       "the costly case: the reader cannot tell who acts.",
    "CLARITY-NOMINAL": "A verb buried in a noun (\"perform a calculation\" -> \"calculate\").",
    "CLARITY-WORDY": "Multi-word phrase with a one-word equivalent.",
    "CLARITY-SVDIST": "Long interruption between subject and verb (Gopen & Swan).",
    "CLARITY-STRESS": "Sentence ends on a qualifier instead of its point (Gopen & Swan).",
    "CLARITY-LATIN": "Latin abbreviation; translates poorly and is often misused.",
    "CLARITY-INCLUSIVE": "Gendered or non-inclusive term.",
    "CLARITY-NORMATIVE": "\"shall\"/\"should\" in procedural text (RFC 2119 discipline).",
    "CLARITY-LOCALE": "Spelling inconsistent with the configured locale.",
    "CLARITY-CONTRACTION": "Contraction, when house style disallows them (off by default).",
    "CLARITY-THAT": "Dropped \"that\" after make sure/verify/confirm.",
    "STAT-STALL": "Adjacent paragraphs share most content words; the second may restate.",
    "STAT-ECHO": "A long phrase repeated within the document.",
    "STAT-ABSTRACT": "Long, abstract sentence with few new content words (the bits test).",
    "AI-LINK": "A relative link or heading anchor that does not resolve. Generated docs "
               "routinely cite files and sections that were never written.",
    "AI-PROSE-RATIO": "Most of the document is tables, bullets, and headings rather than "
                      "prose — scaffolding standing in for explanation.",
    "DOC-LINKTEXT": "Link text that does not say where it goes (\"click here\"). "
                    "Google, Microsoft, WCAG 2.4.4.",
    "DOC-CONDESCEND": "Words that tell the reader how they should find this: simply, "
                      "just, easy, obviously. Google word list; Microsoft.",
    "DOC-PLEASE": "\"Please\" in instructions. Google: documentation instructs.",
    "DOC-ALLOWS": "\"allows you to\" — Google prefers \"lets you\".",
    "DOC-PERSON": "Third person about the reader (\"the user must\") instead of \"you\".",
    "DOC-TENSE": "Future tense for present behavior (\"will return\" -> \"returns\").",
    "DOC-ACRONYM": "An acronym never expanded. IEEE 1063, ISO/IEC 26514.",
    "DOC-HEADING": "Skipped heading level or multiple level-1 headings. WCAG 1.3.1.",
    "DOC-ALT": "Image with no alt text. WCAG 1.1.1.",
    "DOC-ACTION": "Procedure spends many words before its first instruction. "
                  "Carroll's minimalism; Diátaxis separates how-to from explanation.",
    "DOC-READABILITY": "Flesch-Kincaid grade level above target. A proxy, not a verdict.",
}

DOC_GLOBS = ("*.md", "*.markdown", "*.txt", "*.rst")


def build_parser():
    p = argparse.ArgumentParser(
        prog="techlint",
        description="Technical-writing linter with AI-tic detection.")
    p.add_argument("paths", nargs="*",
                   help="files or directories to lint, or '-' for stdin")
    p.add_argument("--mode", choices=["procedure", "reference", "narrative"],
                   help="sets sentence/paragraph budgets (default: reference, "
                        "or the value in techlint.yaml)")
    p.add_argument("--locale", choices=["us", "gb"])
    p.add_argument("--config", help="path to techlint.yaml (default: search upward)")
    p.add_argument("--no-config", action="store_true", help="ignore any config file")
    p.add_argument("--only", choices=["ai", "clarity", "docs", "stats"], action="append",
                   default=[], help="run only these batteries (repeatable)")
    p.add_argument("--disable", action="append", default=[], metavar="RULE")
    p.add_argument("--baseline", default=DEFAULT_NAME,
                   help=f"suppression baseline file (default: {DEFAULT_NAME})")
    p.add_argument("--no-baseline", action="store_true")
    p.add_argument("--baseline-suggest", action="store_true",
                   help="print baseline JSONL lines for the current findings; "
                        "add a `why` to each before committing")
    p.add_argument("--min-severity", choices=Severity.ALL, default=Severity.INFO)
    p.add_argument("--format", choices=["text", "json", "github", "summary"],
                   default="text")
    p.add_argument("--gate", type=float, metavar="WSCORE",
                   help="exit 1 if the weighted score exceeds this")
    p.add_argument("--fail-on", choices=[*Severity.ALL, "never"], default="blocker",
                   help="exit 1 when a finding at or above this severity exists "
                        "(default: blocker)")
    p.add_argument("--explain", metavar="RULE",
                   help="describe a rule and its basis, then exit")
    p.add_argument("--list-rules", action="store_true")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--version", action="version", version=f"techlint {__version__}")
    return p


def collect(paths, config=None):
    """Expand paths to documents.

    Directories are walked recursively for DOC_GLOBS, skipping vendor, build,
    and dot directories (see config.DEFAULT_EXCLUDES). Files named explicitly
    on the command line are always linted, even inside an excluded directory --
    an exclude list should filter a sweep, not override an instruction.
    """
    out, seen = [], set()
    for raw in paths:
        p = Path(raw)
        if raw == "-":
            out.append(raw)
        elif p.is_dir():
            found = []
            for g in DOC_GLOBS:
                found.extend(p.rglob(g))
            for x in sorted(found):
                rel = x.relative_to(p) if p != Path(".") else x
                if config and config.excluded(rel):
                    continue
                s = str(x)
                if s not in seen:
                    seen.add(s)
                    out.append(s)
        else:
            out.append(str(p))
    return out


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.explain:
        rule = args.explain.upper()
        doc = RULE_DOCS.get(rule)
        if not doc:
            print(f"unknown rule {rule!r}. --list-rules shows them all.",
                  file=sys.stderr)
            return 2
        print(f"{rule}\n\n{doc}\n\nBasis and citations: docs/research-basis.md")
        return 0
    if args.list_rules:
        for rule, doc in sorted(RULE_DOCS.items()):
            print(f"{rule:22s} {doc.splitlines()[0]}")
        return 0
    if not args.paths:
        build_parser().print_usage(sys.stderr)
        return 2

    overrides = {}
    if args.mode:
        overrides["mode"] = args.mode
    if args.locale:
        overrides["locale"] = args.locale
    if args.only:
        overrides["enable_ai"] = "ai" in args.only
        overrides["enable_clarity"] = "clarity" in args.only
        overrides["enable_docs"] = "docs" in args.only
        overrides["enable_stats"] = "stats" in args.only

    try:
        if args.no_config:
            config = Config(**overrides)
        elif args.config:
            config = Config.load(args.config, **overrides)
        else:
            config = Config.find(".", **overrides)
        config.disable |= set(args.disable)
        baseline = Baseline() if args.no_baseline else Baseline.load(args.baseline)
    except (ValueError, OSError) as e:
        print(f"techlint: {e}", file=sys.stderr)
        return 2

    files = collect(args.paths, config)
    if not files:
        print("techlint: no documents found", file=sys.stderr)
        return 2

    all_findings, reports = [], []
    for path in files:
        try:
            if path == "-":
                res = lint_text(sys.stdin.read(), "<stdin>", config, baseline)
            else:
                res = lint_file(path, config, baseline)
        except OSError as e:
            print(f"techlint: cannot read {path}: {e}", file=sys.stderr)
            return 2
        findings, _suppressed, report = res
        all_findings.extend(findings)
        reports.append(report)

    total = aggregate(reports, config.bands)
    rank = Severity.ORDER[args.min_severity]
    shown = [f for f in all_findings if Severity.ORDER[f.severity] >= rank]

    if args.baseline_suggest:
        for f in shown:
            print(Baseline.entry(f, why="TODO: why is this one legitimate?"))
        return 0

    if args.format == "json":
        print(json.dumps({"findings": [f.to_dict() for f in shown],
                          "files": reports, "summary": total}, indent=2))
    elif args.format == "github":
        for f in shown:
            level = ("error" if f.severity in (Severity.BLOCKER, Severity.MAJOR)
                     else "warning" if f.severity == Severity.MINOR else "notice")
            msg = f.message
            if f.suggestion:
                msg += f" Fix: {f.suggestion}"
            print(f"::{level} file={f.path},line={f.line},col={f.col},"
                  f"title={f.rule}::{msg}")
    elif args.format == "summary":
        _print_summary(reports, total, color=_want_color(args))
    else:
        _print_text(shown, reports, total, color=_want_color(args))

    if args.gate is not None and total["wscore"] > args.gate:
        print(f"\ntechlint: weighted score {total['wscore']} exceeds gate "
              f"{args.gate}", file=sys.stderr)
        return 1
    if args.fail_on != "never":
        threshold = Severity.ORDER[args.fail_on]
        if any(Severity.ORDER[f.severity] >= threshold for f in all_findings):
            return 1
    return 0


def _want_color(args) -> bool:
    return not args.no_color and sys.stdout.isatty()


def _print_text(findings, reports, total, color: bool):
    def c(code, text):
        return f"{code}{text}{RESET}" if color else text

    for f in findings:
        loc = f"{f.path}:{f.line}:{f.col}"
        print(f"{c(BOLD, loc)} {c(COLORS[f.severity], f.severity)} "
              f"{c(BOLD, f.rule)} {f.message}")
        if f.extract and f.extract not in f.message:
            print(f"    > {f.extract}")
        if f.suggestion:
            print(f"    fix: {f.suggestion}")
        if f.why:
            print(f"    {c(DIM, 'why: ' + f.why)}")
    if findings:
        print()
    _print_summary(reports, total, color)


def _print_summary(reports, total, color: bool):
    def c(code, text):
        return f"{code}{text}{RESET}" if color else text

    if len(reports) > 1:
        for r in reports:
            parts = [f"{n} {s}" for s, n in r["counts"].items() if n]
            print(f"  {r['path']}: " + (", ".join(parts) if parts else "clean")
                  + f"  [wscore {r['wscore']}]")
    cts = total["counts"]
    line = ", ".join(f"{n} {s}" for s, n in cts.items() if n) or "no findings"
    print(f"{total['files']} file(s), {total['words']} words: {line}")

    axes = total.get("axes") or {}
    if any(axes.values()):
        print()
        width = max(len(a) for a in Axis.ALL)
        for name in Axis.ALL:
            score = axes.get(name, 0.0)
            if not score:
                continue
            bar = "█" * min(30, max(1, round(score * 30 / max(total["wscore"], 1))))
            print(f"  {name:<{width}}  {score:6.2f}  {bar}  {Axis.ADVICE[name]}")
        print()

    print(f"weighted score {c(BOLD, total['wscore'])}/1k words — "
          f"{c(BOLD, total['verdict'])}"
          + (f" ({total['suppressed']} suppressed by baseline)"
             if total["suppressed"] else ""))


if __name__ == "__main__":
    sys.exit(main())

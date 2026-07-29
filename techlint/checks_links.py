"""Reference validation -- the "does this actually exist" axis.

Borrowed from the sloppylint project, which validates that imported Python
packages exist because roughly a fifth of AI-suggested imports name packages
that do not. Prose has the same failure mode in a different costume: generated
documentation confidently links to files, anchors, and sections that were never
written.

Everything here is offline and deterministic. No network, no dependencies. A
link that points inside the repository can be checked against the filesystem;
a heading anchor can be checked against the document's own headings. Both are
cheap, and both catch a class of error that no amount of prose review reliably
finds.

Out of scope on purpose: external URLs. Checking those needs the network,
makes the linter non-deterministic, and turns every CI run into someone else's
uptime problem.
"""

import re
from pathlib import Path
from urllib.parse import unquote

from .finding import Finding, Severity

LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\(\s*([^)\s]+?)\s*(?:\"[^\"]*\")?\s*\)")
IMAGE_RE = re.compile(r"!\[([^\]\n]*)\]\(\s*([^)\s]+?)\s*(?:\"[^\"]*\")?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
FENCE_RE = re.compile(r"(?ms)^\s*(```|~~~).*?^\s*\1")

EXTERNAL = ("http://", "https://", "mailto:", "ftp://", "tel:", "//")


def _anchor(heading: str) -> str:
    """GitHub's heading-to-anchor transform, closely enough."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\*\*|__|\*|_|~~", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def _anchors_of(text: str) -> set:
    body = FENCE_RE.sub("", text)
    return {_anchor(m.group(2)) for m in HEADING_RE.finditer(body)}


def check_links(doc, config):
    """Relative links must resolve; in-document anchors must exist."""
    if not config.budgets.get("check_links", True):
        return
    if not doc.path or doc.path == "<stdin>":
        return
    source = Path(doc.path)
    base = source.parent
    body = FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), doc.raw)
    own_anchors = _anchors_of(doc.raw)

    for rx, kind in ((LINK_RE, "link"), (IMAGE_RE, "image")):
        for m in rx.finditer(body):
            target = m.group(2).strip()
            if not target or target.startswith(EXTERNAL) or target.startswith("<"):
                continue
            line = body[: m.start()].count("\n") + 1
            col = m.start() - (body.rfind("\n", 0, m.start()) + 1) + 1

            path_part, _, fragment = target.partition("#")
            path_part, fragment = unquote(path_part), unquote(fragment)

            if not path_part:                      # same-document anchor
                if fragment and fragment.lower() not in own_anchors:
                    yield Finding(
                        rule="AI-LINK", severity=Severity.MAJOR,
                        message=f"Anchor \"#{fragment}\" has no matching heading "
                                "in this document.",
                        line=line, col=col, extract=target,
                        suggestion="fix the anchor, or add the section it promises",
                        why="a link to a section that was never written")
                continue

            resolved = (base / path_part).resolve()
            if not resolved.exists():
                yield Finding(
                    rule="AI-LINK", severity=Severity.MAJOR,
                    message=f"Relative {kind} target \"{path_part}\" does not exist.",
                    line=line, col=col, extract=target,
                    suggestion="fix the path, or write the file it points at",
                    why="generated docs routinely cite files that were never created")
                continue

            if fragment and resolved.suffix.lower() in (".md", ".markdown"):
                try:
                    other = resolved.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if fragment.lower() not in _anchors_of(other):
                    yield Finding(
                        rule="AI-LINK", severity=Severity.MINOR,
                        message=f"\"{path_part}\" exists but has no heading "
                                f"matching anchor \"#{fragment}\".",
                        line=line, col=col, extract=target,
                        suggestion="fix the anchor",
                        why="the file is real; the section is not")


def check_prose_ratio(doc, config):
    """How much of the document is prose rather than scaffolding.

    Found by running techlint against another AI-slop linter's README: of 297
    lines, only 254 words were prose. The rest was tables, badges, and bullets.
    A document built almost entirely from tables and bold bullets *performs*
    organization -- it looks thorough while carrying very little the reader can
    act on, and it escapes prose analysis entirely.

    INFO only, and generous: reference tables and API matrices are legitimately
    table-heavy.
    """
    body = FENCE_RE.sub("", doc.raw)
    lines = [l for l in body.splitlines() if l.strip()]
    if len(lines) < 40:
        return
    scaffold = sum(
        1 for l in lines
        if l.lstrip().startswith(("|", "- ", "* ", "+ ", "#", ">"))
        or re.match(r"^\s*\d{1,3}[.)]\s", l)
        or re.match(r"^\s*[|:\-\s]+$", l))
    ratio = scaffold / len(lines)
    threshold = float(config.budgets.get("scaffold_ratio", 0.75))
    if ratio >= threshold:
        yield Finding(
            rule="AI-PROSE-RATIO", severity=Severity.INFO,
            message=f"{ratio:.0%} of non-blank lines are tables, bullets, or "
                    "headings rather than prose.",
            line=1, col=1,
            suggestion="if the tables carry the content, good; if they are "
                       "standing in for explanation, write the explanation",
            why="scaffolding-heavy documents perform thoroughness and escape review")


LINK_CHECKS = [check_links, check_prose_ratio]

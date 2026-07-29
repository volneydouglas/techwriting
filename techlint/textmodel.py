"""Markdown-aware text model with position tracking.

Parses a document into paragraphs and sentences while keeping, for every
character of cleaned text, the (line, col) it came from in the source file, so
every finding can point at the exact source position.

Markdown handling: fenced code blocks and tables are skipped entirely; inline
code and URLs collapse to one opaque token; headings are parsed but excluded
from prose checks; each list item is its own sentence.

Word counting is plain and honest -- one token, one word. (An earlier version
implemented the ASD-STE100 Section 8 counting rules, where a parenthetical or a
number-plus-unit counts as one word. Those rules exist to make the aviation
20-word cap workable and are not meaningful outside that standard.)
"""

import re
from dataclasses import dataclass, field

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$")
TABLE_RE = re.compile(r"^\s*\|")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?")
HTML_TAG_RE = re.compile(r"<[^>\n]{1,120}>")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMPHASIS_RE = re.compile(r"(\*\*\*|\*\*|\*|___|__|(?<![\w])_(?=\w)|(?<=\w)_(?![\w]))")

# Abbreviations that a sentence should not be split after.
NON_TERMINAL_ABBREVS = {
    "no", "fig", "figs", "eq", "sec", "ref", "vol", "ch", "pt", "para",
    "vs", "etc", "e.g", "i.e", "cf", "al", "approx", "dept", "est",
    "max", "min", "rev", "std", "dr", "mr", "mrs", "ms", "jr", "sr", "st",
    "a.m", "p.m", "u.s", "u.k",
}

WORD_RE = re.compile(r"[^\s]+")


@dataclass
class Sentence:
    text: str                    # cleaned sentence text
    line: int                    # 1-based line of first character
    col: int                     # 1-based column of first character
    positions: list = field(default_factory=list, repr=False)  # per-char (line, col)
    kind: str = "prose"          # prose | heading | bullet | note

    def pos_at(self, offset: int):
        """Source (line, col) for a character offset into ``text``."""
        if not self.positions:
            return (self.line, self.col)
        offset = max(0, min(offset, len(self.positions) - 1))
        return self.positions[offset]

    @property
    def words(self):
        return [m.group(0) for m in WORD_RE.finditer(self.text)]


@dataclass
class Paragraph:
    sentences: list
    kind: str = "prose"          # prose | heading | list | table
    line: int = 1


@dataclass
class Document:
    paragraphs: list
    raw: str = ""
    path: str = ""

    @property
    def sentences(self):
        return [s for p in self.paragraphs for s in p.sentences]

    def prose_sentences(self):
        return [s for s in self.sentences if s.kind in ("prose", "bullet")]

    def word_count(self) -> int:
        """Prose words only -- the denominator for every per-1k rate."""
        return sum(len(s.words) for s in self.prose_sentences())


def _clean_inline(line: str, lineno: int):
    """Strip markdown inline syntax; return (text, per-char (line, col) list)."""
    # Build a char->source-col map, then apply replacements that preserve it.
    chars = list(line)
    cols = list(range(1, len(line) + 1))

    def splice(match_iter, repl_fn):
        nonlocal chars, cols
        text = "".join(chars)
        out_chars, out_cols, last = [], [], 0
        for m in match_iter(text):
            out_chars.extend(chars[last:m.start()])
            out_cols.extend(cols[last:m.start()])
            rep = repl_fn(m)
            src_col = cols[m.start()] if m.start() < len(cols) else (cols[-1] if cols else 1)
            out_chars.extend(list(rep))
            out_cols.extend([src_col] * len(rep))
            last = m.end()
        out_chars.extend(chars[last:])
        out_cols.extend(cols[last:])
        chars, cols = out_chars, out_cols

    splice(IMAGE_RE.finditer, lambda m: m.group(1))
    splice(LINK_RE.finditer, lambda m: m.group(1))
    # Inline code and URLs count as one opaque word each (like quoted text).
    splice(INLINE_CODE_RE.finditer, lambda m: "CODE")
    splice(URL_RE.finditer, lambda m: "URL")
    splice(HTML_TAG_RE.finditer, lambda m: "")
    splice(EMPHASIS_RE.finditer, lambda m: "")

    positions = [(lineno, c) for c in cols]
    return "".join(chars), positions


def _split_sentences(text: str, positions: list):
    """Split cleaned block text into sentences with their position maps."""
    sentences = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ".!?":
            # Collect trailing closers like ")" or quotes.
            j = i + 1
            while j < n and text[j] in ")\"'”’]":
                j += 1
            # End of text, or followed by whitespace then an uppercase/digit/bullet.
            nxt = j
            while nxt < n and text[nxt] in " \t":
                nxt += 1
            is_boundary = nxt >= n or text[nxt] == "\n" or (
                nxt > j and (text[nxt].isupper() or text[nxt].isdigit() or text[nxt] in "\"'“‘(")
            )
            if ch == ".":
                # Do not split after decimals (3.5), abbreviations (No.),
                # single initials, or alphanumeric identifiers.
                m = re.search(r"[\w.°%]+$", text[start:i])
                prev = m.group(0).lower() if m else ""
                if i + 1 < n and text[i + 1].isdigit():
                    is_boundary = False
                elif prev in NON_TERMINAL_ABBREVS or (len(prev) == 1 and prev.isalpha()):
                    is_boundary = False
                elif re.fullmatch(r"\d+", prev) and nxt < n and text[nxt].islower():
                    is_boundary = False
            if is_boundary:
                seg = text[start:j]
                _emit(sentences, seg, positions[start:j])
                start = j
                i = j
                continue
        elif ch == "\n":
            # Newlines inside a block only occur for hard breaks we kept.
            pass
        i += 1
    _emit(sentences, text[start:], positions[start:])
    return sentences


def _emit(sentences, seg, seg_positions):
    stripped = seg.strip()
    if not stripped:
        return
    lead = len(seg) - len(seg.lstrip())
    trail = len(seg) - len(seg.rstrip())
    pos = seg_positions[lead:len(seg_positions) - trail or None]
    line, col = pos[0] if pos else (1, 1)
    sentences.append(Sentence(text=stripped, line=line, col=col, positions=pos))


def parse(text: str, path: str = "") -> Document:
    lines = text.splitlines()
    paragraphs = []
    block_text = []       # list of (cleaned_line, positions)
    block_kind = "prose"
    block_line = 1
    in_fence = False

    def flush():
        nonlocal block_text
        if not block_text:
            return
        joined = ""
        positions = []
        for t, p in block_text:
            if joined:
                joined += " "
                positions.append(positions[-1] if positions else (block_line, 1))
            joined += t
            positions.extend(p)
        sentences = _split_sentences(joined, positions)
        for s in sentences:
            s.kind = "bullet" if block_kind == "list" else (
                "heading" if block_kind == "heading" else "prose")
        if sentences:
            paragraphs.append(Paragraph(sentences=sentences, kind=block_kind,
                                        line=sentences[0].line))
        block_text = []

    for idx, raw in enumerate(lines, start=1):
        if FENCE_RE.match(raw):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = BLOCKQUOTE_RE.sub("", raw)
        if not line.strip():
            flush()
            block_kind = "prose"
            continue
        if TABLE_RE.match(line):
            flush()
            block_kind = "prose"
            continue  # tables are layout, not prose
        hm = HEADING_RE.match(line)
        if hm:
            flush()
            block_kind = "heading"
            offset = len(hm.group(1)) + 1
            cleaned, pos = _clean_inline(hm.group(2), idx)
            pos = [(ln, c + offset) for ln, c in pos]
            block_text = [(cleaned, pos)]
            block_line = idx
            flush()
            block_kind = "prose"
            continue
        bm = BULLET_RE.match(line)
        if bm:
            flush()  # each list item is its own block
            block_kind = "list"
            offset = len(bm.group(1)) + len(bm.group(2)) + 1
            cleaned, pos = _clean_inline(bm.group(3), idx)
            pos = [(ln, c + offset) for ln, c in pos]
            block_text = [(cleaned, pos)]
            block_line = idx
            continue
        # Setext heading underline
        if re.fullmatch(r"\s*(=+|-+)\s*", line) and block_text:
            block_kind = "heading"
            flush()
            block_kind = "prose"
            continue
        cleaned, pos = _clean_inline(line, idx)
        if not block_text:
            block_line = idx
            if block_kind != "list":
                block_kind = "prose"
        block_text.append((cleaned, pos))
    flush()
    return Document(paragraphs=paragraphs, raw=text, path=path)

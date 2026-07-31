"""Per-project configuration.

The framework ships no domain knowledge. Everything project-specific -- the
domain vocabulary that must never be flagged, sentence budgets, house style
choices -- lives in `techlint.yaml` (or `.json`) next to the docs. Porting
techlint to a new project is writing one config file. (Pattern taken from the
narrative-quality-engineering project.)

Example `techlint.yaml`:

    mode: reference            # reference | procedure | narrative
    locale: us

    budgets:
      sentence_words: 30       # MINOR above this
      paragraph_sentences: 6
      em_dash_per_1k: 10

    style:
      contractions: allow      # allow | flag   (Google's guide allows them)
      latin_abbreviations: flag
      serial_semicolons: flag

    # Exemption 2 of the taxonomy, declared up front: words this project uses
    # literally. Never flagged as AI vocabulary.
    domain_vocabulary:
      - harness                # the wiring harness this product ships
      - robust                 # reliability engineering term of art
      - realm                  # Kerberos realm

    disable: [CLARITY-SVDIST]

PyYAML is used when available; otherwise a small subset parser handles the
flat/nested-scalar/list shapes above.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAMES = ["techlint.yaml", "techlint.yml", "techlint.json", ".techlint.yaml"]

# Directories never walked when a path expands to a tree. Without this,
# `techlint .` in any real project reads every README in node_modules.
# Extend per project with `exclude:` in techlint.yaml; these defaults always
# apply on top of whatever you add.
DEFAULT_EXCLUDES = [
    "node_modules", "vendor", "vendored", "third_party", "thirdparty",
    ".venv", "venv", "env", ".env", "virtualenv",
    "site-packages", "dist-packages", "__pycache__", ".tox", ".nox",
    "build", "dist", "target", "out", "_build", ".next", ".nuxt",
    ".git", ".hg", ".svn", ".cache", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "htmlcov", "coverage", ".idea", ".vscode",
    "bower_components", "jspm_packages", "Pods", ".terraform",
]

MODE_DEFAULTS = {
    # mode          sentence_words  paragraph_sentences
    "procedure":   (20, 6),    # instructions: one action, short
    "reference":   (30, 6),    # API/reference/explanatory prose
    "narrative":   (40, 10),   # essays, blog posts, release narratives
}


@dataclass
class Config:
    mode: str = "reference"
    locale: str = "us"
    budgets: dict = field(default_factory=dict)
    style: dict = field(default_factory=dict)
    domain_vocabulary: set = field(default_factory=set)
    disable: set = field(default_factory=set)
    exclude: list = field(default_factory=list)
    bands: dict = field(default_factory=dict)
    enable_ai: bool = True
    enable_clarity: bool = True
    enable_docs: bool = True
    enable_stats: bool = True
    pedantic: bool = False
    path: str = ""

    def __post_init__(self):
        sw, ps = MODE_DEFAULTS.get(self.mode, MODE_DEFAULTS["reference"])
        self.budgets.setdefault("sentence_words", sw)
        self.budgets.setdefault("paragraph_sentences", ps)
        self.budgets.setdefault("em_dash_per_1k", 10)
        self.budgets.setdefault("triad_share", 0.35)
        self.budgets.setdefault("opener_share", 0.15)
        self.style.setdefault("contractions", "allow")
        self.style.setdefault("latin_abbreviations", "flag")
        self.style.setdefault("serial_semicolons", "flag")
        self.domain_vocabulary = {w.lower() for w in self.domain_vocabulary}

    # -- budget accessors -------------------------------------------------
    @property
    def sentence_words(self) -> int:
        return int(self.budgets["sentence_words"])

    @property
    def paragraph_sentences(self) -> int:
        return int(self.budgets["paragraph_sentences"])

    def flags(self, key: str) -> bool:
        return self.style.get(key) == "flag"

    def is_domain_word(self, word: str) -> bool:
        return word.lower() in self.domain_vocabulary

    def excluded(self, path) -> bool:
        """True if any path component matches an exclude pattern.

        Patterns are matched against directory and file names, not full paths,
        and support globs: `exclude: ["generated-*", "*.min.md"]`.
        """
        import fnmatch
        from pathlib import Path

        parts = Path(path).parts
        patterns = [*DEFAULT_EXCLUDES, *self.exclude]
        for part in parts:
            if part.startswith(".") and part not in (".", ".."):
                return True
            for pat in patterns:
                if fnmatch.fnmatch(part, pat):
                    return True
        return False

    # -- loading ----------------------------------------------------------
    @classmethod
    def find(cls, start=".", **overrides):
        """Walk up from `start` looking for a config file; else defaults."""
        d = Path(start).resolve()
        for parent in [d, *d.parents]:
            for name in CONFIG_NAMES:
                p = parent / name
                if p.exists():
                    return cls.load(p, **overrides)
        return cls(**overrides)

    @classmethod
    def load(cls, path, **overrides):
        p = Path(path)
        text = p.read_text()
        data = json.loads(text) if p.suffix == ".json" else _parse_yaml(text)
        data = {k: v for k, v in (data or {}).items() if not k.startswith("_")}
        for key in ("disable", "domain_vocabulary"):
            if key in data and data[key] is not None:
                data[key] = set(data[key])
        data.update(overrides)
        data["path"] = str(p)
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"{p}: unknown config keys {sorted(unknown)}")
        return cls(**data)


# -- minimal YAML subset ---------------------------------------------------

def _parse_yaml(text: str):
    """Handles the shapes used by techlint.yaml: nested maps of scalars and
    lists of scalars, two-space indented. Uses PyYAML when it is installed."""
    try:
        import yaml  # noqa: PLC0415
        return yaml.safe_load(text)
    except ImportError:
        return _parse_yaml_subset(text)


def _parse_yaml_subset(text: str):
    """The stdlib fallback, and the path every zero-dependency install takes.

    Kept separate from _parse_yaml so the tests can exercise it directly. Run
    through _parse_yaml instead and a dev machine with PyYAML installed tests
    PyYAML, leaving this parser unverified until CI.
    """
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip() if not _in_quotes(raw, "#") else raw.rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if body.startswith("- "):
            # _Pending is a dict subclass that also collects list items, so it
            # is never a `list` -- test for the capability, not the type.
            if isinstance(parent, (list, _Pending)):
                parent.append(_scalar(body[2:].strip()))
            continue
        if ":" not in body:
            continue
        key, _, val = body.partition(":")
        key, val = key.strip(), val.strip()
        if val == "":
            # Peek is unnecessary: create a dict, swap to list on first "- ".
            child = _Pending(parent, key)
            stack.append((indent, child))
        else:
            parent[key] = _scalar(val)
    return _materialize(root)


class _Pending(dict):
    """A container whose type (map vs list) is decided by its first child."""

    def __init__(self, parent, key):
        super().__init__()
        self._parent, self._key = parent, key
        self._list = []
        parent[key] = self

    def append(self, item):
        self._list.append(item)

    def resolve(self):
        return self._list if self._list else {k: v for k, v in self.items()}


def _materialize(node):
    if isinstance(node, _Pending):
        return _materialize(node.resolve())
    if isinstance(node, dict):
        return {k: _materialize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_materialize(v) for v in node]
    return node


def _in_quotes(line: str, ch: str) -> bool:
    i = line.find(ch)
    return i > 0 and line[:i].count('"') % 2 == 1


def _scalar(v: str):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d*\.\d+", v):
        return float(v)
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    return v

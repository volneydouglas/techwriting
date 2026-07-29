"""AI tic detection.

Three layers, in descending order of confidence:

1. **Artifacts** (BLOCKER) -- text that has no legitimate place in a technical
   document at all: the assistant's chat frame, unfilled placeholders,
   appeals to unnamed studies. Near-zero false-positive rate.
2. **Patterns** (MAJOR/MINOR) -- phrasal and syntactic templates. Includes the
   participial-editorial clause, which stylometric research identifies as one
   of the most consistent structural markers of LLM text.
3. **Vocabulary** (tiered by measured effect size) -- the Kobak et al. excess
   vocabulary, tiered by how far each word's 2024 frequency exceeded its
   pre-LLM trend across 15M abstracts. A word at 28x is a tell; a word at 1.6x
   is a budget item.

Nothing here proves a machine wrote the text. These are smells: signals that a
passage was probably not thought through, which is a defect regardless of
authorship. Every MAJOR gets a context review against the exemption taxonomy
(docs/exemptions.md) before it gets "fixed".
"""

import json
import re
import statistics
from functools import lru_cache
from pathlib import Path

from .finding import Finding, Severity
from .textmodel import scan_text

DATA = Path(__file__).parent / "data"

EMDASH_RE = re.compile(r"—|\s--\s")
TRIAD_RE = re.compile(
    r"\b[\w'-]+(?: [\w'-]+){0,3}, [\w'-]+(?: [\w'-]+){0,3},? (?:and|or) [\w'-]+", re.I)
BOLD_TERM_RE = re.compile(
    r"^\s*(?:[-*+]|\d{1,3}[.)])\s+\*\*[^*\n]+?(?::\*\*|\*\*\s*[:—–-])", re.M)
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F0FF"
    "\U00002600-\U000026FF✅✨❌⭐❗❤]")
# The copula daisy-chain: a term repeats across the copula. Corpus-verified at
# zero occurrences in ~1M words of human prose by the prose-smells project.
COPULA_CHAIN_RE = re.compile(
    r"\b(?:is|was) the (\w{4,}),? and the \1 (?:is|was)\b", re.I)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")

# Exemption 4 (quoted text), automated. Shared with the DOC battery.
_scan_text = scan_text


@lru_cache(maxsize=1)
def _patterns():
    d = json.loads((DATA / "ai_patterns.json").read_text())
    artifacts = [(re.compile(p["pattern"], re.I), p) for p in d["artifacts"]]
    phrases = [(re.compile(p["pattern"], re.I), p) for p in d["phrases"]]
    return artifacts, phrases, d["hedges"], tuple(d["transition_openers"]), d["intensifiers"]


@lru_cache(maxsize=1)
def _vocab():
    d = json.loads((DATA / "ai_excess_vocab.json").read_text())
    words = d["words"]
    rx = re.compile(
        r"\b(" + "|".join(sorted(map(re.escape, words), key=len, reverse=True)) + r")\b",
        re.IGNORECASE)
    return words, rx


# Calibration verdict (2026-07-29): the mild tier (1.6x-2.5x excess) fired on
# RFC 793, published in 1981. A word that appears in a document written four
# decades before GPT existed is not evidence of GPT. Mild-tier words are
# therefore never reported individually -- they only feed the density signal
# below, where a *concentration* of them still means something.
TIER_SEVERITY = {"strong": Severity.MAJOR,
                 "moderate": Severity.MINOR,
                 "mild": None}

# Exemption 3 (literal usage), built in. These excess-vocabulary words have a
# common literal sense in technical writing that is a *noun*, while the LLM
# tell is the *verb*. Calibration caught this on PEP 8 (2001), which says
# "underscores" 19 times meaning the `_` character.
#   underscore -> the character         vs. "underscores the importance of"
#   realm      -> Kerberos/auth realm   vs. "in the realm of"
#   harness    -> wiring / test harness vs. "harness the power of"
HOMOGRAPHS = {"underscore", "underscores", "realm", "realms", "harness",
              "harnesses", "streamline", "streamlines", "pioneers", "stands",
              "holds", "excels", "hinges", "poised", "spanned", "spanning"}
# A determiner, quantifier, or attributive adjective immediately before the
# word means it is a noun. Demonstratives (this/that/these) are deliberately
# EXCLUDED: "This underscores the need" is the verb sense — they are subjects,
# not determiners, when they sit directly before the word.
NOUN_CUE = {
    "a", "an", "the", "no", "any", "each", "every", "some", "all",
    "one", "two", "three", "four", "five", "single", "double", "triple",
    "leading", "trailing", "initial", "final", "first", "second", "last",
    "test", "wiring", "cable", "kerberos", "auth", "authentication",
    "security", "with", "without", "of", "in", "by", "into",
}
PREV_WORD_RE = re.compile(r"([A-Za-z][A-Za-z'’-]*)\W+$")


def _is_noun_use(text: str, start: int) -> bool:
    m = PREV_WORD_RE.search(text[:start])
    return bool(m) and m.group(1).lower() in NOUN_CUE


# -- layer 1: artifacts ----------------------------------------------------

def check_artifacts(doc, config):
    artifacts, _, _, _, _ = _patterns()
    for s in doc.prose_sentences():
        text = _scan_text(s, config)
        for rx, p in artifacts:
            for m in rx.finditer(text):
                line, col = s.pos_at(m.start())
                yield Finding(
                    rule="AI-ARTIFACT", severity=Severity.BLOCKER,
                    message=f"Generated-text artifact: \"{_clip(m.group(0))}\".",
                    line=line, col=col, extract=m.group(0)[:70],
                    suggestion=p["fix"], why=p["why"],
                    meta={"id": p["id"]})


# -- layer 2: phrasal / syntactic patterns ---------------------------------

def check_patterns(doc, config):
    """Scan per sentence, then again per paragraph.

    Several of the strongest tics straddle a sentence boundary by design --
    "The result? Latency halved.", "Not X. Not Y. Just Z.", "This isn't merely
    a cache. It is a coordination layer." Scanning only within sentences makes
    those undetectable, so the paragraph pass runs too and duplicates are
    dropped by source position.
    """
    _, phrases, _, _, _ = _patterns()
    seen = set()

    def emit(rx, p, text, locate):
        for m in rx.finditer(text):
            line, col = locate(m.start())
            key = (p["id"], line, col)
            if key in seen:
                continue
            seen.add(key)
            sev = Severity.MAJOR if p.get("severity") == "major" else Severity.MINOR
            yield Finding(
                rule="AI-PHRASE", severity=sev,
                message=f"Stock construction: \"{_clip(m.group(0))}\".",
                line=line, col=col, extract=m.group(0)[:70],
                suggestion=p["fix"], why=p["why"],
                meta={"id": p["id"]})

    for s in doc.prose_sentences():
        for rx, p in phrases:
            yield from emit(rx, p, _scan_text(s, config), s.pos_at)

    for para in doc.paragraphs:
        if para.kind not in ("prose", "list") or len(para.sentences) < 2:
            continue
        joined, index = _join(para.sentences, config)
        for rx, p in phrases:
            yield from emit(rx, p, joined, index)


def _join(sentences, config):
    """Join a paragraph's sentences and return (text, offset -> (line, col))."""
    parts, spans, cursor = [], [], 0
    for s in sentences:
        chunk = _scan_text(s, config)
        parts.append(chunk)
        spans.append((cursor, cursor + len(chunk), s))
        cursor += len(chunk) + 1
    text = " ".join(parts)

    def locate(offset):
        for start, end, s in spans:
            if start <= offset < end:
                return s.pos_at(offset - start)
        return (sentences[0].line, sentences[0].col)

    return text, locate


def check_copula_chain(doc, config):
    """Zero occurrences in ~1M words of human prose (prose-smells calibration)."""
    for s in doc.prose_sentences():
        for m in COPULA_CHAIN_RE.finditer(_scan_text(s, config)):
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="AI-COPULA", severity=Severity.BLOCKER,
                message=f"Copula daisy-chain: \"{_clip(m.group(0))}\".",
                line=line, col=col, extract=m.group(0)[:70],
                suggestion="rewrite as one statement about the thing",
                why="zero occurrences in ~1M words of human prose")


# -- layer 3: vocabulary ---------------------------------------------------

def check_vocabulary(doc, config):
    words, rx = _vocab()
    for s in doc.prose_sentences():
        text = _scan_text(s, config)
        for m in rx.finditer(text):
            surface = m.group(0)
            key = surface.lower()
            entry = words.get(key)
            if entry is None:
                continue
            if config.is_domain_word(key):
                continue            # exemption 2: declared literal/domain usage
            if surface[0].isupper() and m.start() > 0:
                continue            # exemption 1: proper noun mid-sentence
            if key in HOMOGRAPHS and _is_noun_use(text, m.start()):
                continue            # exemption 3: literal noun, not the verb tell
            sev = TIER_SEVERITY[entry["tier"]]
            if sev is None:
                continue            # mild tier: density signal only
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="AI-VOCAB", severity=sev,
                message=f"\"{surface}\" is {entry['ratio']}x more frequent in "
                        f"post-LLM text than the pre-LLM trend predicts.",
                line=line, col=col, extract=surface,
                suggestion=_vocab_fix(key),
                why=f"excess ratio {entry['ratio']} ({entry['tier']} tier), "
                    "Kobak et al. 2025, 15M PubMed abstracts",
                meta={"ratio": entry["ratio"], "tier": entry["tier"]})


def check_vocab_density(doc, config):
    """Concentration of excess vocabulary, including the mild tier.

    One "notably" proves nothing -- RFC 793 has several. A document where 2% of
    words come from the excess list is a different matter. The threshold is the
    calibration corpus ceiling with headroom: pre-LLM technical canon runs
    2-9 excess words per 1,000 (RFC 793: 5.6/1k over 21k words), so the
    default budget is 18/1k. Tune `budgets.excess_vocab_per_1k` against your
    own corpus before trusting it.
    """
    words, rx = _vocab()
    total = doc.word_count()
    if total < 250:
        return
    budget = float(config.budgets.get("excess_vocab_per_1k", 18))
    hits, first = 0, None
    for s in doc.prose_sentences():
        for m in rx.finditer(_scan_text(s, config)):
            key = m.group(0).lower()
            if key not in words or config.is_domain_word(key):
                continue
            hits += 1
            if first is None:
                first = s.pos_at(m.start())
    rate = hits / total * 1000
    if rate > budget and hits >= 8:
        line, col = first or (1, 1)
        yield Finding(
            rule="AI-VOCAB-DENSITY", severity=Severity.MINOR,
            message=f"{hits} excess-vocabulary words in {total} "
                    f"({rate:.0f}/1k, budget {budget:.0f}; pre-LLM technical "
                    "canon runs 2-9/1k).",
            line=line, col=col,
            suggestion="the individual words may each be defensible; the "
                       "concentration is the signal",
            why="aggregate over the Kobak et al. excess-vocabulary list")


PLAIN = {
    "delve": "examine", "delves": "examines", "delving": "examining",
    "delved": "examined",
    "underscore": "show", "underscores": "shows", "underscoring": "which shows",
    "underscored": "showed",
    "showcase": "show", "showcases": "shows", "showcasing": "showing",
    "showcased": "showed",
    "meticulously": "carefully", "meticulous": "careful",
    "intricate": "complex", "intricacies": "details", "intricately": "closely",
    "realm": "area", "realms": "areas",
    "leverage": "use", "leverages": "uses", "leveraging": "using",
    "harness": "use", "harnesses": "uses", "harnessing": "using",
    "utilize": "use", "utilizes": "uses", "utilizing": "using",
    "facilitate": "help", "facilitates": "helps", "facilitating": "helping",
    "encompass": "include", "encompasses": "includes", "encompassing": "including",
    "elucidate": "explain", "elucidates": "explains",
    "necessitate": "require", "necessitates": "requires", "necessitating": "requiring",
    "commendable": "good", "renowned": "well-known", "formidable": "difficult",
    "groundbreaking": "new", "revolutionize": "change", "transformative": "major",
    "comprehensive": "complete", "multifaceted": "complex", "nuanced": "detailed",
    "pivotal": "key", "crucial": "necessary", "seamless": "uninterrupted",
    "seamlessly": "without extra steps", "robust": "reliable",
    "streamline": "simplify", "streamlines": "simplifies", "streamlining": "simplifying",
    "garnered": "received", "excels": "is good at", "surpassing": "beating",
    "poised": "ready", "swift": "fast", "adept": "skilled",
    "endeavors": "efforts", "advancements": "advances", "escalating": "growing",
    "grappling": "struggling", "unveil": "release", "unveiled": "released",
    "unveils": "releases", "expedite": "speed up", "expediting": "speeding up",
    "bolster": "strengthen", "bolstering": "strengthening",
    "emphasize": "stress", "emphasizing": "stressing", "notable": "significant",
    "heightened": "increased", "pioneers": "leads", "uncharted": "unexplored",
}


def _vocab_fix(word: str) -> str:
    plain = PLAIN.get(word)
    return f"plainer: \"{plain}\"" if plain else "use the plainest accurate word"


# -- structural / statistical ----------------------------------------------

def check_em_dashes(doc, config):
    total = doc.word_count()
    if total < 120:
        return
    hits = [s.pos_at(m.start())
            for s in doc.prose_sentences() for m in EMDASH_RE.finditer(s.text)]
    budget = config.budgets["em_dash_per_1k"]
    rate = len(hits) / total * 1000
    if rate > budget and len(hits) >= 3:
        line, col = hits[0]
        yield Finding(
            rule="AI-DASH", severity=Severity.MINOR,
            message=f"{len(hits)} em-dashes in {total} words "
                    f"({rate:.0f}/1k, budget {budget}).",
            line=line, col=col,
            suggestion="replace most with periods, commas, or parentheses",
            why="sustained em-dash interruption is a current-generation LLM rhythm")


def check_triads(doc, config):
    sents = [s for s in doc.prose_sentences() if len(s.words) >= 6]
    if len(sents) < 6:
        return
    hits = [s for s in sents if TRIAD_RE.search(s.text)]
    share = len(hits) / len(sents)
    if share >= config.budgets["triad_share"] and len(hits) >= 4:
        yield Finding(
            rule="AI-TRIAD", severity=Severity.INFO,
            message=f"{len(hits)} of {len(sents)} sentences carry a three-item "
                    f"list ({share:.0%}).",
            line=hits[0].line, col=hits[0].col,
            suggestion="vary list length; cut items that add no information",
            why="the rule of three is emitted reflexively; items 2-3 are often padding")


def check_transition_openers(doc, config):
    _, _, _, openers, _ = _patterns()
    hits = []
    for s in doc.prose_sentences():
        low = s.text.lower()
        for op in openers:
            if low.startswith(op + ",") or low.startswith(op + " "):
                hits.append((s, op))
                break
    sents = doc.prose_sentences()
    if len(hits) >= 3 and sents and len(hits) / len(sents) > config.budgets["opener_share"]:
        used = ", ".join(sorted({op for _, op in hits}))
        s = hits[0][0]
        yield Finding(
            rule="AI-OPENER", severity=Severity.MINOR,
            message=f"{len(hits)} sentences open with a stock transition ({used}).",
            line=s.line, col=s.col,
            suggestion="connect ideas with content, not connectors",
            why="rigid transition scaffolding is an identified LLM discourse marker")


def check_hedge_stacks(doc, config):
    """Two or more hedges in one clause: the confidence goes to zero."""
    _, _, hedges, _, _ = _patterns()
    rx = re.compile(r"\b(" + "|".join(map(re.escape, hedges)) + r")\b", re.I)
    for s in doc.prose_sentences():
        found = [(m.group(0), m.start()) for m in rx.finditer(s.text)]
        if len(found) >= 3:
            line, col = s.pos_at(found[0][1])
            yield Finding(
                rule="AI-HEDGE", severity=Severity.MINOR,
                message=f"{len(found)} hedges in one sentence "
                        f"({', '.join(w for w, _ in found)}).",
                line=line, col=col, extract=_clip(s.text),
                suggestion="commit to the claim, or state the condition that decides it",
                why="hedge stacking is an identified marker of LLM text")


def check_intensifiers(doc, config):
    _, _, _, _, intens = _patterns()
    rx = re.compile(r"\b(" + "|".join(map(re.escape, intens)) + r")\b", re.I)
    total = doc.word_count()
    if total < 120:
        return
    hits = [(s, m) for s in doc.prose_sentences() for m in rx.finditer(s.text)]
    rate = len(hits) / total * 1000
    if rate > 8 and len(hits) >= 4:
        s, m = hits[0]
        line, col = s.pos_at(m.start())
        yield Finding(
            rule="AI-INTENSIFY", severity=Severity.INFO,
            message=f"{len(hits)} intensifiers in {total} words ({rate:.0f}/1k).",
            line=line, col=col,
            suggestion="most are deletable; the ones that survive should carry a number",
            why="intensifier density substitutes emphasis for evidence")


def check_bold_term_lists(doc, config):
    matches = list(BOLD_TERM_RE.finditer(doc.raw))
    if len(matches) >= 4:
        line = doc.raw[: matches[0].start()].count("\n") + 1
        yield Finding(
            rule="AI-BOLDLIST", severity=Severity.INFO,
            message=f"{len(matches)} bullets in the '**Term:** explanation' shape.",
            line=line, col=1,
            suggestion="merge into prose or a table, or expand the items that matter",
            why="the listicle skeleton performs organization while each item stays too thin to use")


def check_uniform_sentences(doc, config):
    lengths = [len(s.words) for s in doc.prose_sentences() if len(s.words) >= 3]
    if len(lengths) < 12:
        return
    mean = statistics.mean(lengths)
    stdev = statistics.stdev(lengths)
    if mean > 8 and stdev / mean < 0.32:
        s = doc.prose_sentences()[0]
        yield Finding(
            rule="AI-UNIFORM", severity=Severity.INFO,
            message=f"Sentence length is unusually uniform (mean {mean:.0f} words, "
                    f"sd {stdev:.1f}, cv {stdev/mean:.2f}).",
            line=s.line, col=s.col,
            suggestion="mix short sentences with long ones",
            why="low burstiness; human technical prose varies more")


def check_emoji(doc, config):
    for s in doc.sentences:
        m = EMOJI_RE.search(s.text)
        if m:
            line, col = s.pos_at(m.start())
            yield Finding(
                rule="AI-EMOJI", severity=Severity.INFO,
                message="Decorative emoji in technical prose.",
                line=line, col=col, extract=m.group(0),
                suggestion="remove unless the house style calls for it",
                why="generated-README convention")
            return


def _clip(t: str, n: int = 60) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1] + "…"


AI_CHECKS = [
    check_artifacts,
    check_copula_chain,
    check_patterns,
    check_vocabulary,
    check_vocab_density,
    check_em_dashes,
    check_triads,
    check_transition_openers,
    check_hedge_stacks,
    check_intensifiers,
    check_bold_term_lists,
    check_uniform_sentences,
    check_emoji,
]

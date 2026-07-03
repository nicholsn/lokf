"""Propose typed relations from the markdown links in concept bodies.

Concept prose often links to other concepts without asserting the
relationship in frontmatter. This module extracts those links
(:func:`extract_links`), classifies each one against a cue-phrase table
(:func:`propose`), and can write accepted proposals back into the source
files' frontmatter without disturbing formatting (:func:`apply`).
"""
from __future__ import annotations

import io
import pathlib
import posixpath
import re
from dataclasses import dataclass

from lokf.model import Bundle, Concept
from lokf.schema import Relation, Vocabulary, vocabulary

# Markdown inline link [text](target); the lookbehind skips images. The
# target is either angle-bracketed (group 2, may contain spaces) or bare
# (group 3); an optional quoted title after the target is matched but
# excluded — use _link_target() to read the target.
_LINK_RE = re.compile(
    r"(?<!!)\[([^\]]+)\]"  # [text]
    r"\(\s*"
    r"(?:<([^<>\n]*)>|([^)\s]+))"  # <target> | target
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?"  # optional "Title" / 'Title'
    r"\s*\)"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# Cue-phrase heuristics, in match-priority order: (regex, relation name,
# base confidence). The first row whose regex matches the link's sentence
# (and whose relation's domains admit the source concept's type) wins;
# adjacency of the cue to the link text adds _ADJACENCY_BOOST.
CUE_TABLE: tuple[tuple[re.Pattern, str, float], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), name, confidence)
    for pattern, name, confidence in (
        (r"\bsame as\b|\balias(?:es)?\b", "sameAs", 0.8),
        (r"\bderived\b|\bcomputed\b|\bbuilt from\b", "derivedFrom", 0.75),
        (r"\bpart of\b|\bwithin\b", "isPartOf", 0.75),
        (r"\bcontains?\b|\bincludes?\b|\bincluding\b", "hasPart", 0.7),
        (r"\bdepends?\b|\brequires?\b|\bneeds?\b", "dependsOn", 0.7),
        (r"\bdefined by\b|\bdefinitions?\b", "definedBy", 0.7),
        (r"\bmeasures?\b|\bcounts?\b", "measures", 0.7),
        (r"\bjoins? with\b|\bjoined (?:on|with)\b", "joinsWith", 0.7),
        (
            r"\battributed to\b|\bauthored by\b|\bwritten by\b|\bmaintained by\b",
            "wasAttributedTo",
            0.7,
        ),
        (r"\babout\b|\bcovers?\b|\bdescribes?\b", "about", 0.6),
        (r"\bsee\b|\brefer(?:s|ence)?\b|\bused by\b", "references", 0.55),
        (r"\bsource\b|\bfrom\b", "source", 0.5),
    )
)
_FALLBACK = ("relatedTo", 0.25)
# RelationType names deliberately absent from CUE_TABLE: relatedTo is the
# _FALLBACK when no cue matches, so a cue row for it would be redundant.
UNCUED: frozenset[str] = frozenset({"relatedTo"})
_ADJACENCY_BOOST = 0.15
_ADJACENCY_GAP = 24  # max chars between cue and link text to count as adjacent
_CONFIDENCE_CAP = 0.95


@dataclass
class Link:
    """One markdown prose link, resolved (where possible) to a bundle concept."""

    text: str
    target_raw: str
    target: Concept | None
    sentence: str


@dataclass
class Proposal:
    """A proposed relation from ``source`` to ``link.target``."""

    source: Concept
    link: Link
    relation: Relation
    confidence: float
    rationale: str
    target_iri: str  # resolved at propose() time; apply() writes exactly this


def _link_target(m: re.Match) -> str:
    """The target of a :data:`_LINK_RE` match (angle-bracketed or bare)."""
    target = m.group(2)
    return m.group(3) if target is None else target


def _mask_code(text: str) -> str:
    """Blank out fenced code blocks and inline code spans, preserving offsets."""
    out, fence = [], None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker = stripped[:3]
        if fence is None and marker in ("```", "~~~"):
            fence = marker
        elif fence is not None:
            if stripped.startswith(fence):
                fence = None
            out.append(_blank(line))
            continue
        out.append(_blank(line) if fence is not None else line)
    masked = "".join(out)
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), masked)


def _blank(line: str) -> str:
    content = line.rstrip("\n")
    return " " * len(content) + line[len(content):]


def _sentence_at(text: str, pos: int) -> str:
    """The prose sentence (link markup flattened) around offset ``pos``."""
    prev_break = text.rfind("\n\n", 0, pos)
    para_start = prev_break + 2 if prev_break != -1 else 0
    para_end = text.find("\n\n", pos)
    para_end = len(text) if para_end == -1 else para_end
    start, end = para_start, para_end
    for m in _SENTENCE_SPLIT_RE.finditer(text, para_start, para_end):
        if m.end() <= pos:
            start = m.end()
        elif m.start() >= pos:
            end = m.start()
            break
    sentence = _LINK_RE.sub(lambda m: m.group(1), text[start:end])
    return " ".join(sentence.split())


def _resolve_target(concept: Concept, bundle: Bundle, raw: str) -> Concept | None:
    """Resolve a link target to a bundle concept, or None."""
    target = raw.split("#", 1)[0]
    if not target:
        return None
    found = bundle.get(target)
    if found is not None or target.startswith(("http://", "https://", "urn:", "/")):
        return found
    joined = posixpath.normpath(
        posixpath.join(posixpath.dirname(concept.concept_id), target)
    )
    return bundle.get(joined) if not joined.startswith("..") else None


def extract_links(concept: Concept, bundle: Bundle) -> list[Link]:
    """Markdown prose links in ``concept.body`` (code blocks/spans excluded)."""
    masked = _mask_code(concept.body)
    return [
        Link(
            text=m.group(1),
            target_raw=_link_target(m),
            target=_resolve_target(concept, bundle, _link_target(m)),
            sentence=_sentence_at(masked, m.start()),
        )
        for m in _LINK_RE.finditer(masked)
    ]


def _asserted_iris(concept: Concept, bundle: Bundle, vocab: Vocabulary) -> set[str]:
    """Target IRIs already asserted in frontmatter (slots + reified relations)."""
    iris = set()
    for name in vocab.relation_slots:
        values = concept.data.get(name) or []
        if isinstance(values, str):
            values = [values]
        iris.update(bundle.resolve(v) for v in values if isinstance(v, str))
    for rel in concept.data.get("relations") or []:
        if isinstance(rel, dict) and isinstance(rel.get("target"), str):
            iris.add(bundle.resolve(rel["target"]))
    return iris


def _domain_ok(relation: Relation, source: Concept) -> bool:
    return (
        not relation.domains
        or "Concept" in relation.domains
        or source.type in relation.domains
    )


def _adjacent(sentence: str, link_text: str, cue: re.Match) -> bool:
    """Whether the cue match sits next to (or inside) the link text."""
    text = " ".join(link_text.split())
    link_start = sentence.find(text)
    if link_start == -1:
        return False
    link_end = link_start + len(text)
    return (
        cue.start() < link_end + _ADJACENCY_GAP
        and cue.end() > link_start - _ADJACENCY_GAP
    )


def _classify(
    source: Concept, link: Link, vocab: Vocabulary, target_iri: str
) -> Proposal | None:
    """Pick a relation for one link from the cue table (fallback: relatedTo)."""
    for pattern, name, confidence in CUE_TABLE:
        relation = vocab.relation_slots.get(name) or vocab.relation_types.get(name)
        if relation is None or not _domain_ok(relation, source):
            continue
        match = pattern.search(link.sentence)
        if match is None:
            continue
        boosted = _adjacent(link.sentence, link.text, match)
        return Proposal(
            source=source,
            link=link,
            relation=relation,
            confidence=min(
                confidence + (_ADJACENCY_BOOST if boosted else 0), _CONFIDENCE_CAP
            ),
            rationale=f'cue "{match.group(0).lower()}" '
            + ("adjacent to link" if boosted else "in sentence"),
            target_iri=target_iri,
        )
    name, confidence = _FALLBACK
    relation = vocab.relation_slots.get(name) or vocab.relation_types.get(name)
    if relation is None or not _domain_ok(relation, source):
        return None
    return Proposal(
        source=source,
        link=link,
        relation=relation,
        confidence=confidence,
        rationale="no cue phrase matched",
        target_iri=target_iri,
    )


def propose(
    bundle: Bundle,
    vocab: Vocabulary | None = None,
    concept: Concept | None = None,
) -> list[Proposal]:
    """Propose relations for prose links not already asserted in frontmatter."""
    vocab = vocab if vocab is not None else vocabulary()
    proposals = []
    for source in [concept] if concept is not None else bundle.concepts:
        asserted = _asserted_iris(source, bundle, vocab)
        for link in extract_links(source, bundle):
            if link.target is None:
                continue
            target_iri = bundle.iri(link.target)
            if target_iri in asserted:
                continue
            proposal = _classify(source, link, vocab, target_iri)
            if proposal is not None:
                proposals.append(proposal)
    return proposals


def _rt_yaml():
    from ruamel.yaml import YAML

    y = YAML()
    y.preserve_quotes = True
    y.width = 100000
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def apply(proposals: list[Proposal], min_confidence: float = 0.0) -> list[Proposal]:
    """Write accepted proposals into source frontmatter; return those written.

    Slot relations append the target IRI under the slot key; non-slot
    relations append ``{predicate, target}`` to ``relations``. Files are
    edited with round-trip YAML so comments, key order, and quoting survive;
    duplicates are never written, and everything outside the frontmatter
    block (any preamble before the first ``---`` and the whole body after
    the second) is preserved byte-for-byte.
    """
    from ruamel.yaml.comments import CommentedMap

    by_path: dict[pathlib.Path, list[Proposal]] = {}
    for p in proposals:
        if p.confidence >= min_confidence:
            by_path.setdefault(p.source.path, []).append(p)
    yaml_rt = _rt_yaml()
    applied = []
    for path, batch in by_path.items():
        raw = path.read_text(encoding="utf-8")
        prefix, _, rest = raw.partition("---")
        front, _, remainder = rest.partition("---")
        fm = yaml_rt.load(front)
        if fm is None:  # empty frontmatter block
            fm = CommentedMap()
        changed = False
        for p in batch:
            iri = p.target_iri
            if p.relation.is_slot:
                values = fm.setdefault(p.relation.name, [])
                if not isinstance(values, list):
                    values = fm[p.relation.name] = [values]
                if iri in values:
                    continue
                values.append(iri)
            else:
                entry = {"predicate": p.relation.name, "target": iri}
                relations = fm.setdefault("relations", [])
                if any(
                    r.get("predicate") == entry["predicate"]
                    and r.get("target") == entry["target"]
                    for r in relations
                    if isinstance(r, dict)
                ):
                    continue
                relations.append(entry)
            applied.append(p)
            changed = True
        if changed:
            buf = io.StringIO()
            yaml_rt.dump(fm, buf)
            path.write_text(
                prefix + "---\n" + buf.getvalue() + "---" + remainder,
                encoding="utf-8",
            )
    return applied

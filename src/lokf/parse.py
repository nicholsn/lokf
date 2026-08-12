"""Parse OKF/LOKF concept markdown into JSON-LD-ready dictionaries.

These helpers are the seed of the LOKF toolkit's parser: ``parse_concept``
splits a concept file into frontmatter + body, and ``isoify`` normalizes
YAML-parsed dates to the ISO-8601 ``Z`` form used by the committed RDF
projections.
"""
from __future__ import annotations

import datetime as dt

#: OKF type spellings normalized to their LOKF class names. OKF v0.2 writes
#: ``type: Attested Computation`` (§10); LOKF classes are single-word (the
#: GlossaryTerm precedent), and a spaced @type would not expand to a valid
#: vocab IRI. Applied in :func:`parse_concept`, so every consumer sees the
#: canonical form while authors may use either spelling.
OKF_TYPE_ALIASES = {
    "Attested Computation": "AttestedComputation",
    "Glossary Term": "GlossaryTerm",
}


def isoify(o):
    """Recursively convert ``datetime``/``date`` values to ISO-8601 strings.

    ``+00:00`` offsets are normalized to ``Z`` so JSON/RDF output matches the
    committed ``examples/*.nt`` projections byte-for-byte.
    """
    if isinstance(o, dict):
        return {k: isoify(v) for k, v in o.items()}
    if isinstance(o, list):
        return [isoify(v) for v in o]
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat().replace("+00:00", "Z")
    return o


def parse_concept(path: str) -> dict:
    """Read one concept markdown file into a dict of frontmatter + ``body``.

    Raises ``ValueError`` with a clear message if the file has no ``---``
    delimited YAML frontmatter (e.g. a plain markdown or reserved file).
    """
    import yaml

    raw = open(path, encoding="utf-8").read()
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path}: no YAML frontmatter (expected a '---' delimited block)")
    _, front, body = parts
    d = yaml.safe_load(front) or {}
    d["body"] = body.strip()
    if d.get("type") in OKF_TYPE_ALIASES:
        d["type"] = OKF_TYPE_ALIASES[d["type"]]
    # OKF v0.2 §5.2: a bare `verified: { by, at }` mapping MUST be read as a
    # one-element list. Normalized here so validation, RDF projection, and
    # trust derivation all see the canonical list form.
    if isinstance(d.get("verified"), dict):
        d["verified"] = [d["verified"]]
    return isoify(d)

"""Producer-side consistency of the event families, run by ``lokf validate``.

The schema checks each event on its own. These checks read two events of one
concept together, which JSON Schema cannot: a ``revised`` that precedes
``generated`` is a contradiction, since an edit cannot come before production.
Consumers stay permissive (:mod:`lokf.trust` reads the later of the two);
the producer-side verdict is strict.
"""
from __future__ import annotations

from lokf.trust import _as_datetime


def event_findings(bundle):
    """Yield (severity, message) for each contradiction between a concept's events."""
    for concept in bundle.concepts:
        data = concept.data
        generated, revised = data.get("generated"), data.get("revised")
        if not (isinstance(generated, dict) and isinstance(revised, dict)):
            continue
        g, r = _as_datetime(generated.get("at")), _as_datetime(revised.get("at"))
        if g is not None and r is not None and r < g:
            yield "ERROR", (
                f"{bundle.iri(concept)}: `revised.at` ({revised.get('at')}) precedes "
                f"`generated.at` ({generated.get('at')}); an edit cannot come before production"
            )

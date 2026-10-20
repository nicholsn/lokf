"""SHACL for LOKF's authoring RDF projection, with local reference boundaries."""
from __future__ import annotations

from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, SH, XSD


def _list(graph, predicate, subject, values):
    graph.remove((subject, predicate, None))
    head = BNode()
    Collection(graph, head, values)
    graph.add((subject, predicate, head))


def build_shapes(schema: str | Path) -> Graph:
    """Adapt LinkML shapes to the same flat authoring context as conversion.

    Distinct native shape names preserve classes sharing a class_uri (Source
    and Citation). JSON Schema enforces closed frontmatter; RDF shapes are
    open so inherited shapes do not reject a subclass's extra properties.
    """
    from linkml.generators.shaclgen import ShaclGenerator
    from linkml_runtime.utils.schemaview import SchemaView
    from lokf.schema import _PARAMETER_KINDS, schema_context

    view = SchemaView(str(schema))
    context = schema_context(schema)
    graph = Graph().parse(data=ShaclGenerator(
        str(schema), use_class_uri_names=False, suffix='Shape', closed=False,
    ).serialize(), format='turtle')

    def class_uri(name):
        return URIRef(view.get_uri(view.get_class(name), expand=True))

    def shape_uri(name):
        return URIRef(view.get_uri(view.get_class(name), expand=True, native=True) + 'Shape')

    # Two frontmatter slots can intentionally project to the same predicate
    # (e.g. Person.name and Concept.title). RDF loses that distinction, so
    # per-slot maximum counts are enforced by JSON Schema, not on aliases.
    aliases = {}
    for name in view.all_classes():
        for slot in view.class_induced_slots(name):
            aliases.setdefault(URIRef(view.get_uri(slot, expand=True)), set()).add(slot.name)

    for name, cls in view.all_classes().items():
        shape = shape_uri(name)
        ancestors = view.class_ancestors(name, mixins=True)
        # Helpers are validated via their containing property, not globally:
        # Source and Citation share an RDF class but have different contracts.
        if 'Concept' not in ancestors:
            graph.remove((shape, SH.targetClass, None))
        else:
            graph.add((shape, SH.nodeKind, SH.IRI))
        for parent in ([cls.is_a] if cls.is_a else []) + list(cls.mixins or []):
            graph.add((class_uri(name), RDFS.subClassOf, class_uri(parent)))
        slots = {URIRef(view.get_uri(s, expand=True)): s for s in view.class_induced_slots(name)}
        for prop in list(graph.objects(shape, SH.property)):
            path = graph.value(prop, SH.path)
            if len(aliases.get(path, ())) > 1:
                graph.remove((prop, SH.maxCount, None))
            slot = slots.get(path)
            if slot is None:
                continue
            term = context.get(slot.name, {})
            if term == '@type':
                graph.set((prop, SH.path, RDF.type))
                for predicate in (SH.datatype, SH.nodeKind, SH.maxCount):
                    graph.remove((prop, predicate, None))
                graph.add((prop, SH.nodeKind, SH.IRI))
            if slot.range in view.all_classes():
                if not (slot.inlined or slot.inlined_as_list):
                    graph.remove((prop, SH.node, None))
                    graph.set((prop, SH['class'], class_uri(slot.range)))
                # OKF author strings are deliberately uncoerced by the context.
                if slot.name == 'author' and isinstance(term, dict) and '@type' not in term:
                    for predicate in (SH.node, SH['class'], SH.nodeKind):
                        graph.remove((prop, predicate, None))
                    text, agent = BNode(), BNode()
                    graph.add((text, SH.datatype, XSD.string))
                    graph.add((agent, SH.node, shape_uri(slot.range)))
                    graph.add((agent, SH.nodeKind, SH.BlankNodeOrIRI))
                    _list(graph, SH['or'], prop, [text, agent])
            elif slot.range in view.all_enums():
                enum = view.get_enum(slot.range)
                values = []
                for key, value in enum.permissible_values.items():
                    if term == '@type' or (isinstance(term, dict) and term.get('@type') in ('@id', '@vocab')):
                        iri = (view.expand_curie(value.meaning) if value.meaning
                               else context.get('@vocab', 'https://w3id.org/lokf/') + key)
                        values.append(URIRef(iri))
                    else:
                        values.append(Literal(key))
                _list(graph, SH['in'], prop, values)
            # The flat context applies resource's anyURI coercion even where
            # Source widens its authoring range to admit scope descriptions.
            if isinstance(term, dict) and term.get('@type', '').startswith('xsd:'):
                graph.set((prop, SH.datatype, URIRef(str(XSD) + term['@type'][4:])))
                graph.set((prop, SH.nodeKind, SH.Literal))
    for kind in _PARAMETER_KINDS.values():
        graph.add((URIRef('https://w3id.org/lokf/' + kind), RDFS.subClassOf, class_uri('Parameter')))
    # Drop detached list nodes left by enum replacement to keep artifacts small.
    reachable = {subject for subject in graph.subjects() if isinstance(subject, URIRef)}
    pending = list(reachable)
    while pending:
        for value in graph.objects(pending.pop(), None):
            if isinstance(value, BNode) and value not in reachable:
                reachable.add(value)
                pending.append(value)
    for subject in set(graph.subjects()) - reachable:
        graph.remove((subject, None, None))
    return graph


def validate_graph(data: Graph, shapes: Graph, base_iri: str, concept_iris=()):
    """Check the actual graph without inferring or repairing its value types.

    External referenced IRIs are not dereferenced or required to carry local
    class declarations. Explicit concept IDs remain local even outside base.
    """
    from pyshacl import validate

    shapes = Graph() + shapes  # Per-bundle exceptions must not mutate cached artifacts.
    local = set(map(str, concept_iris))
    if local:
        known_concepts = BNode()
        shapes.add((known_concepts, SH['class'], URIRef('https://w3id.org/lokf/Concept')))
        for iri in local:
            shapes.add((known_concepts, SH.targetNode, URIRef(iri)))
    for prop, _, expected in list(shapes.triples((None, SH['class'], None))):
        path = shapes.value(prop, SH.path)
        if not isinstance(path, URIRef):
            continue
        external = sorted({value for value in data.objects(None, path)
                           if isinstance(value, URIRef) and str(value) not in local
                           and base_iri and not str(value).startswith(base_iri)}, key=str)
        if external:
            shapes.remove((prop, SH['class'], expected))
            typed, exempt = BNode(), BNode()
            shapes.add((typed, SH['class'], expected))
            _list(shapes, SH['in'], exempt, external)
            _list(shapes, SH['or'], prop, [typed, exempt])
    hierarchy = Graph()
    for triple in shapes.triples((None, RDFS.subClassOf, None)):
        hierarchy.add(triple)
    return validate(data, shacl_graph=shapes, ont_graph=hierarchy, inference='none',
                    advanced=False, inplace=False, do_owl_imports=False)

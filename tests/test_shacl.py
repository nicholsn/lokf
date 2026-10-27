"""Validate the real projection, and reject deliberately corrupted RDF."""
from pathlib import Path

import pytest
import yaml
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD
from typer.testing import CliRunner

from lokf.cli import app
from lokf.model import load_bundle
from lokf.shacl import build_shapes, validate_graph

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://example.org/kb/'
LOKF = 'https://w3id.org/lokf/'
SCHEMA = 'http://schema.org/'


@pytest.fixture(scope='module')
def shapes():
    return Graph().parse(ROOT / 'lokf.shacl.ttl')


def make_bundle(tmp_path, **docs):
    (tmp_path / 'index.md').write_text('---\nbase_iri: ' + BASE + '\ntitle: KB\n---\n')
    for name, data in docs.items():
        (tmp_path / (name + '.md')).write_text('---\n' + yaml.safe_dump(data) + '---\nBody\n')
    return load_bundle(tmp_path)


def test_reference_bundle_passes_shacl_cli():
    result = CliRunner().invoke(app, ['validate', str(ROOT / 'examples/acme-knowledge'), '--shacl'])
    assert result.exit_code == 0, result.output
    assert 'RDF conforms' in result.output


def test_people_organizations_external_targets_and_helpers(tmp_path, shapes):
    b = make_bundle(tmp_path,
        service={'type': 'Service', 'title': 'Service', 'dependsOn': ['person', 'org'],
                 'source': ['https://external.example/source'], 'status': 'stable', 'genre': 'reference',
                 'generated': {'by': 'process:x', 'at': '2026-01-01T00:00:00Z'},
                 'verified': [{'by': 'human:x'}],
                 'sources': [{'resource': 'all queries in X', 'author': 'team:x'}],
                 'citations': [{'title': 'A citation', 'url': 'https://external.example/citation'}],
                 'relations': [{'predicate': 'references', 'target': 'person'}]},
        person={'type': 'Person', 'title': 'Person', 'name': 'Pat'},
        org={'type': 'Organization', 'title': 'Org', 'name': 'Example'},
    )
    graph = b.graph()
    before = set(graph)
    conforms, _, report = validate_graph(graph, shapes, b.base_iri, b.by_iri())
    assert conforms, report
    assert set(graph) == before


@pytest.mark.parametrize('bad_target', ['wrong_class', 'literal', 'missing', 'explicit_wrong_class'])
def test_relation_range_and_kind_are_enforced(tmp_path, shapes, bad_target):
    b = make_bundle(tmp_path, service={'type': 'Service', 'title': 'Service'})
    graph = b.graph()
    target = URIRef(BASE + 'bad')
    local = list(b.by_iri())
    if bad_target == 'literal':
        target = Literal('not-an-iri')
    elif bad_target == 'explicit_wrong_class':
        target = URIRef('https://other.example/explicit-local')
        local.append(str(target))
    if bad_target in ('wrong_class', 'explicit_wrong_class'):
        graph.add((target, RDF.type, URIRef(SCHEMA + 'PropertyValue')))
    graph.add((URIRef(BASE + 'service'), URIRef('http://purl.org/dc/terms/requires'), target))
    conforms, _, _ = validate_graph(graph, shapes, BASE, local)
    assert not conforms


def test_nested_value_validation_is_not_skipped(tmp_path, shapes):
    b = make_bundle(tmp_path, service={'type': 'Service', 'title': 'Service', 'generated': {'by': 'process:x'}})
    graph = b.graph()
    by = URIRef('http://www.w3.org/ns/prov#wasAssociatedWith')
    event = next(graph.subjects(by, None))
    graph.set((event, by, Literal(42, datatype=XSD.integer)))
    conforms, _, report = validate_graph(graph, shapes, BASE, b.by_iri())
    assert not conforms and 'wasAssociatedWith' in report


def test_domain_shapes_follow_slot_ranges(tmp_path):
    schema = ROOT / 'tests/fixtures/domain-schema/reranges-a-slot.yaml'
    b = make_bundle(tmp_path, rule={'type': 'Regulation', 'title': 'Rule', 'governedBy': ['person']},
                    person={'type': 'Person', 'title': 'Person', 'name': 'Pat'})
    graph = b.graph(schema=schema)
    shapes = build_shapes(schema)
    conforms, _, report = validate_graph(graph, shapes, BASE, b.by_iri())
    assert conforms, report
    person = URIRef(BASE + 'person')
    graph.remove((person, RDF.type, None))
    graph.add((person, RDF.type, URIRef(SCHEMA + 'PropertyValue')))
    assert not validate_graph(graph, shapes, BASE, b.by_iri())[0]


def test_missing_optional_extra_has_install_hint(tmp_path, monkeypatch):
    import sys
    make_bundle(tmp_path)
    monkeypatch.setitem(sys.modules, 'pyshacl', None)
    result = CliRunner().invoke(app, ['validate', str(tmp_path), '--shacl'])
    assert result.exit_code == 1
    assert "pip install 'lokf[shacl]'" in result.output


def test_cli_domain_schema_is_used_for_projection_and_shapes():
    result = CliRunner().invoke(app, ['validate', str(ROOT / 'examples/acme-knowledge'),
        '--shacl', '--schema', str(ROOT / 'tests/fixtures/domain-schema/imports-only.yaml')])
    assert result.exit_code == 0, result.output


def test_known_concept_cannot_silently_lose_its_type(tmp_path, shapes):
    b = make_bundle(tmp_path, service={'type': 'Service', 'title': 'Service'})
    graph = b.graph()
    graph.remove((URIRef(BASE + 'service'), RDF.type, None))
    assert not validate_graph(graph, shapes, BASE, b.by_iri())[0]


def test_distribution_checksum_projection_validates_and_rejects_bad_fields(tmp_path, shapes):
    spdx = 'http://spdx.org/rdf/terms#'
    bundle = make_bundle(tmp_path, release={
        'type': 'Dataset', 'title': 'Release', 'distribution': [{
            'access_url': 'https://example.org/release.zip', 'byte_size': 42,
            'checksum': {'algorithm': 'sha256', 'checksum_value': 'e' * 64}}]})
    graph = bundle.graph()
    assert validate_graph(graph, shapes, BASE, bundle.by_iri())[0]
    checksum = next(graph.subjects(RDF.type, URIRef(spdx + 'Checksum')))
    graph.remove((checksum, URIRef(spdx + 'algorithm'), None))
    assert not validate_graph(graph, shapes, BASE, bundle.by_iri())[0]

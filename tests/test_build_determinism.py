"""`lokf-build` must be byte-reproducible.

Re-running the LinkML generators over an unmodified `lokf.yaml` used to rewrite
~2,575 lines across the committed artifacts, from three causes: wall-clock
stamps, an unsorted CREATE INDEX block, and blank-node labels minted from
uuid4. That churn buried every real schema diff and made it impossible for CI
to assert the artifacts matched their source. These cover each cause; the
`generated-fresh` CI job covers the whole build end to end.
"""
import json
import pathlib

import pytest
from rdflib import BNode, Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import SH

from lokf.build import _canonicalize_rdf, _relabel_bnodes, _sort_set_valued_lists, _sort_sql_indexes

ROOT = pathlib.Path(__file__).resolve().parents[1]


# -- CREATE INDEX ordering ---------------------------------------------------
def test_sort_sql_indexes_orders_indexes_and_leaves_tables_alone(tmp_path):
    f = tmp_path / "s.sql"
    f.write_text(
        'CREATE TABLE "B" (x TEXT);\n'
        'CREATE TABLE "A" (y TEXT);\n'
        'CREATE INDEX "ix_z" ON "B" (x);\n'
        'CREATE INDEX "ix_a" ON "A" (y);\n',
        encoding="utf-8",
    )
    _sort_sql_indexes(f)
    lines = f.read_text(encoding="utf-8").splitlines()
    # table order preserved (it is already stable, and FK order can matter)
    assert lines[:2] == ['CREATE TABLE "B" (x TEXT);', 'CREATE TABLE "A" (y TEXT);']
    assert lines[2:] == ['CREATE INDEX "ix_a" ON "A" (y);', 'CREATE INDEX "ix_z" ON "B" (x);']


def test_sort_sql_indexes_is_idempotent(tmp_path):
    f = tmp_path / "s.sql"
    f.write_text('CREATE TABLE "A" (y TEXT);\nCREATE INDEX "ix_b" ON "A" (y);\n', encoding="utf-8")
    _sort_sql_indexes(f)
    once = f.read_text(encoding="utf-8")
    _sort_sql_indexes(f)
    assert f.read_text(encoding="utf-8") == once


# -- blank-node relabelling --------------------------------------------------
def _same_graph_different_bnode_labels():
    """One graph, serialized twice with unrelated blank-node labels."""
    ttl = """
    @prefix ex: <https://ex.org/> .
    ex:S ex:p [ ex:a "1" ; ex:b [ ex:c "2" ] ] .
    ex:T ex:p [ ex:a "3" ] .
    """
    a, b = Graph().parse(data=ttl, format="turtle"), Graph().parse(data=ttl, format="turtle")
    return a, b


def test_relabel_bnodes_is_stable_across_independent_parses():
    a, b = _same_graph_different_bnode_labels()
    assert {str(n) for n in a.all_nodes() if isinstance(n, BNode)} != {
        str(n) for n in b.all_nodes() if isinstance(n, BNode)
    }, "precondition: rdflib minted different labels"
    assert sorted(_relabel_bnodes(a).serialize(format="nt").splitlines()) == sorted(
        _relabel_bnodes(b).serialize(format="nt").splitlines()
    )


def test_relabel_bnodes_preserves_every_triple():
    a, _ = _same_graph_different_bnode_labels()
    assert len(_relabel_bnodes(a)) == len(a)


def test_canonicalize_rdf_is_byte_stable(tmp_path):
    a, b = _same_graph_different_bnode_labels()
    fa, fb = tmp_path / "a.ttl", tmp_path / "b.ttl"
    fa.write_text(a.serialize(format="turtle"), encoding="utf-8")
    fb.write_text(b.serialize(format="turtle"), encoding="utf-8")
    _canonicalize_rdf(fa, "turtle")
    _canonicalize_rdf(fb, "turtle")
    assert fa.read_text(encoding="utf-8") == fb.read_text(encoding="utf-8")


def test_canonicalize_rdf_keeps_a_header_comment(tmp_path):
    a, _ = _same_graph_different_bnode_labels()
    f = tmp_path / "a.ttl"
    f.write_text(a.serialize(format="turtle"), encoding="utf-8")
    _canonicalize_rdf(f, "turtle", header="# provenance\n\n")
    assert f.read_text(encoding="utf-8").startswith("# provenance\n")


def test_canonicalize_nt_sorts_lines(tmp_path):
    f = tmp_path / "a.nt"
    f.write_text(
        '<https://ex.org/b> <https://ex.org/p> "2" .\n'
        '<https://ex.org/a> <https://ex.org/p> "1" .\n',
        encoding="utf-8",
    )
    _canonicalize_rdf(f, "nt")
    assert f.read_text(encoding="utf-8").splitlines() == sorted(
        f.read_text(encoding="utf-8").splitlines()
    )


# -- set-valued rdf:List ordering -------------------------------------------
def test_sort_set_valued_lists_orders_members_without_changing_membership():
    g = Graph()
    head = BNode()
    members = [URIRef("https://ex.org/z"), URIRef("https://ex.org/a"), URIRef("https://ex.org/m")]
    Collection(g, head, members)
    g.add((URIRef("https://ex.org/Shape"), SH.ignoredProperties, head))
    before = {str(x) for x in Collection(g, head)}
    _sort_set_valued_lists(g)
    after = list(Collection(g, head))
    assert [str(x) for x in after] == sorted(str(x) for x in after)
    assert {str(x) for x in after} == before


# -- the committed artifacts -------------------------------------------------
@pytest.mark.parametrize("rel", ["lokf.context.jsonld", "src/lokf/data/lokf.context.jsonld"])
def test_committed_context_carries_no_wall_clock_stamp(rel):
    """A timestamp on a committed artifact is churn; git records the change."""
    comments = json.loads((ROOT / rel).read_text(encoding="utf-8")).get("comments", {})
    assert "generation_date" not in comments
    assert comments.get("source")  # the useful provenance is kept


def test_committed_datamodel_carries_no_wall_clock_stamp():
    text = (ROOT / "src" / "lokf" / "datamodel.py").read_text(encoding="utf-8")
    assert "# Generation date:" not in text
    assert "# Auto generated from lokf.yaml" in text  # provenance kept


def test_committed_sql_indexes_are_sorted():
    idx = [
        line
        for line in (ROOT / "lokf.sql").read_text(encoding="utf-8").splitlines()
        if line.startswith("CREATE INDEX")
    ]
    assert idx and idx == sorted(idx)

"""`lokf validate --check-excerpts`: each sources[].excerpt is in its local resource."""
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from lokf.cli import app
from lokf.excerpts import check_excerpts, find
from lokf.model import load_bundle

CORPUS = yaml.safe_load((Path(__file__).parent / 'fixtures' / 'excerpt-corpus.yaml').read_text(encoding='utf-8'))
runner = CliRunner()


@pytest.mark.parametrize('case', CORPUS['cases'], ids=lambda c: c['id'])
def test_corpus(case):
    """The grammar's cases, as any other checker would run them."""
    problem = find(case['excerpt'], case['text'], markdown=case.get('markdown', True))
    assert (problem is None) == case['found'], problem


def test_corpus_names_each_reason():
    """A miss says why, in words a bundle's author can act on."""
    assert find('...', 'x') == 'is empty'
    assert find('a ... b ... c', 'a b c') == 'joins 3 spans; at most two, around one `...`'
    assert find('nope', 'a b c', where="'doc.md'") == "is not in 'doc.md'"
    assert find('nope ... c', 'a b c') == 'starts with a span that is not in the resource'
    assert find('a ... nope', 'a b c') == 'ends with a span that is not in the resource'
    assert find('c ... a', 'a b c') == 'has two spans that are not in order inside one heading section of the resource'


def bundle_at(root, **fields):
    root.mkdir(exist_ok=True)
    (root / 'index.md').write_text('---\nbase_iri: https://example.org/\ntitle: KB\n---\n')
    (root / 'c.md').write_text('---\n' + yaml.safe_dump({'type': 'Service', 'title': 'C', **fields}) + '---\n')
    return load_bundle(root)


def test_local_resources_are_read_and_remote_ones_counted(tmp_path):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'a.md').write_text('## Limits\n\nThe service keeps **no** copy of the request.\n')
    (tmp_path / 'notes.txt').write_text('plain text, one section')
    b = bundle_at(tmp_path / 'kb', sources=[
        {'resource': 'docs/a.md', 'excerpt': 'keeps **no** copy of the request'},
        {'resource': './notes.txt', 'excerpt': 'Plain text'},
        {'resource': 'https://example.org/page', 'excerpt': 'never fetched'},
        {'resource': 'docs/a.md'},
        {'resource': 'docs/a.md', 'excerpt': 'keeps no copy of the request'}])
    stats = {}
    findings = list(check_excerpts(b, tmp_path, stats))
    assert stats == {'local': 3, 'remote': 1, 'unchecked': 0}
    # Markdown is matched as written: the emphasis markers are part of the passage.
    assert len(findings) == 1 and findings[0][0] == 'ERROR'
    assert "`sources[4].excerpt` ('keeps no copy of the request') is not in 'docs/a.md'" in findings[0][1]


def test_what_holds_no_text_is_an_error(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    (root / 'docs').mkdir()
    (root / 'docs' / 'a.svg').write_text('<svg/>')
    (tmp_path / 'blob.bin').write_bytes(b'\x00\x01binary')
    (tmp_path / 'secret.md').write_text('outside')
    (root / 'link.md').symlink_to(tmp_path / 'secret.md')
    b = bundle_at(root / 'kb', sources=[
        {'resource': 'all queries in project X', 'excerpt': 'a quote'},
        {'resource': 'docs', 'excerpt': 'a quote'},
        {'resource': 'docs/*.svg', 'excerpt': 'a quote'},
        {'resource': '../blob.bin', 'excerpt': 'a quote'},
        {'resource': 'link.md', 'excerpt': 'outside'},
        {'resource': 'missing.md', 'excerpt': 'a quote'}])
    findings = list(check_excerpts(b, root))
    assert [s for s, _ in findings] == ['ERROR'] * 6
    for i, said in enumerate(['scope description', 'directory', 'pattern', 'outside resource root',
                              'outside resource root', 'names no file']):
        assert f'sources[{i}].excerpt' in findings[i][1] and said in findings[i][1], findings[i][1]
    (root / 'blob.bin').write_bytes(b'\x00\x01binary')
    b = bundle_at(root / 'kb', sources=[{'resource': 'blob.bin', 'excerpt': 'a quote'}])
    (severity, message), = check_excerpts(b, root)
    assert severity == 'ERROR' and 'not text' in message


def test_cli_opt_in_root_and_verdict(tmp_path):
    (tmp_path / 'a.md').write_text('# A\n\nthe fox jumps\n')
    kb = bundle_at(tmp_path / 'kb', sources=[
        {'resource': 'a.md', 'excerpt': 'the fox jumps'},
        {'resource': 'https://example.org/page', 'excerpt': 'elsewhere'}]).root
    assert runner.invoke(app, ['validate', str(kb)]).exit_code == 0
    result = runner.invoke(app, ['validate', str(kb), '--check-excerpts'])
    assert result.exit_code == 0, result.output
    assert 'Every local excerpt is in its resource; 1 on remote resources not fetched.' in result.output
    assert runner.invoke(app, ['validate', str(kb), '--check-excerpts', '--root', str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ['validate', str(kb), '--root', str(tmp_path)]).exit_code == 2
    (tmp_path / 'a.md').write_text('# A\n\nthe fox sleeps\n')
    result = runner.invoke(app, ['validate', str(kb), '--check-excerpts'])
    assert result.exit_code == 1
    assert "[ERROR] https://example.org/c: `sources[0].excerpt` ('the fox jumps') is not in 'a.md'" in result.output
    kb = bundle_at(tmp_path / 'kb2', sources=[{'resource': 'https://example.org/page', 'excerpt': 'x'}]).root
    result = runner.invoke(app, ['validate', str(kb), '--check-excerpts'])
    assert result.exit_code == 0 and 'No local excerpt to check; 1 on remote' in result.output
    kb = bundle_at(tmp_path / 'kb3', sources=[{'resource': 'a.md'}]).root
    result = runner.invoke(app, ['validate', str(kb), '--check-excerpts'])
    assert result.exit_code == 0 and 'No local excerpt to check.' in result.output


@pytest.mark.parametrize("inner", ["```", "~~~", "````not-a-close"])
def test_fence_contents_do_not_hide_the_next_section(inner):
    text = f"## A\nfirst point\n````md\n{inner}\nexample\n````\n## B\nsecond point\n"
    assert find("first point ... second point", text) is not None
    # Conversely, a heading inside the outer fence must not split a section.
    text = f"## A\nfirst point\n````md\n{inner}\n## code heading\n````\nsecond point\n"
    assert find("first point ... second point", text) is None


def test_oversized_excerpt_is_reported_unchecked(tmp_path, monkeypatch):
    monkeypatch.setattr("lokf.excerpts.MAX_BYTES", 32)
    (tmp_path / "large.txt").write_text("x" * 33)
    kb = bundle_at(tmp_path / "kb", sources=[
        {"resource": "large.txt", "excerpt": "not actually present"}]).root
    result = runner.invoke(app, ["validate", str(kb), "--check-excerpts"])
    assert result.exit_code == 0, result.output
    assert "1 local excerpts left unchecked" in result.output
    assert "Every local excerpt is in its resource" not in result.output


def cite_at(root, **ids_and_excerpts):
    """A bundle whose concepts each cite a source by `id`, with an excerpt or
    none: ``a=('paper', 'a passage')``."""
    root.mkdir(exist_ok=True)
    (root / 'index.md').write_text('---\nbase_iri: https://example.org/kb/\ntitle: KB\n---\n')
    for name, (ref, excerpt) in ids_and_excerpts.items():
        source = {'id': ref, 'resource': 'https://example.org/paper'}
        if excerpt is not None:
            source['excerpt'] = excerpt
        (root / f'{name}.md').write_text(
            '---\n' + yaml.safe_dump({'type': 'Explanation', 'title': name, 'sources': [source]}) + '---\n')
    return root


def test_a_relative_source_id_is_local_to_its_concept(tmp_path):
    """SPEC §5.4: a relative source `id` is a label local to its concept, as a
    footnote label is local to its page. Two concepts quoting two passages under
    one label get one node each, and still share the material through
    `schema:url`."""
    from rdflib import Literal, URIRef
    from lokf.rdf import graph_of

    kb = cite_at(tmp_path / 'kb', a=('paper', 'the first passage'), b=('paper', 'the second passage'))
    result = runner.invoke(app, ['validate', str(kb), '--shacl'])
    assert result.exit_code == 0, result.output
    assert 'different excerpts' not in result.output
    g = graph_of(kb)
    isBasedOn, excerpt = URIRef('http://schema.org/isBasedOn'), URIRef('https://w3id.org/lokf/excerpt')
    nodes = {str(s): str(o) for s, o in g.subject_objects(isBasedOn)}
    assert nodes == {'https://example.org/kb/a': 'https://example.org/kb/a#paper',
                     'https://example.org/kb/b': 'https://example.org/kb/b#paper'}
    assert set(g.objects(URIRef('https://example.org/kb/a#paper'), excerpt)) == {Literal('the first passage')}
    urls = {o for n in nodes.values() for o in g.objects(URIRef(n), URIRef('http://schema.org/url'))}
    assert len(urls) == 1


def test_an_absolute_source_id_is_shared_and_holds_one_excerpt(tmp_path):
    """An absolute IRI names one node that every concept giving it shares, so
    two excerpts on it pass the schema but not SHACL. `lokf validate` names the
    id and the files without changing its verdict."""
    shared = 'https://example.org/kb/paper'
    kb = cite_at(tmp_path / 'kb', a=(shared, 'the first passage'), b=(shared, 'the second passage'))
    result = runner.invoke(app, ['validate', str(kb)])
    assert result.exit_code == 0, result.output
    assert (f"[WARNING] source id '{shared}' has 2 different "
            "excerpts: a.md sources[0] vs. b.md sources[0]") in result.output
    result = runner.invoke(app, ['validate', str(kb), '--shacl'])
    assert result.exit_code == 1
    assert 'MaxCount' in result.output and 'lokf:excerpt' in result.output


def test_excerpt_conflicts_group_by_the_node_an_id_names(tmp_path):
    """One excerpt, or none, on a node is no clash, and neither is one label
    in two concepts. Two absolute ids name two nodes. One concept giving a
    label two excerpts is a clash."""
    from lokf.excerpts import excerpt_conflicts

    shared = 'https://example.org/kb/paper'
    quiet = cite_at(tmp_path / 'quiet', a=(shared, 'one passage'), b=(shared, 'one passage'),
                    c=(shared, None), d=('paper', 'another passage'), e=('paper', 'a third passage'))
    assert list(excerpt_conflicts(load_bundle(quiet))) == []
    loud = cite_at(tmp_path / 'loud', a=(shared, 'one passage'), b=('ex:paper', 'one passage'),
                   c=(shared, 'another passage'))
    findings = list(excerpt_conflicts(load_bundle(loud)))
    assert [severity for severity, _ in findings] == ['WARNING']
    assert 'a.md sources[0] vs. c.md sources[0]' in findings[0][1]
    one = tmp_path / 'one'
    one.mkdir()
    (one / 'index.md').write_text('---\nbase_iri: https://example.org/kb/\ntitle: KB\n---\n')
    (one / 'a.md').write_text('---\n' + yaml.safe_dump({'type': 'Explanation', 'title': 'a', 'sources': [
        {'id': 'paper', 'resource': 'https://example.org/paper', 'excerpt': 'one passage'},
        {'id': 'paper', 'resource': 'https://example.org/paper', 'excerpt': 'another passage'}]}) + '---\n')
    findings = list(excerpt_conflicts(load_bundle(one)))
    assert len(findings) == 1
    assert "source id 'paper' (https://example.org/kb/a#paper)" in findings[0][1]


def test_excerpt_conflicts_expand_ids_under_the_context(tmp_path):
    """A CURIE and its full IRI name one node; a prefix with `_` is a CURIE."""
    from lokf.excerpts import excerpt_conflicts

    kb = cite_at(tmp_path / 'curie', a=('schema:Article', 'one passage'),
                 b=('http://schema.org/Article', 'another passage'))
    findings = list(excerpt_conflicts(load_bundle(kb)))
    assert len(findings) == 1 and '(http://schema.org/Article)' in findings[0][1]
    kb = cite_at(tmp_path / 'adms', a=('adms_status:Completed', 'one passage'),
                 b=('adms_status:Completed', 'another passage'))
    assert len(list(excerpt_conflicts(load_bundle(kb)))) == 1


def test_a_source_label_stays_local_without_a_base(tmp_path):
    """With no base_iri, a label stays local to its relative Concept ID, so a
    base a consumer supplies still gives two nodes."""
    from rdflib import URIRef
    from lokf.excerpts import excerpt_conflicts
    from lokf.rdf import graph_of

    kb = cite_at(tmp_path / 'kb', a=('paper', 'one passage'), b=('paper', 'another passage'))
    (kb / 'index.md').write_text('---\ntitle: KB\n---\n')
    assert list(excerpt_conflicts(load_bundle(kb))) == []
    nodes = set(graph_of(kb).objects(None, URIRef('http://schema.org/isBasedOn')))
    assert len(nodes) == 2 and all(str(n).endswith(('/a#paper', '/b#paper')) for n in nodes)


def test_source_nodes_under_a_hash_base_stay_apart(tmp_path):
    """Under `base_iri: ...#`, a citation never lands on a concept's IRI or on
    another concept's citation (SPEC §5.4)."""
    from rdflib import URIRef
    from lokf.rdf import graph_of

    kb = tmp_path / 'kb'
    (kb / 'a').mkdir(parents=True)
    (kb / 'index.md').write_text('---\nbase_iri: https://example.org/kb#\ntitle: KB\n---\n')
    def write(name, sources):
        (kb / f'{name}.md').write_text('---\n' + yaml.safe_dump(
            {'type': 'Explanation', 'title': name, 'sources': sources}) + '---\n')
    write('a', [{'id': 'evidence', 'resource': 'https://example.org/e', 'excerpt': 'one passage'},
                {'id': 'b/fig', 'resource': 'https://example.org/f'}])
    write('a/evidence', [])
    write('a/b', [{'id': 'fig', 'resource': 'https://example.org/g'}])
    g = graph_of(kb)
    nodes = {str(o) for o in g.objects(None, URIRef('http://schema.org/isBasedOn'))}
    assert nodes == {'https://example.org/kb#a//evidence', 'https://example.org/kb#a//b/fig',
                     'https://example.org/kb#a/b//fig'}
    assert not set(g.objects(URIRef('https://example.org/kb#a/evidence'), URIRef('https://w3id.org/lokf/excerpt')))
    result = runner.invoke(app, ['validate', str(kb), '--shacl'])
    assert result.exit_code == 0, result.output


def test_malformed_source_id_warns_without_aborting_other_conflict_checks(tmp_path):
    kb = cite_at(tmp_path / 'kb', a=('http://[', 'invalid id passage'),
                 b=('https://example.org/kb/paper', 'first passage'),
                 c=('https://example.org/kb/paper', 'second passage'))
    result = runner.invoke(app, ['validate', str(kb)])
    assert result.exit_code == 0, result.output
    assert "a.md sources[0]: cannot resolve source id 'http://['" in result.output
    assert 'excerpt conflict check skipped for this entry' in result.output
    assert "source id 'https://example.org/kb/paper'" in result.output
    assert 'b.md sources[0] vs. c.md sources[0]' in result.output


def test_strict_fails_one_source_id_with_two_excerpts(tmp_path):
    """SPEC §5.4: an absolute source id SHOULD be used for one passage only.
    `--strict` fails a bundle that does not, and `--shacl` still runs after it
    and names the node."""
    from lokf.validation import validate_bundle

    shared = 'https://example.org/kb/paper'
    kb = cite_at(tmp_path / 'kb', a=(shared, 'the first passage'), b=(shared, 'the second passage'))
    result = runner.invoke(app, ['validate', str(kb), '--strict'])
    assert result.exit_code == 1, result.output
    assert f"[ERROR] source id '{shared}'" in result.output
    report = validate_bundle(kb, strict=True).as_dict()
    assert report['outcome'] == 'invalid' and report['checks']['excerpt_conflicts'] == 'failed'
    assert [(d['code'], d['severity']) for d in report['diagnostics']] == [('excerpt.conflict', 'error')]
    report = validate_bundle(kb, strict=True, shacl=True).as_dict()
    assert report['checks']['shacl'] == 'failed'
    assert 'shacl.MaxCount' in [d['code'] for d in report['diagnostics']]
    local = cite_at(tmp_path / 'local', a=('paper', 'the first passage'), b=('paper', 'the second passage'))
    result = runner.invoke(app, ['validate', str(local), '--strict', '--shacl'])
    assert result.exit_code == 0, result.output

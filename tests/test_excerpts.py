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
    assert stats == {'local': 3, 'remote': 1}
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

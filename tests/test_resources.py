from pathlib import Path

import yaml
from typer.testing import CliRunner
from lokf.cli import app
from lokf.model import load_bundle
from lokf.resources import check_resources, resource_root


def bundle_at(root, **fields):
    root.mkdir(exist_ok=True)
    (root / 'index.md').write_text('---\nbase_iri: https://example.org/\ntitle: KB\n---\n')
    (root / 'c.md').write_text('---\n' + yaml.safe_dump({'type': 'Service', 'title': 'C', **fields}) + '---\n')
    return load_bundle(root)


def test_paths_identifiers_and_scopes(tmp_path):
    (tmp_path / 'with spaces.txt').write_text('source')
    (tmp_path / 'folder').mkdir()
    b = bundle_at(tmp_path / 'knowledge', resource='with spaces.txt', sources=[
        {'resource': './with spaces.txt'}, {'resource': 'folder'},
        {'resource': 'https://unreachable.invalid/no-file'}, {'resource': 'urn:source:x'},
        {'resource': 'prefix:resource'}, {'resource': 'all queries in project X'},
        {'resource': './absent file.txt'}])
    findings = list(check_resources(b, tmp_path))
    assert [s for s, _ in findings] == ['WARNING', 'ERROR']
    assert 'sources[5].resource' in findings[0][1]
    assert 'sources[6].resource' in findings[1][1]
    assert str(tmp_path / 'absent file.txt') in findings[1][1]


def test_escape_and_symlinks(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    (tmp_path / 'secret').write_text('outside')
    (root / 'link').symlink_to(tmp_path / 'secret')
    b = bundle_at(root / 'kb', resource='link', sources=[{'resource': '../secret'}])
    assert all('outside resource root' in message for _, message in check_resources(b, root))
    assert len(list(check_resources(b, root))) == 2


def test_default_root_and_cli_opt_in(tmp_path):
    b = bundle_at(tmp_path / 'kb', resource='missing.txt')
    assert resource_root(b.root) == tmp_path
    (tmp_path / '.git').write_text('gitdir: elsewhere')
    assert resource_root(b.root) == tmp_path
    runner = CliRunner()
    assert runner.invoke(app, ['validate', str(b.root)]).exit_code == 0
    result = runner.invoke(app, ['validate', str(b.root), '--check-resources'])
    assert result.exit_code == 1 and 'missing.txt' in result.output
    (tmp_path / 'missing.txt').write_text('present')
    assert runner.invoke(app, ['validate', str(b.root), '--check-resources', '--root', str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ['validate', str(b.root), '--root', str(tmp_path)]).exit_code == 2

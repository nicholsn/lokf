from pathlib import Path

from typer.testing import CliRunner

from lokf.cli import app
from lokf.logs import check_logs


def test_nested_logs_report_date_errors_with_lines(tmp_path):
    folder = tmp_path / 'nested'
    folder.mkdir()
    (folder / 'log.md').write_text('# Log\n\n## 2026-02-30\n\n## 2026-01-01 (2)\n')
    findings = list(check_logs(tmp_path))
    assert [(s, p.relative_to(tmp_path), n) for s, p, n, _ in findings] == [
        ('ERROR', Path('nested/log.md'), 3), ('ERROR', Path('nested/log.md'), 5)]


def test_logs_ignore_code_and_html_and_allow_missing(tmp_path):
    assert not list(check_logs(tmp_path))
    (tmp_path / 'log.md').write_text('## 2026-02-01\n\n```md\n## bogus\n```\n\n'
                                    '~~~\n## bogus\n~~~\n\n    ## bogus\n\n'
                                    '<!--\n## bogus\n-->\n\n## 2026-01-01\n')
    assert not list(check_logs(tmp_path))


def test_cli_warns_on_order_and_duplicates_but_fails_bad_dates(tmp_path):
    (tmp_path / 'index.md').write_text('---\nbase_iri: https://example.org/\ntitle: KB\n---\n')
    log = tmp_path / 'log.md'
    log.write_text('## 2026-01-01\n\n## 2026-02-01\n\n## 2026-01-01\n')
    result = CliRunner().invoke(app, ['validate', str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert 'duplicate date' in result.output and 'newest first' in result.output
    log.write_text('## 2026-02-30\n')
    result = CliRunner().invoke(app, ['validate', str(tmp_path)])
    assert result.exit_code == 1
    assert 'log.md:1' in result.output

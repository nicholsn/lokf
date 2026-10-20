"""The shipped JSON Schema and CLI must agree after generator upgrades."""
import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from typer.testing import CliRunner

from lokf.cli import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('field', ['status', 'genre', 'http_method'])
@pytest.mark.parametrize('value,valid', [(None, True), ('not-an-enum-value', False)])
def test_optional_enums_agree_in_cli_and_published_schema(tmp_path, field, value, valid):
    concept = {'type': 'Service', 'title': 'Example', field: value, 'body': 'Example'}
    metadata = {'base_iri': 'https://example.org/kb/', 'title': 'KB'}
    (tmp_path / 'index.md').write_text('---\n' + yaml.safe_dump(metadata) + '---\n')
    (tmp_path / 'term.md').write_text('---\n' + yaml.safe_dump(concept) + '---\nExample')
    document = {**metadata, 'concepts': [{**concept, 'id': 'https://example.org/kb/term'}]}
    schema = json.loads((ROOT / 'lokf.schema.json').read_text())
    validator = jsonschema.validators.validator_for(schema)(schema)
    assert validator.is_valid(document) is valid
    result = CliRunner().invoke(app, ['validate', str(tmp_path)])
    assert (result.exit_code == 0) is valid, result.output


def test_bundle_unknown_fields_agree_in_cli_and_published_schema(tmp_path):
    metadata = {'base_iri': 'https://example.org/kb/', 'title': 'KB', 'misspelled_metadata': 'oops'}
    (tmp_path / 'index.md').write_text('---\n' + yaml.safe_dump(metadata) + '---\n')
    schema = json.loads((ROOT / 'lokf.schema.json').read_text())
    validator = jsonschema.validators.validator_for(schema)(schema)
    assert not validator.is_valid({**metadata, 'concepts': []})
    result = CliRunner().invoke(app, ['validate', str(tmp_path)])
    assert result.exit_code == 1
    assert 'misspelled_metadata' in result.output

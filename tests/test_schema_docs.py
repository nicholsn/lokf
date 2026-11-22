from lokf.schema_docs import schema_documentation
from lokf.cli import app
from typer.testing import CliRunner
from pathlib import Path
import json


def test_reference_includes_abstract_and_effective_fields(tmp_path):
    schema = tmp_path / 'domain.yaml'
    schema.write_text('''id: https://example.org/domain
name: domain
prefixes:
  ex: https://example.org/
  linkml: https://w3id.org/linkml/
default_prefix: ex
imports: [linkml:types]
classes:
  Parent:
    abstract: true
    slots: [related, label]
  Child:
    is_a: Parent
    slot_usage:
      related:
        range: Child
        required: true
        multivalued: false
    attributes:
      label:
        range: integer
      local:
        range: string
        pattern: '^x'
        multivalued: true
        exact_cardinality: 2
slots:
  related:
    range: Parent
    multivalued: true
  label:
    range: string
    description: A label
''')
    model = schema_documentation(schema)
    parent, child = ({c['name']: c for c in model['classes']}[n] for n in ['Parent','Child'])
    assert parent['abstract'] and parent['local']
    assert child['is_a'] == 'Parent'
    fields = {s['name']:s for s in child['slots']}
    assert fields['related']['range'] == 'Child'
    assert fields['related']['required'] is True
    assert fields['related']['multivalued'] is False
    assert fields['related']['overridden_here']
    assert not fields['related']['declared_here']
    assert fields['local']['pattern'] == '^x'
    assert fields['label']['class_attribute'] and fields['label']['range'] == 'integer'
    assert next(s for s in model['slots'] if s['name'] == 'label')['range'] == 'string'
    assert fields['local']['declared_here']
    assert fields['local']['exact_cardinality'] == 2
    assert 'local' not in {s['name'] for s in model['slots']}
    assert any(t['name']=='string' and not t['local'] for t in model['types'])


def test_export_schema_is_opt_in(tmp_path):
    runner = CliRunner()
    bundle = Path(__file__).parents[1] / 'examples/acme-knowledge'
    args = ['export',str(bundle),'-d',str(tmp_path)]
    result=runner.invoke(app,args)
    assert result.exit_code == 0, result.output
    assert not (tmp_path/'schema.json').exists()
    result=runner.invoke(app,args+['--schema-docs'])
    assert result.exit_code == 0, result.exception
    model=json.loads((tmp_path/'schema.json').read_text())
    assert model['format']=='lokf-schema-docs-v1'
    assert any(c['name']=='Concept' and c['abstract'] for c in model['classes'])
    source=next(c for c in model['classes'] if c['name']=='Source')
    author=next(s for s in source['slots'] if s['name']=='author')
    assert author['range']=='string'

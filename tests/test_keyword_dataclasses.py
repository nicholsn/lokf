"""Track upstream keyword loading without hiding unrelated generator failures."""
from pathlib import Path

import pytest
import yaml
from linkml.generators.pythongen import PythonGenerator
from linkml_runtime.loaders import yaml_loader


class KeywordLoadingBug(Exception):
    pass


@pytest.mark.xfail(
    raises=KeywordLoadingBug, strict=True,
    reason="LinkML #4083: generated domain dataclasses cannot load the authored from key",
)
def test_domain_dataclasses_load_authored_usage_window(tmp_path):
    core = Path(__file__).resolve().parents[1] / "lokf.yaml"
    schema = tmp_path / "domain.yaml"
    schema.write_text(yaml.safe_dump({
        "id": "https://example.org/domain", "name": "domain",
        "prefixes": {**yaml.safe_load(core.read_text())["prefixes"],
                     "domain": "https://example.org/domain/"},
        "default_prefix": "domain", "imports": [str(core.with_suffix(""))],
        "classes": {"DomainMetric": {"is_a": "Metric"}},
    }))
    # Generate afresh, bypassing LOKF's post-processing of its own module.
    module = PythonGenerator(str(schema)).compile_module()
    data = {
        "id": "https://example.org/metric", "type": "DomainMetric", "title": "Metric",
        "usage_window": {"from": "2026-01-01T00:00:00Z", "to": "2026-02-01T00:00:00Z"},
    }
    try:
        loaded = yaml_loader.loads(yaml.safe_dump(data), target_class=module.DomainMetric)
    except TypeError as exc:
        if "UsageWindow.__init__() got an unexpected keyword argument 'from'" not in str(exc):
            raise
        raise KeywordLoadingBug(str(exc)) from exc
    assert str(loaded.usage_window.from_).startswith("2026-01-01")
    assert str(loaded.usage_window.to).startswith("2026-02-01")


def test_packaged_dataclasses_keep_loading_authored_from():
    from lokf.datamodel import Metric
    loaded = yaml_loader.loads(
        'id: https://example.org/metric\ntype: Metric\ntitle: Metric\n'
        'usage_window:\n  from: "2026-01-01T00:00:00Z"\n  to: "2026-02-01T00:00:00Z"\n',
        target_class=Metric,
    )
    assert str(loaded.usage_window.from_).startswith("2026-01-01")

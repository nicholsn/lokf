"""The JSON-LD injection escapes HTML-breakout sequences."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location(
    "lokf_hooks", ROOT / "docs" / "hooks" / "lokf_hooks.py"
)
hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hooks)


def test_ldjson_script_escapes_script_breakout():
    doc = {"name": "</script><script>alert(1)</script>", "@type": "Dataset"}
    block = hooks._ldjson_script(doc)
    # The raw closing tag must not survive inside the payload.
    inner = block[len('<script type="application/ld+json">'):-len("</script>")]
    assert "</script>" not in inner
    assert "<" not in inner and ">" not in inner
    # Still valid JSON, and round-trips back to the original string.
    import json

    assert json.loads(inner)["name"] == "</script><script>alert(1)</script>"

"""Drift guard for the twice-vendored cytoscape.js.

The package ships src/lokf/static/cytoscape.min.js for the `lokf serve` graph
explorer; the docs site ships docs/assets/js/cytoscape.min.js for its graph
page. `just sync-cytoscape` copies the package copy to the docs copy; this
test fails if they diverge (e.g. a version bump applied to only one).
"""
import pathlib

ROOT = pathlib.Path(__file__).parent.parent


def test_cytoscape_copies_match():
    package = (ROOT / "src" / "lokf" / "static" / "cytoscape.min.js").read_bytes()
    docs = (ROOT / "docs" / "assets" / "js" / "cytoscape.min.js").read_bytes()
    assert package == docs, "cytoscape.min.js copies drifted; run `just sync-cytoscape`"

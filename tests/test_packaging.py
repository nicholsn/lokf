"""Packaging metadata: the license the project declares and the files it ships.

Nothing asserted any of this before, which is how a CC-BY-4.0 LICENSE for
software survived, and how a NOTICE file could be added and then left out of
the wheel.

Asserted against the installed distribution's metadata rather than by parsing
pyproject.toml, so this tests what actually ships — and needs no TOML parser
(``tomllib`` is 3.11+, and the package supports 3.10).
"""
from __future__ import annotations

import pathlib
from importlib.metadata import metadata

ROOT = pathlib.Path(__file__).resolve().parents[1]
META = metadata("lokf")


def test_declared_license_is_apache_2_0():
    """The distribution declares an OSI-approved license, not a CC one."""
    assert META["License-Expression"] == "Apache-2.0"


def test_license_file_is_apache_2_0():
    """LICENSE is the Apache text — the assertion that catches a CC-BY LICENSE."""
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "creativecommons.org" not in text


def test_notice_is_packaged():
    """Apache-2.0 §4(d) only works if NOTICE reaches the installed artifact."""
    assert set(META.get_all("License-File")) == {"LICENSE", "NOTICE"}
    assert (ROOT / "NOTICE").is_file()


def test_notice_names_a_copyright_holder():
    """The Apache grant needs a named owner; LICENSE's appendix is boilerplate."""
    assert "Copyright" in (ROOT / "NOTICE").read_text(encoding="utf-8")

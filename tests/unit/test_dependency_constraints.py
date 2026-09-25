"""Regression test for the mcp dependency upper bound (production risk).

mcp 2.x removed `mcp.server.fastmcp.FastMCP` (this project's server scaffold,
see src/debate_hall_mcp/server.py). An unpinned `mcp>=1.0.0` specifier lets
`pip`/`uv` resolve mcp 2.x, which breaks both CI (mypy fails on the missing
FastMCP attribute) and any fresh `pip install debate-hall-mcp` from PyPI.

This test parses pyproject.toml directly (no import-time dependency on the
mcp package itself) and asserts the declared specifier excludes the 2.x
major line, so a future accidental widening of the constraint fails fast.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet


def _mcp_requirement() -> Requirement:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())
    dependencies = data["project"]["dependencies"]
    mcp_specs = [dep for dep in dependencies if Requirement(dep).name == "mcp"]
    assert len(mcp_specs) == 1, f"expected exactly one mcp dependency line, found {mcp_specs!r}"
    return Requirement(mcp_specs[0])


def test_mcp_dependency_excludes_v2() -> None:
    """mcp>=1.0.0 with no upper bound resolves to mcp 2.x, which removed
    mcp.server.fastmcp.FastMCP and breaks this project at import time.
    The specifier MUST exclude the 2.x major line.
    """
    requirement = _mcp_requirement()
    specifier: SpecifierSet = requirement.specifier

    # A version just inside 2.x must be rejected by the pinned specifier.
    assert not specifier.contains("2.0.0", prereleases=True), (
        f"mcp dependency specifier {specifier!s} permits mcp==2.0.0, which removed "
        "mcp.server.fastmcp.FastMCP (see src/debate_hall_mcp/server.py). "
        'Pin it with an upper bound, e.g. "mcp>=1.0.0,<2".'
    )

    # A known-good 1.x release must still be permitted.
    assert specifier.contains("1.27.1", prereleases=True), (
        f"mcp dependency specifier {specifier!s} unexpectedly excludes the "
        "currently locked working version mcp==1.27.1"
    )

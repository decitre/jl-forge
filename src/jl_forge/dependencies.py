# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Read pyproject.toml dependencies for a browser (emscripten) kernel."""

import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

# Markers are evaluated as if running in Pyodide / xeus-python.
EMSCRIPTEN_MARKERS = {"sys_platform": "emscripten", "platform_system": "Emscripten", "os_name": "posix"}


def load_project(pyproject: Path) -> dict:
    with open(pyproject, "rb") as f:
        return tomllib.load(f).get("project", {})


def collect_requirements(
    project: dict,
    extras: list[str] | None = None,
    baseline: list[str] | None = None,
    exclude: set[str] | None = None,
) -> dict[str, SpecifierSet]:
    """Map canonical package name to the intersection of all its version constraints.

    Requirement extras (``pkg[extra]``) are dropped: conda and piplite don't resolve them.
    """
    optional = project.get("optional-dependencies", {})
    for unknown in sorted(set(extras or ()) - optional.keys()):
        print(f"jl-forge: no optional-dependencies group {unknown!r}, ignored", file=sys.stderr)
    selected = [optional[name] for name in extras or () if name in optional]
    groups = [baseline or (), project.get("dependencies", ()), *selected]

    excluded = {canonicalize_name(n) for n in exclude or ()}
    specs: dict[str, SpecifierSet] = {}
    for group in groups:
        for dep in group:
            req = Requirement(dep)
            name = canonicalize_name(req.name)
            if name in excluded or (req.marker and not req.marker.evaluate(EMSCRIPTEN_MARKERS)):
                continue
            specs[name] = specs.get(name, SpecifierSet()) & req.specifier
    return specs


def to_specs(requirements: dict[str, SpecifierSet]) -> list[str]:
    """Format as ``name>=1,<2`` strings, accepted by both conda and piplite."""
    return [f"{name}{spec}" for name, spec in requirements.items()]

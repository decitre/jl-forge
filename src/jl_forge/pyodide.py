# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Install a project wheel and its dependencies in the Pyodide kernel via piplite."""

import re
from pathlib import Path

INSTALL_LINE = "from install import _; await _()\n"


def find_wheel(wheel_dir: Path, package_name: str) -> Path:
    distribution = re.sub(r"[-_.]+", "_", package_name).lower()
    wheels = sorted(
        p for p in wheel_dir.glob("*.whl") if p.is_file() and p.name.split("-", 1)[0].lower() == distribution
    )
    if len(wheels) != 1:
        found = ", ".join(p.name for p in wheels) or "none"
        raise ValueError(f"expected exactly one wheel for {package_name} in {wheel_dir}; found {len(wheels)}: {found}")
    return wheels[0]


def install_script(wheel_name: str, packages: list[str]) -> str:
    """Source of an ``install.py`` that sits next to the wheel in the site contents."""
    pkg_list = ", ".join(repr(p) for p in [f"emfs:{wheel_name}", *packages])
    return (
        "import piplite\n"
        "async def _():\n"
        f"  packages = [{pkg_list}]\n"
        "  await piplite.install(packages, keep_going=True)\n"
    )

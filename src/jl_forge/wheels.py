# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Bundle wheels into a Pyodide site, so piplite installs them from the site instead of PyPI."""

import base64
import hashlib
import json
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from email.parser import Parser
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

from jl_forge import cache
from jl_forge.dependencies import EMSCRIPTEN_MARKERS

PYPI = "https://pypi.org/pypi"
KERNEL_INDEX = "share/jupyter/labextensions/@jupyterlite/pyodide-kernel-extension/static/pypi/all.json"


def kernel_index_names(prefix: Path = Path(sys.prefix)) -> set[str]:
    """Packages the installed kernel ships in its own piplite index (piplite, its ipykernel stand-in, ...)."""
    index = Path(prefix) / KERNEL_INDEX
    if not index.is_file():
        raise RuntimeError(f"{index} not found; run in the venv where jupyterlite-pyodide-kernel is installed")
    return {canonicalize_name(name) for name in json.loads(index.read_text())}


def _metadata(wheel: Path) -> tuple[str, bytes]:
    with zipfile.ZipFile(wheel) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA") and n.count("/") == 1)
        return name, zf.read(name)


def requires(wheel: Path) -> list[Requirement]:
    """The wheel's Requires-Dist."""
    message = Parser().parsestr(_metadata(wheel)[1].decode())
    return [Requirement(r) for r in message.get_all("Requires-Dist") or []]


def strip_requires(wheel: Path, out: Path) -> None:
    """Copy ``wheel`` to ``out`` without Requires-Dist, so piplite installs it without its dependencies."""
    name, metadata = _metadata(wheel)
    stripped = b"".join(line for line in metadata.splitlines(keepends=True) if not line.startswith(b"Requires-Dist:"))
    digest = base64.urlsafe_b64encode(hashlib.sha256(stripped).digest()).rstrip(b"=").decode()
    with zipfile.ZipFile(wheel) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == name:
                data = stripped
            elif info.filename.endswith(".dist-info/RECORD"):  # keep the wheel's hashes valid
                lines = data.decode().splitlines()
                data = (
                    "\n".join(
                        f"{name},sha256={digest},{len(stripped)}" if line.startswith(name + ",") else line
                        for line in lines
                    ).encode()
                    + b"\n"
                )
            dst.writestr(info, data)


def pure_wheel(name: str, specifier, index: str = PYPI) -> tuple[str, str]:
    """(URL, filename) of the newest pure-Python wheel of ``name`` matching ``specifier``."""
    with urllib.request.urlopen(f"{index.rstrip('/')}/{urllib.parse.quote(name)}/json") as response:
        releases = json.load(response)["releases"]
    versions = []
    for text, files in releases.items():
        try:
            version = Version(text)
        except InvalidVersion:
            continue
        if not version.is_prerelease and specifier.contains(version):
            versions.append((version, files))
    for _, files in sorted(versions, key=lambda vf: vf[0], reverse=True):
        for f in files:
            if f["filename"].endswith("-none-any.whl") and not f.get("yanked"):
                return f["url"], f["filename"]
    raise ValueError(f"{name}{specifier}: no pure-Python wheel on {index}, and the Pyodide distribution lacks it")


def bundle(
    requirements: list[str],
    provided: set[str],
    out_dir: Path,
    cache_dir: Path,
    python_version: str,
    local_wheels: list[Path] = (),
    strip: set[str] = frozenset(),
    index: str = PYPI,
) -> list[Path]:
    """Put in ``out_dir`` the wheels ``requirements`` need beyond the ``provided`` packages; return them.

    Dependencies are followed with markers evaluated for Pyodide's ``python_version``. For a package
    required twice, the first requirement decides the version.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = {
        **EMSCRIPTEN_MARKERS,
        "python_version": ".".join(python_version.split(".")[:2]),
        "python_full_version": python_version,
    }
    local = {canonicalize_name(parse_wheel_filename(Path(w).name)[0]): Path(w) for w in local_wheels}
    todo = [Requirement(r) for r in requirements] + [Requirement(n) for n in local]
    done, bundled = set(), []
    while todo:
        req = todo.pop(0)
        name = canonicalize_name(req.name)
        if name in provided or name in done:
            continue
        done.add(name)
        if name in local:
            wheel = local[name]
        else:
            url, filename = pure_wheel(name, req.specifier, index)
            wheel = cache.download(url, Path(cache_dir) / filename)
        target = out_dir / wheel.name
        if name in strip:
            strip_requires(wheel, target)
        else:
            shutil.copyfile(wheel, target)
            extras = ["", *req.extras]
            todo += [
                r
                for r in requires(wheel)
                if not r.marker or any(r.marker.evaluate({**env, "extra": e}) for e in extras)
            ]
        bundled.append(target)
    return bundled

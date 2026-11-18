# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Bundle wheels into a Pyodide site, so piplite installs them from the site instead of PyPI."""

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from email.parser import Parser
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
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


def _pyodide_env(python_version: str) -> dict[str, str]:
    """Marker environment of Pyodide's Python."""
    return {
        **EMSCRIPTEN_MARKERS,
        "python_version": ".".join(python_version.split(".")[:2]),
        "python_full_version": python_version,
    }


def required_names(wheel_dir: Path, python_version: str, requested: list[str] = ()) -> set[str]:
    """Canonical names the wheels in ``wheel_dir`` require in Pyodide, e.g. distribution packages to keep.

    A wheel's extras count when one of these wheels or a ``requested`` requirement (``pkg[extra]``) asks for them.
    """
    reqs = {canonicalize_name(parse_wheel_filename(w.name)[0]): requires(w) for w in Path(wheel_dir).glob("*.whl")}
    extras = {name: {""} for name in reqs}
    for r in [*(Requirement(r) for r in requested), *(r for rs in reqs.values() for r in rs)]:
        extras.get(canonicalize_name(r.name), set()).update(r.extras)
    env = _pyodide_env(python_version)
    return {
        canonicalize_name(r.name)
        for name, rs in reqs.items()
        for r in rs
        if not r.marker or any(r.marker.evaluate({**env, "extra": e}) for e in extras[name])
    }


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


def resolve(
    requirements: list[str], provided: set[str], python_version: str, simple_indexes: tuple[str, ...] = ()
) -> dict[str, Version]:
    """Solve ``requirements`` together with uv for Pyodide; incompatible constraints raise ValueError.

    ``provided`` packages are overridden out of the solve, so they don't need a wheel for the platform.
    ``simple_indexes`` (PEP 503 URLs, the first one the default) replace uv's own index settings; without
    them uv uses its configuration (``UV_INDEX_URL``, ``uv.toml``, ``pip.conf``).
    shortcut: uv's newest Pyodide target is wasm32-pyodide2024 (Python 3.12 ABI), fine for pure wheels only.
    """
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv not found on PATH; see https://docs.astral.sh/uv/getting-started/installation/")
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "in.txt").write_text("\n".join(requirements))
        (Path(tmp) / "override.txt").write_text("".join(f"{n}; python_version < '0'\n" for n in sorted(provided)))
        result = subprocess.run(
            [uv, "pip", "compile", str(Path(tmp) / "in.txt"), "--override", str(Path(tmp) / "override.txt")]
            + ["--python-platform", "wasm32-pyodide2024", "--python-version", ".".join(python_version.split(".")[:2])]
            + [arg for i, url in enumerate(simple_indexes) for arg in ("--default-index" if i == 0 else "--index", url)]
            + ["--only-binary", ":all:", "--no-header", "--no-annotate", "--quiet"],
            capture_output=True,
            text=True,
        )
    if result.returncode:
        raise ValueError(f"conflicting requirements:\n{result.stderr.strip()}")
    pins = (line.split("==") for line in result.stdout.splitlines() if "==" in line)
    return {canonicalize_name(n): Version(v) for n, v in pins}


def _from_any(name: str, specifier, indexes: tuple[str, ...]) -> tuple[str, str]:
    """``pure_wheel`` from the first of ``indexes`` that has the package, e.g. PyPI, then an intranet index."""
    errors = []
    for index in indexes:
        try:
            return pure_wheel(name, specifier, index)
        except (ValueError, urllib.error.URLError) as e:
            errors.append(str(e))
    raise ValueError("; ".join(errors))


def bundle(
    requirements: list[str],
    provided: set[str],
    out_dir: Path,
    cache_dir: Path,
    python_version: str,
    local_wheels: list[Path] = (),
    strip: set[str] = frozenset(),
    indexes: tuple[str, ...] = (PYPI,),
    simple_indexes: tuple[str, ...] = (),
    provided_versions: dict[str, Version] = {},
) -> list[Path]:
    """Put in ``out_dir`` the wheels ``requirements`` need beyond the ``provided`` packages; return them.

    Dependencies are followed with markers evaluated for Pyodide's ``python_version``. For a package
    required twice, uv picks one version for all of them (see ``resolve``); a conflict raises ValueError, and so does a requirement
    the version of a ``provided`` package in ``provided_versions`` doesn't satisfy.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _pyodide_env(python_version)
    local = {canonicalize_name(parse_wheel_filename(Path(w).name)[0]): Path(w) for w in local_wheels}
    todo = [Requirement(r) for r in requirements] + [Requirement(n) for n in local]
    # stripped local wheels are left out of the solve: their dependencies are deliberately not installed
    pins = resolve(
        [*requirements, *(str(w.resolve()) for n, w in local.items() if n not in strip)],
        provided,
        python_version,
        simple_indexes,
    )
    done, bundled = set(), []
    while todo:
        req = todo.pop(0)
        name = canonicalize_name(req.name)
        if name in provided:
            have = provided_versions.get(name)
            if have and not req.specifier.contains(have, prereleases=True):
                raise ValueError(f"{req} is required but the Pyodide distribution provides {name} {have}")
            continue
        if name in done:
            continue
        done.add(name)
        if name in local:
            wheel = local[name]
        else:
            specifier = SpecifierSet(f"=={pins[name]}") if name in pins else req.specifier
            url, filename = _from_any(name, specifier, indexes)
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

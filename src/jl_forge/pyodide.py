# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Pyodide kernel: install the project wheel via piplite, and self-host a pruned Pyodide distribution."""

import io
import json
import re
import tarfile
from pathlib import Path, PurePosixPath

from packaging.utils import canonicalize_name

from jl_forge import cache

INSTALL_LINE = "from install import _; await _()\n"

RELEASE_URL = "https://github.com/pyodide/pyodide/releases/download/{version}/pyodide-{version}.tar.bz2"
LOCK = "pyodide/pyodide-lock.json"
# Distribution packages the kernel loads at startup, measured in the browser with
# jupyterlite-pyodide-kernel 0.7.0; their dependencies come from the lock closure.
KERNEL_PACKAGES = frozenset({"micropip", "sqlite3", "jedi", "ipython", "matplotlib"})


def find_wheel(wheel_dir: Path, package_name: str) -> Path:
    distribution = re.sub(r"[-_.]+", "_", package_name).lower()
    wheels = sorted(
        p for p in wheel_dir.glob("*.whl") if p.is_file() and p.name.split("-", 1)[0].lower() == distribution
    )
    if len(wheels) != 1:
        found = ", ".join(p.name for p in wheels) or "none"
        raise ValueError(f"expected exactly one wheel for {package_name} in {wheel_dir}; found {len(wheels)}: {found}")
    return wheels[0]


def install_script(wheel_name: str, packages: list[str], bundled_wheels: list[str] = ()) -> str:
    """Source of an ``install.py`` that sits next to the wheels in the site contents.

    The project wheel and ``bundled_wheels`` install with ``deps=False``: their dependencies come by
    name in ``packages``, so ``--exclude`` holds and wheel metadata isn't resolved again.
    """
    wheels = ", ".join(repr(f"emfs:{w}") for w in [wheel_name, *bundled_wheels])
    return (
        "import piplite\n"
        "async def _():\n"
        f"  emfs_wheels = [{wheels}]\n"
        "  for wheel in emfs_wheels:\n"
        "    await piplite.install(wheel, deps=False, keep_going=True)\n"
        f"  packages = [{', '.join(repr(p) for p in packages)}]\n"
        "  if packages:\n"
        "    await piplite.install(packages, keep_going=True)\n"
    )


def kernel_pyodide_version() -> str:
    """Pyodide release the installed jupyterlite-pyodide-kernel loads."""
    try:
        from jupyterlite_pyodide_kernel.constants import PYODIDE_VERSION
    except ImportError as e:
        raise RuntimeError("jupyterlite-pyodide-kernel is not installed here; pass --version") from e
    return PYODIDE_VERSION


def download(version: str, cache_dir: Path) -> Path:
    """Full ``pyodide-<version>.tar.bz2`` from the GitHub release, downloaded once into ``cache_dir``."""
    return cache.download(RELEASE_URL.format(version=version), Path(cache_dir) / f"pyodide-{version}.tar.bz2")


def _members(tar: tarfile.TarFile):
    """Members of an untrusted distribution: regular files and directories under ``pyodide/`` only."""
    for member in tar:
        parts = PurePosixPath(member.name).parts
        if not parts or parts[0] != "pyodide" or ".." in parts or not (member.isfile() or member.isdir()):
            raise ValueError(f"unexpected member in Pyodide distribution: {member.name!r}")
        yield member


def read_lock(tarball: Path) -> dict:
    with tarfile.open(tarball, "r:bz2") as tar:
        for member in _members(tar):
            if member.name == LOCK:
                return json.load(tar.extractfile(member))
    raise ValueError(f"{tarball} has no {LOCK}")


def cached_lock(version: str, cache_dir: Path) -> dict:
    """``pyodide-lock.json`` of a release, read from its download once and kept next to it."""
    path = Path(cache_dir) / f"pyodide-{version}-lock.json"
    if not path.exists():
        lock = read_lock(download(version, cache_dir))
        path.write_text(json.dumps(lock))
        return lock
    return json.loads(path.read_text())


def lock_closure(lock: dict, names) -> set[str]:
    """Canonical names of ``names`` plus their transitive dependencies in the lock; names absent from it are ignored."""
    packages = {canonicalize_name(k): v for k, v in lock["packages"].items()}
    keep, todo = set(), [canonicalize_name(n) for n in names]
    while todo:
        name = todo.pop()
        if name in keep or name not in packages:
            continue
        keep.add(name)
        todo += [canonicalize_name(d) for d in packages[name].get("depends", ())]
    return keep


def prune(tarball: Path, lock: dict, keep: set[str], out: Path) -> tuple[int, int]:
    """Write ``out`` without the files of packages outside ``keep``; return (kept, dropped) package counts.

    Dropped: the files and lock entries of packages outside ``keep``, and wheels the lock doesn't list
    (Pyodide's test fixtures, which can't be loaded). Everything else, the runtime with its
    ``python_stdlib.zip``, stays. ``out`` keeps the upstream top-level ``pyodide/`` directory, the
    only layout jupyterlite's ``--pyodide`` option reads from a tarball.
    """
    files = {
        canonicalize_name(key): (e["file_name"], e["file_name"] + ".metadata") for key, e in lock["packages"].items()
    }
    kept_files = {f for name in keep for f in files.get(name, ())}
    dropped_files = {f for name, fs in files.items() if name not in keep for f in fs}
    # pruned entries must leave the lock too, or import-based loading fetches them and 404s
    pruned_lock = json.dumps(
        {**lock, "packages": {k: v for k, v in lock["packages"].items() if canonicalize_name(k) in keep}}
    ).encode()
    part = out.with_name(out.name + ".part")
    with tarfile.open(tarball, "r:bz2") as src, tarfile.open(part, "w:bz2") as dst:
        for member in _members(src):
            name = PurePosixPath(member.name).name
            if name in dropped_files or (name.endswith((".whl", ".whl.metadata")) and name not in kept_files):
                continue
            if member.name == LOCK:
                member.size = len(pruned_lock)
                dst.addfile(member, io.BytesIO(pruned_lock))
                continue
            dst.addfile(member, src.extractfile(member) if member.isfile() else None)
    part.rename(out)
    return len(keep), len(lock["packages"]) - len(keep)

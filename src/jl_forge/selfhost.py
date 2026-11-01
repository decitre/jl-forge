# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Serve the files a built JupyterLite site still fetches from other hosts from the site itself."""

import os
import shutil
import tarfile
from pathlib import Path, PurePosixPath

from jl_forge import cache

# Conda-to-PyPI name mapping (prefix-dev/parselmouth, BSD-3-Clause), fetched by jupyterlite-xeus at kernel
# start through a URL hard-coded in its scripts, from both the page and the kernel worker.
MAPPING_URL = b"https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/compressed_mapping.json"
MAPPING = "compressed_mapping.json"
# Font Awesome, linked from Voici pages; "^5" resolves to 5.15.4 (CC-BY-4.0, OFL-1.1 and MIT).
FONTAWESOME_CDN = b"https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@^5/"
FONTAWESOME_TGZ = "https://registry.npmjs.org/@fortawesome/fontawesome-free/-/fontawesome-free-5.15.4.tgz"
FONTAWESOME_DIR = "static/fontawesome-free"
FONTAWESOME_FILES = ("css/all.min.css", "css/v4-shims.min.css", "LICENSE.txt")


def _replace(path: Path, old: bytes, new: bytes) -> None:
    path.write_bytes(path.read_bytes().replace(old, new))


def self_host(site: Path, cache_dir: Path) -> list[str]:
    """Make ``site`` serve the name mapping and Font Awesome itself; return a line per change."""
    site, changes = Path(site), []
    pages = sorted(site.rglob("*.html"))

    scripts = [p for p in site.rglob("*.js") if MAPPING_URL in p.read_bytes()]
    if scripts:
        mapping = cache.download(MAPPING_URL.decode(), Path(cache_dir) / MAPPING)
        for script in scripts:
            _replace(script, MAPPING_URL, MAPPING.encode())
        # a relative URL resolves against the fetching page's directory, or the worker script's
        targets = {s.parent for s in scripts} | {p.parent for p in pages}
        for target in targets:
            shutil.copyfile(mapping, target / MAPPING)
        changes.append(f"{site}: name mapping served from {len(targets)} directories")

    linking = [p for p in pages if FONTAWESOME_CDN in p.read_bytes()]
    if linking:
        tgz = cache.download(FONTAWESOME_TGZ, Path(cache_dir) / FONTAWESOME_TGZ.rsplit("/", 1)[1])
        _extract_fontawesome(tgz, site / FONTAWESOME_DIR)
        for page in linking:
            relative = os.path.relpath(site / FONTAWESOME_DIR, page.parent).replace(os.sep, "/")
            _replace(page, FONTAWESOME_CDN, f"{relative}/".encode())
        changes.append(f"{site}: Font Awesome served for {len(linking)} pages")
    return changes


def _extract_fontawesome(tgz: Path, dest: Path) -> None:
    """The CSS, the woff2/woff fonts browsers load, and the license, from the npm package."""
    with tarfile.open(tgz) as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            if not member.isfile() or path.parts[0] != "package":
                continue
            inner = PurePosixPath(*path.parts[1:])
            is_font = inner.parent == PurePosixPath("webfonts") and inner.suffix in (".woff2", ".woff")
            if str(inner) in FONTAWESOME_FILES or is_font:
                target = dest / inner.parent.name / inner.name if inner.parent.name else dest / inner.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())

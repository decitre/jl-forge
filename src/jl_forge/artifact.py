# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Size of built sites: hardlink identical files, measure against a Pages size limit."""

import hashlib
import os
import re
from collections import defaultdict
from pathlib import Path

UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}


def _files(root: Path):
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and not path.is_symlink():
            yield path


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dedup(root: Path) -> tuple[int, int]:
    """Hardlink files with identical content under ``root``; return (files linked, bytes saved).

    Run it last: a later step editing a file in place would change all its linked copies.
    """
    by_size = defaultdict(list)
    for path in _files(root):
        by_size[path.stat().st_size].append(path)
    linked = saved = 0
    for size, paths in by_size.items():
        if size == 0 or len(paths) < 2:
            continue
        by_digest = defaultdict(list)
        for path in paths:
            by_digest[_digest(path)].append(path)
        for first, *rest in by_digest.values():
            for path in rest:
                if os.path.samefile(first, path):
                    continue
                tmp = path.with_name(path.name + ".jl-forge-link")
                os.link(first, tmp)
                os.replace(tmp, path)  # atomic: the path always holds one of the identical copies
                linked, saved = linked + 1, saved + size
    return linked, saved


def size(root: Path) -> tuple[int, int]:
    """(bytes counting every file in full, bytes counting each hardlinked file once)."""
    total = unique = 0
    seen = set()
    for path in _files(root):
        st = path.stat()
        total += st.st_size
        if (st.st_dev, st.st_ino) not in seen:
            seen.add((st.st_dev, st.st_ino))
            unique += st.st_size
    return total, unique


def parse_size(text: str) -> int:
    """``1G``, ``1000M``, ``500KB`` or bytes; units are powers of 1024, as with ``du``."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMG]?)(?:i?B)?\s*", text, re.IGNORECASE)
    if not match:
        raise ValueError(f"invalid size {text!r}; use e.g. 1G, 1000M or 500K")
    return int(float(match[1]) * UNITS[match[2].upper()])


def human(n: int) -> str:
    return f"{n / 1024**2:.1f} MB"

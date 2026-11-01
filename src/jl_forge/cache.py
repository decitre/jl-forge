# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Downloads and environments kept between builds."""

import shutil
import sys
import urllib.request
from pathlib import Path

DEFAULT_DIR = Path.home() / ".cache" / "jl-forge"


def download(url: str, path: Path) -> Path:
    """``url`` saved at ``path``, downloaded only if ``path`` doesn't exist yet."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        print(f"Downloading {url}", file=sys.stderr)
        with urllib.request.urlopen(url) as response, open(part, "wb") as f:
            shutil.copyfileobj(response, f)
        part.rename(path)  # only complete downloads reach the cache
    return path

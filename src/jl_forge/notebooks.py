# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Prepare notebooks for a JupyterLite site."""

import json
from pathlib import Path


def strip(notebook: dict) -> dict:
    """Reset code cells to unexecuted and drop saved widget state; other cells stay as they are."""
    for cell in (c for c in notebook.get("cells", []) if c.get("cell_type") == "code"):
        cell.update(outputs=[], execution_count=None)
    notebook.get("metadata", {}).pop("widgets", None)
    return notebook


def prepend_to_first_code_cell(notebook: dict, line: str) -> bool:
    """Prepend ``line`` to the first code cell unless it already starts with it.

    Returns False if the notebook has no code cell.
    """
    if not line.endswith("\n"):
        line += "\n"
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            source = cell.get("source", [])
            if isinstance(source, str):
                source = source.splitlines(keepends=True)
            if not source or source[0] != line:
                cell["source"] = [line, *source]
            return True
    return False


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, notebook: dict) -> None:
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

#!/usr/bin/env bash
# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0
#
# Local check, not run in CI: build the demo's Pyodide site with the latest
# jupyterlite-pyodide-kernel 0.8.x (Pyodide 314, Python 3.14) into
# workspace-0.8.x/public/pyodide-latest. Lab and Notebook only: Voici needs kernel 0.7.0.
# Test it with:
#   JL_FORGE_PUBLIC=examples/demo/workspace-0.8.x/public uv run --group browser pytest examples/demo/smoke_test.py -v
set -euo pipefail

DEMO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO_DIR=$(cd "$DEMO_DIR/../.." && pwd -P)
WORKSPACE="$DEMO_DIR/workspace-0.8.x"
PUBLIC="$WORKSPACE/public"
CACHE="${JL_FORGE_CACHE:-$HOME/.cache/jl-forge}"

cd "$DEMO_DIR"
uv run --no-project --with-editable "$REPO_DIR" jl-forge clean workspace-0.8.x
mkdir -p "$WORKSPACE/content"

uv venv -q "$WORKSPACE/venv"
VIRTUAL_ENV="$WORKSPACE/venv" uv pip install -q -e "$REPO_DIR" jupyterlite-core jupyter_server jupyterlab_server libarchive-c \
  "jupyterlite-pyodide-kernel>=0.8,<0.9" "jupyterlab_widgets~=3.0"
PATH="$WORKSPACE/venv/bin:$PATH"
python -c "from importlib.metadata import version as v; from jupyterlite_pyodide_kernel.constants import PYODIDE_VERSION as p
print(f'jupyterlite-pyodide-kernel {v(\"jupyterlite-pyodide-kernel\")}, Pyodide {p}')"

cp notebooks/*.ipynb "$WORKSPACE/content/"
uv build --wheel --out-dir "$WORKSPACE/content" .
jl-forge pyodide-install --pyproject pyproject.toml --package-name jl-forge-demo --wheel-dir "$WORKSPACE/content"
jl-forge notebooks "$WORKSPACE/content" --strip --pyodide-install
jl-forge pyodide-wheels --pyproject pyproject.toml --cache-dir "$CACHE" --out-dir "$WORKSPACE/lite/pypi"
PYODIDE_DIST=$(jl-forge pyodide-dist --pyproject pyproject.toml --cache-dir "$CACHE/pyodide" --out "$WORKSPACE/pyodide-dist.tar.bz2")
(cd "$WORKSPACE" && jupyter lite build --apps lab --apps notebooks --apps tree --contents "$WORKSPACE/content" \
  --output-dir "$PUBLIC/pyodide-latest" --lite-dir lite --pyodide "$PYODIDE_DIST")

cat > "$PUBLIC/index.html" <<'HTML'
<!doctype html>
<meta charset="utf-8">
<title>jl-forge demo, Pyodide kernel 0.8.x</title>
<h1>jl-forge demo, Pyodide kernel 0.8.x</h1>
<ul>
  <li><a href="pyodide-latest/lab/index.html?path=demo.ipynb">JupyterLab</a>,
    <a href="pyodide-latest/notebooks/index.html?path=demo.ipynb">Notebook</a></li>
</ul>
HTML

jl-forge self-host "$PUBLIC" --cache-dir "$CACHE/self-host"
jl-forge size "$PUBLIC" --max 1G
jl-forge urls "$PUBLIC"

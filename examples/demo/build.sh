#!/usr/bin/env bash
# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0
#
# Build the demo into workspace/public/{xeus,pyodide}. Requires uv and micromamba.
# Each kernel builds in its own venv: jupyter lite copies every installed
# labextension, so a shared venv would put both kernels in both sites. (Real venvs,
# not `uv run --with`: empack looks for its config under sys.prefix.)
set -euo pipefail

DEMO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO_DIR=$(cd "$DEMO_DIR/../.." && pwd -P)
WORKSPACE="$DEMO_DIR/workspace"
PUBLIC="$WORKSPACE/public"
XEUS_PREFIX="$WORKSPACE/xeus-root/envs/xeus-kernels"
# Listing --apps replaces the defaults; voici needs voici-core in the build venv.
APPS=(--apps lab --apps notebooks --apps tree --apps voici)

venv() {  # venv <dir> <packages...>: create a build venv with jl-forge and jupyterlite
  local dir="$1"; shift
  uv venv -q "$dir"
  VIRTUAL_ENV="$dir" uv pip install -q -e "$REPO_DIR" jupyterlite-core jupyter_server jupyterlab_server libarchive-c voici-core "$@"
}

cd "$DEMO_DIR"
uv run --no-project --with-editable "$REPO_DIR" jl-forge clean workspace
mkdir -p "$WORKSPACE/content-xeus" "$WORKSPACE/content-pyodide"

echo "== xeus-python site"
venv "$WORKSPACE/venv-xeus" jupyterlite-xeus
PATH="$WORKSPACE/venv-xeus/bin:$PATH"
cp notebooks/*.ipynb "$WORKSPACE/content-xeus/"
jl-forge notebooks "$WORKSPACE/content-xeus" --strip
jl-forge xeus-env --micromamba --root-prefix "$WORKSPACE/xeus-root" --pyproject pyproject.toml
mounts=$(jl-forge xeus-mount src/jl_forge_demo --prefix "$XEUS_PREFIX")
(cd "$WORKSPACE" && jupyter lite build "${APPS[@]}" --contents "$WORKSPACE/content-xeus" --output-dir "$PUBLIC/xeus" --lite-dir lite-xeus \
  --XeusAddon.prefix="$XEUS_PREFIX" \
  --XeusAddon.mount_jupyterlite_content=True \
  --XeusAddon.mounts="$mounts")

echo "== Pyodide site"
# shortcut: voici-core 0.10.0 only runs the Pyodide kernel up to 0.7.0 (0.7.1+ needs
# @jupyterlab/pluginmanager, missing in Voici's frontend); unpin after a newer voici-core.
# jupyterlab_widgets: the widget frontend for lab/notebooks. xeus gets it from ipywidgets
# in the conda prefix; Pyodide installs ipywidgets at run time, so the build must add it.
venv "$WORKSPACE/venv-pyodide" jupyterlite-pyodide-kernel==0.7.0 "jupyterlab_widgets~=3.0"
PATH="$WORKSPACE/venv-pyodide/bin:$PATH"
cp notebooks/*.ipynb "$WORKSPACE/content-pyodide/"
uv build --wheel --out-dir "$WORKSPACE/content-pyodide" .
jl-forge pyodide-install --pyproject pyproject.toml --package-name jl-forge-demo --wheel-dir "$WORKSPACE/content-pyodide"
jl-forge notebooks "$WORKSPACE/content-pyodide" --strip --pyodide-install
(cd "$WORKSPACE" && jupyter lite build "${APPS[@]}" --contents "$WORKSPACE/content-pyodide" --output-dir "$PUBLIC/pyodide" --lite-dir lite-pyodide)

cat > "$PUBLIC/index.html" <<'HTML'
<!doctype html>
<meta charset="utf-8">
<title>jl-forge demo</title>
<h1>jl-forge demo</h1>
<ul>
  <li>xeus-python kernel: <a href="xeus/lab/index.html?path=demo.ipynb">JupyterLab</a>,
    <a href="xeus/voici/render/demo.html">Voici dashboard</a></li>
  <li>Pyodide kernel: <a href="pyodide/lab/index.html?path=demo.ipynb">JupyterLab</a>,
    <a href="pyodide/voici/render/demo.html">Voici dashboard</a></li>
</ul>
HTML
touch "$PUBLIC/.nojekyll"

jl-forge urls "$PUBLIC"

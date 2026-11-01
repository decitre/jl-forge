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
# Kept between builds (CI caches it): xeus environments and Pyodide/self-hosted downloads.
CACHE="${JL_FORGE_CACHE:-$HOME/.cache/jl-forge}"
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
XEUS_PREFIX=$(jl-forge xeus-env --micromamba --cache-dir "$CACHE/xeus" --pyproject pyproject.toml)
mounts=$(jl-forge xeus-mount src/jl_forge_demo --prefix "$XEUS_PREFIX")
EMPACK_CONFIG=$(jl-forge xeus-pack-config --out "$WORKSPACE/empack.yml")
(cd "$WORKSPACE" && jupyter lite build "${APPS[@]}" --contents "$WORKSPACE/content-xeus" --output-dir "$PUBLIC/xeus" --lite-dir lite-xeus \
  --XeusAddon.prefix="$XEUS_PREFIX" \
  --XeusAddon.empack_config="$EMPACK_CONFIG" \
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
# Bundle the wheels piplite would fetch from PyPI (ipywidgets and its dependencies); jupyter lite build
# indexes <lite-dir>/pypi into the site.
jl-forge pyodide-wheels --pyproject pyproject.toml --cache-dir "$CACHE" --out-dir "$WORKSPACE/lite-pyodide/pypi"
# Self-host Pyodide: the distribution the kernel loads, pruned to the packages the site uses.
PYODIDE_DIST=$(jl-forge pyodide-dist --pyproject pyproject.toml --cache-dir "$CACHE/pyodide" --out "$WORKSPACE/pyodide-dist.tar.bz2")
(cd "$WORKSPACE" && jupyter lite build "${APPS[@]}" --contents "$WORKSPACE/content-pyodide" --output-dir "$PUBLIC/pyodide" --lite-dir lite-pyodide \
  --pyodide "$PYODIDE_DIST")

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

# Serve what the sites still fetch from other hosts (xeus name mapping, Font Awesome) from the sites.
jl-forge self-host "$PUBLIC" --cache-dir "$CACHE/self-host"
# Hardlink the files both sites share: smaller on disk, and in GitLab Pages artifacts. GitHub's Pages
# uploader stores every copy in full, so the limit below counts them all.
jl-forge dedup "$PUBLIC"
jl-forge size "$PUBLIC" --max 1G

jl-forge urls "$PUBLIC"

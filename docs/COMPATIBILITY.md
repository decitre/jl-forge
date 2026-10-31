# Apps, Kernels & Version Constraints

Which JupyterLite apps work with which kernel, the package versions that make them work, and where each constraint comes from. Constraints come from upstream projects; jl-forge doesn't add any.

Verified on 2026-10-31 by building [`examples/demo`](../examples/demo) and running its notebook in Chrome: kernel info, an ipywidgets button updating a label, and two `Output` widgets updated from the button callback. [`smoke_test.py`](../examples/demo/smoke_test.py) repeats these checks in CI on every build.

## Support Matrix

| App | xeus-python | Pyodide |
|:----|:------------|:--------|
| JupyterLab (`--apps lab`) | ✅ Works, widgets included | ✅ Works; widgets need `jupyterlab_widgets` in the build venv |
| Notebook (`--apps notebooks`) | ✅ Same as JupyterLab | ✅ Same as JupyterLab |
| Voici (`--apps voici`) | ✅ Works, except `with output:` capture from callbacks ([below](#output-capture-in-voici-with-xeus-python)) | ✅ Works with `jupyterlite-pyodide-kernel==0.7.0` only |
| Python version | 3.13 | 3.13 with Voici (kernel 0.7.0); 3.14 without (kernel 0.8.x) |

Add `--apps tree` for the file browser and the Notebook app's *File → Open*, and `--apps edit` for the text editor.

## Tested Versions

| Package | xeus-python site | Pyodide site |
|:--------|:-----------------|:-------------|
| `jupyterlite-core` | 0.7.6 (capped by voici-core) | 0.7.6 (capped by voici-core) |
| Kernel | `jupyterlite-xeus` 5.1.0; xeus-python 0.17.8, Python 3.13.1 (emscripten-forge-dev) | `jupyterlite-pyodide-kernel` 0.7.0 (Pyodide 0.29.0, Python 3.13.2) |
| `voici-core` | 0.10.0 | 0.10.0 |
| ipywidgets (kernel) | 8.1.9 from conda-forge | latest from PyPI, installed by piplite |
| Widget frontend | `jupyterlab_widgets` 3.0.17, copied from the conda prefix | `jupyterlab_widgets` 3.0.17, from the build venv |
| Voici widget manager | bundled `@jupyter-widgets/jupyterlab-manager` 5.0.11 | same |

## Constraints and Their Sources

### Voici caps JupyterLite at 0.7

`voici-core` 0.10.0 (2025-12-30, the latest release) requires `jupyterlite-core>=0.7.0,<0.8.0` ([PyPI](https://pypi.org/project/voici-core/0.10.0/)). Its frontend is built on JupyterLite 0.7.0 and JupyterLab 4.5 ([voici#169](https://github.com/voila-dashboards/voici/pull/169)).

Consequence: installing `voici-core` in a build venv holds `jupyterlite-core`, and with it the kernel packages, on the 0.7 line, even for the JupyterLab and Notebook apps of the same site.

### Voici with Pyodide needs `jupyterlite-pyodide-kernel==0.7.0`

- `jupyterlite-pyodide-kernel` 0.7.1 requires `jupyterlite-core>=0.7.3` ([PyPI](https://pypi.org/project/jupyterlite-pyodide-kernel/0.7.1/)). Its extension expects `@jupyterlab/pluginmanager` in the shared frontend modules, a dependency added in JupyterLite 0.7.x ([jupyterlite#1785](https://github.com/jupyterlite/jupyterlite/pull/1785)).
- Voici's frontend, built on JupyterLite 0.7.0, doesn't share it. The page shows "No kernel available"; the console shows `Shared module @jupyterlab/pluginmanager doesn't exist in shared scope default` ([voici#178](https://github.com/voila-dashboards/voici/issues/178)).
- 0.7.0 is the only release that works.

Lift the pin once a voici-core release builds on a newer JupyterLite.

### Pyodide's Python version follows the kernel package

Each `jupyterlite-pyodide-kernel` release loads one Pyodide release from jsDelivr: 0.7.0 loads Pyodide 0.29.0 (Python 3.13), 0.8.x loads Pyodide 314.0.x (Python 3.14). The Voici pin therefore keeps Pyodide sites on Python 3.13.

`jupyter lite build --PyodideAddon.pyodide_url=<release tarball>` bundles another Pyodide release, provided the kernel package supports it.

### xeus-python is on Python 3.13

The Python version is whatever the conda solve picks on the configured channels:

- emscripten-forge-dev (used by jl-forge): Python 3.13.1 only; xeus-python up to 0.17.8, all for 3.13.
- emscripten-forge-4x: Python 3.13.1 and 3.14.3, but xeus-python builds (up to 0.19.0) target 3.13 only.
- The [python recipe](https://github.com/emscripten-forge/recipes/blob/main/recipes/recipes_emscripten/python/recipe.yaml) is at 3.14.3; xeus-python on 3.14 will follow its [recipe](https://github.com/emscripten-forge/recipes/blob/main/recipes/recipes_emscripten/xeus-python/recipe.yaml). `jl-forge xeus-mount` derives the site-packages path from the prefix, so nothing in jl-forge changes when it does.

### Widget frontend in the JupyterLab and Notebook apps

- **xeus-python**: `ipywidgets` in the project dependencies brings `jupyterlab_widgets` into the conda prefix, and `jupyterlite-xeus` copies its labextension into the site. Frontend and kernel versions match by construction.
- **Pyodide**: piplite installs `ipywidgets` in the browser at run time, too late for the site build. Install `jupyterlab_widgets` in the build venv; without it, widgets don't render and the console shows `Exception opening new comm`. Keep it compatible with the kernel's ipywidgets: `ipywidgets` 8.1.x requires `jupyterlab_widgets~=3.0` ([PyPI](https://pypi.org/project/ipywidgets/)).
- **Voici** bundles its own widget manager (`@jupyter-widgets/jupyterlab-manager` 5.0.11, ipywidgets 8 protocol) in both kernels.

### `Output` capture in Voici with xeus-python

Printing inside `with output:` from a widget callback leaves the `Output` widget empty in Voici with xeus-python; the console shows `No such comm registered`. It works in JupyterLab and Notebook with xeus-python, and in all apps with Pyodide. Reported as [voici#127](https://github.com/voila-dashboards/voici/issues/127) (open), see also [voici#132](https://github.com/voila-dashboards/voici/issues/132) for `interact`.

Workaround: update the widget's outputs directly instead of capturing. `append_stdout()` is verified in all six combinations.

```python
output.append_stdout("message\n")                                       # public API
output.outputs = ({"name": "stdout", "output_type": "stream", "text": "message\n"},)  # replace
```

### The `notebook` package isn't needed

The Notebook app comes from `jupyterlite-core` itself (`--apps notebooks`); don't add the `notebook` package to the build venv. The demo builds both Notebook apps without it.

## Desktop-Only Constraints

These affect the same notebooks run in desktop Jupyter (ipykernel), not JupyterLite:

- **ipykernel 7** doesn't run async background tasks after cell completion, so widget updates from such tasks only appear after the next cell ([ipykernel#1510](https://github.com/ipython/ipykernel/issues/1510), [ipywidgets#4012](https://github.com/jupyter-widgets/ipywidgets/issues/4012)). Pin `ipykernel<7` where this matters.
- **Button handlers called twice** for one click ([ipywidgets#3996](https://github.com/jupyter-widgets/ipywidgets/issues/3996)); debounce button handlers as a workaround.

## Options

| Goal | Configuration |
|:-----|:--------------|
| Lab + Notebook + Voici on both kernels (the demo) | Both venvs with `voici-core`; Pyodide venv pins `jupyterlite-pyodide-kernel==0.7.0` and adds `jupyterlab_widgets~=3.0`. Python 3.13 everywhere. |
| Python 3.14 in Pyodide | Pyodide venv without `voici-core`, `jupyterlite-pyodide-kernel` 0.8.x, `jupyterlab_widgets~=3.0`. No Voici on that site; keep Voici on the xeus site. |
| Both of the above | Three sites: xeus (all apps), Pyodide 3.14 (lab, notebooks), Pyodide 3.13 (voici). Longer build, more URLs. |
| Newest JupyterLite for Lab/Notebook | No `voici-core` in that venv: `jupyterlite-core` 0.8.x with `jupyterlite-xeus` 5.1 or `jupyterlite-pyodide-kernel` 0.8.x. |

Each site is one `jupyter lite build` from its own venv, so these combine freely in one build script.

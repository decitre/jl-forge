# Voici Dashboards

[Voici](https://github.com/voila-dashboards/voici) renders each notebook of a JupyterLite site as a dashboard page, `voici/render/<notebook>.html`, run in the browser by the site's kernel. jl-forge needs nothing specific for it: the steps are the same as for any site, plus the three points below. The [demo](https://decitre.github.io/jl-forge/xeus/voici/render/demo.html) builds Voici on both kernels.

## Set It Up

1. **Install `voici-core`** in the build venv, next to the kernel package.
2. **List the apps**: Voici isn't built by default, and `--apps` replaces the defaults.

   ```bash
   jupyter lite build --apps lab --apps notebooks --apps tree --apps voici ...
   ```

   The `[static] app 'voici' is not one of: ...` warning is harmless.
3. **On Pyodide, pin the kernel**: `jupyterlite-pyodide-kernel==0.7.0`, the only release Voici's frontend can run, and add `jupyterlab_widgets~=3.0` so widgets also render in the JupyterLab and Notebook apps of that site.

Each kernel builds from its own venv, so a Voici site on both kernels looks like this (the rest of each build is in the [Usage Guide](USAGE.md#complete-build-script); the demo's [`build.sh`](../examples/demo/build.sh) is a working one):

| Site | Build venv |
|:--|:--|
| xeus-python | `jupyterlite-core`, `jupyterlite-xeus`, `voici-core` |
| Pyodide | `jupyterlite-core`, `jupyterlite-pyodide-kernel==0.7.0`, `jupyterlab_widgets~=3.0`, `voici-core` |

`jl-forge urls PUBLIC` lists the Voici pages it finds, and `self-host` also fetches the Font Awesome CSS that Voici pages load from a CDN, so the site still makes no request to other hosts.

## What to Expect

- **Versions**: `voici-core` 0.10.0 holds `jupyterlite-core` at 0.7 and Pyodide at Python 3.13. To use Python 3.14 or JupyterLite 0.8, keep Voici on the xeus site and build the others without `voici-core`; [the options](COMPATIBILITY.md#options) list the combinations, and [the reasons](COMPATIBILITY.md#voici-caps-jupyterlite-at-07) cite their sources.
- **Widgets**: Voici bundles its own widget manager (ipywidgets 8 protocol) on both kernels.
- **`Output` widget on xeus-python**: `with output:` capture from a callback leaves it empty ([voici#127](https://github.com/voila-dashboards/voici/issues/127)). Use `output.append_stdout("message\n")`; it works in all six app and kernel combinations.

## When Something Is Wrong

| You see | Cause |
|:--|:--|
| "No kernel available" on a Pyodide dashboard, and `Shared module @jupyterlab/pluginmanager doesn't exist` in the console | The Pyodide kernel is newer than 0.7.0; [pin it](DEVELOPMENT.md#voici-shows-no-kernel-available-with-pyodide) |
| A widget doesn't render in JupyterLab or Notebook on Pyodide (`Exception opening new comm`) | `jupyterlab_widgets` is missing from the Pyodide build venv |
| An `Output` widget stays empty on xeus-python | Voici's capture limit above |
| `No version of module anywidget is registered` on a xeus-python Voici site built after a xeus-python Lab site | Both builds ran from the same directory and shared `.jupyterlite.doit.db`; [build each site from its own directory](USAGE.md#complete-build-script) |

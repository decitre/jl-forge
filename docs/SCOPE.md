# When to Use jl-forge

jl-forge doesn't build JupyterLite sites: `jupyter lite build` does, with its kernel add-ons. jl-forge prepares what goes into that build and checks what comes out. This page says what JupyterLite already provides, what jl-forge adds, and when you can do without it.

## The Short Answer

JupyterLite alone is enough when:

- you publish notebooks that import only what the kernel already has, or a short, fixed list of packages;
- loading Pyodide from a CDN is fine, and the site size doesn't matter;
- you use one kernel, and for xeus-python an `environment.yml` is the dependency list you want.

jl-forge pays off when:

- the notebooks import **your own package**, or a dependency list that you keep once in `pyproject.toml` for both kernels;
- the site must **make no request to another host** (an intranet, an offline machine, a privacy requirement);
- the site must **fit a size limit**, such as GitHub Pages' 1 GB, and a 340 MB Pyodide distribution doesn't;
- you build **both kernels** from one project and rebuild often, so cached environments and generated build steps matter.

## What JupyterLite Provides, What jl-forge Adds

| Need | JupyterLite | jl-forge adds |
|:--|:--|:--|
| Build the site: apps, contents, output directory | `jupyter lite build` | Nothing: your build script still calls it |
| Self-host Pyodide | `--pyodide <release tarball>` ships the whole distribution (several hundred MB); you choose the release, and it must match the kernel | `pyodide-dist` takes the release the installed kernel loads and prunes it to the packages the site uses (23 MB instead of 340 MB for the demo) |
| Packages piplite installs | You list wheel URLs by hand (`PipliteAddon.piplite_urls`) | `pyodide-wheels` solves the project's dependencies with uv for Pyodide, so one version fits every constraint, and bundles the complete wheel set; conflicts fail the build |
| Your own package in Pyodide | A wheel you build and install yourself | `pyodide-install` writes the `install.py` for the wheel, `notebooks --pyodide-install` adds the install line to each notebook |
| xeus-python environment | jupyterlite-xeus creates it from an `environment.yml` or uses a `prefix`, packs it with empack, mounts files | `xeus-env` creates the prefix from `pyproject.toml` dependencies and keeps it between builds; `xeus-pack-config` leaves build-only files out of the pack (about half the size); `xeus-mount` derives the `--XeusAddon.mounts` value for your package from the Python installed in the prefix |
| Nothing leaves the site | The offline guide covers Pyodide and the piplite wheels; xeus packages are build-time assets | `self-host` also fetches the files xeus and Voici load from other hosts; the demo's [browser smoke test](DEVELOPMENT.md#browser-smoke-test) shows how to verify it |
| Clean notebooks | | `notebooks --strip` removes code cell outputs and widget state |
| Hosting limits | | `dedup` hardlinks files the sites share, `size` fails the build above a limit |
| Safe rebuilds | | `clean` resets the workspace and refuses directories outside the project |

Kernel 0.8 of the Pyodide kernel adds a lock addon that overlaps with `pyodide-wheels`. [COMPATIBILITY.md](COMPATIBILITY.md#pyodide-kernel-08s-lock-addon) compares them and says when to use which.

## What Stays Out of jl-forge

- **The build.** jl-forge never replaces `jupyter lite build`; you choose the apps and the output directory.
- **The browser.** It installs nothing in the page; see [RUNTIME.md](RUNTIME.md).
- **Application assets.** Models, datasets and other files your app loads are yours to host; `self-host` covers what JupyterLite, xeus and Voici fetch.

## What Could Move Upstream

These steps could belong in the JupyterLite projects, and jl-forge would then shrink. They are candidates, not plans: nothing here has been agreed with upstream.

- **Matching the self-hosted Pyodide to the kernel.** The kernel knows which release it loads; `--pyodide` could default to it.
- **Pruning the Pyodide distribution.** The lock addon already writes a custom `pyodide-lock.json`; pruning is the step it lacks.
- **Resolving the wheel set.** The lock addon does it for kernel 0.8 and later. `pyodide-wheels` remains for kernel 0.7.0, which Voici needs, and for sites that must not reach other hosts.
- **Dependencies from `pyproject.toml`.** jupyterlite-xeus reads `environment.yml`; reading the project's dependencies would make `xeus-env` unnecessary.
- **Files fetched from other hosts.** Bundling them in the xeus and Voici packages would replace the `self-host` step.

`dedup`, `size`, `clean`, `notebooks` and `urls` serve static-hosting workflows and have no obvious upstream home.

## Related Projects

| Project | Relation |
|:--|:--|
| [jupyterlite-core](https://github.com/jupyterlite/jupyterlite), [jupyterlite-pyodide-kernel](https://github.com/jupyterlite/pyodide-kernel), [jupyterlite-xeus](https://github.com/jupyterlite/xeus) | The build system and kernels jl-forge drives |
| jupyterlite-pyodide-kernel's lock addon (0.8+) | Solves a custom `pyodide-lock.json` with uv, as `pyodide-wheels` does for its wheels, but doesn't prune or make the site offline, and Voici needs kernel 0.7.0; see [COMPATIBILITY.md](COMPATIBILITY.md#pyodide-kernel-08s-lock-addon) |
| [Voici](https://github.com/voila-dashboards/voici) | Dashboard app jl-forge's sites include |
| [jupyterlite-sphinx](https://github.com/jupyterlite/jupyterlite-sphinx) | JupyterLite embedded in Sphinx documentation, for docs rather than standalone sites |
| [Shinylive](https://github.com/posit-dev/py-shinylive), [marimo](https://github.com/marimo-team/marimo) | Static WebAssembly exports of their own app and notebook formats; Shinylive also prunes Pyodide |
| [pyodide-pack](https://github.com/pyodide/pyodide-pack) | Shrinks Pyodide apps by detecting the modules they use at run time, a finer cut than pruning whole packages |

<!-- Also related, not listed: jupyterlite-pyodide-lock (standalone lock addon,
     https://github.com/deathbeds/jupyterlite-pyodide-lock), repo2jupyterlite
     (https://pypi.org/project/repo2jupyterlite/). -->

## Examples

- **[lmLite](https://github.com/decitre/lmlite)** runs transformer models in the browser. It builds a xeus-python site and a Pyodide site, mounts or installs its package, self-hosts Transformers.js and optional model files next to jl-forge's own self-hosting, and checks the Pyodide site on kernel 0.8.x. Its [`scripts/lite-build.sh`](https://github.com/decitre/lmlite/blob/main/scripts/lite-build.sh) is a full build script.
- **[divelet-ml](https://github.com/decitre/divelet-ml)** adapts *Dive into Deep Learning* notebooks for JupyterLite. Its [`build.sh`](https://github.com/decitre/divelet-ml/blob/main/build.sh) builds both kernels with JupyterLab, Notebook and the file browser, a Pyodide distribution pruned to NumPy and the kernel's startup packages, and the project mounted or installed from one `pyproject.toml`.
- **The [demo](../examples/demo)** in this repository is the smallest complete project, with a browser smoke test.

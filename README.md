<img src="https://raw.githubusercontent.com/decitre/jl-forge/main/docs/logo.svg"
     alt="jl-forge — build steps for JupyterLite sites"
     width="300">

[![Tests][tests-badge]][tests-url]
[![Build demo][ci-badge]][ci-url]
[![Coverage][codecov-badge]][codecov-url]

Package version: `0.3.4`

**Build steps for JupyterLite sites** — turn a Python project and its notebooks into version-matched, pruned and fully offline xeus-python or Pyodide sites, sized for GitHub or GitLab Pages.


## Quick Start

jl-forge runs on the build machine (macOS or Linux), from a project's own build script. Pick a kernel, and install jl-forge in the build environment, next to `jupyterlite-core` and the kernel, not with `pipx` or `uv tool`: `pyodide-dist` reads the Pyodide version from the installed kernel, and the xeus commands import jupyterlite-xeus and empack. In a uv project, `uv add --dev` does it.

**Pyodide site**: project wheel via piplite, bundled wheels, self-hosted and pruned Pyodide.

```sh
pip install jl-forge jupyterlite-core jupyterlite-pyodide-kernel

jl-forge clean workspace                          # rm -rf, refused outside the cwd
jl-forge notebooks workspace/content --strip      # clear code cell outputs
jl-forge pyodide-install --pyproject pyproject.toml --package-name mypkg --wheel-dir workspace/content
jl-forge notebooks workspace/content --pyodide-install
jl-forge pyodide-wheels --pyproject pyproject.toml --out-dir workspace/lite/pypi
jupyter lite build --contents workspace/content --output-dir workspace/public --lite-dir workspace/lite \
  --pyodide "$(jl-forge pyodide-dist --pyproject pyproject.toml --out workspace/pyodide.tar.bz2)"
```

**xeus-python site**: cached conda environment, packed without build-only files, project mounted from source. Also needs [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html).

```sh
pip install 'jl-forge[xeus]' jupyterlite-core     # the extra adds jupyterlite-xeus

jl-forge clean workspace
jl-forge notebooks workspace/content --strip
PREFIX=$(jl-forge xeus-env --micromamba --cache-dir ~/.cache/jl-forge/xeus --pyproject pyproject.toml)
jupyter lite build --contents workspace/content --output-dir workspace/public \
  --XeusAddon.prefix="$PREFIX" \
  --XeusAddon.empack_config="$(jl-forge xeus-pack-config --out workspace/empack.yml)" \
  --XeusAddon.mounts="$(jl-forge xeus-mount src/mypkg --prefix "$PREFIX")"
```

**After either build**: no request to other hosts, shared files stored once, within Pages limits.

```sh
jl-forge self-host workspace/public
jl-forge dedup workspace/public
jl-forge size workspace/public --max 1G
jl-forge urls workspace/public                    # serve command and notebook URLs
```

Building both sites needs one environment per kernel, as [`examples/demo/build.sh`](examples/demo/build.sh) does: `jupyter lite build` copies every installed labextension.

## Features

- **Either kernel**: xeus-python (conda prefix, source mount) or Pyodide (wheel + piplite `install.py`)
- **One dependency list**: kernel packages come from `[project.dependencies]` and extras in `pyproject.toml`
- **Correct dependency handling**: names normalized, duplicate constraints intersected, markers evaluated for emscripten
- **Notebook preparation**: strip outputs of code cells only; idempotent install line for Pyodide
- **No hard-coded Python version**: xeus mount paths follow the Python installed in the prefix
- **Voici dashboards**: demo and docs for either kernel; `jl-forge urls` lists the dashboard pages
- **Self-hosting**: Pyodide pruned to the packages the site uses (`pyodide-dist`, 23 MB instead of 340 MB), the wheels piplite installs (`pyodide-wheels`), and the files xeus and Voici fetch from other hosts (`self-host`): no request leaves the site
- **Pages size limits**: `dedup` hardlinks the files sites share, `size` fails the build above a limit
- **Smaller, faster xeus builds**: environments packed without build-only files (half the size) and reused between builds
- **Safe workspace reset**: `clean` refuses directories outside the project or that look like a project

## What is jl-forge?

jl-forge is a small library and CLI extracted from the JupyterLite builds of several projects. It automates the steps around `jupyter lite build` that JupyterLite's [offline guide](https://jupyterlite.readthedocs.io/en/latest/howto/configure/advanced/offline.html) leaves manual, and that each project used to script by hand:

- **Version matching**: the self-hosted Pyodide is the release the installed kernel loads.
- **Pruning**: Pyodide's 340 MB distribution cut to the packages the site uses, with their dependencies; xeus environments packed without build-only files.
- **A complete wheel set**: the PyPI packages piplite would fetch, with their dependencies, bundled into the site.
- **No external requests**: also the files xeus and Voici load from other hosts, which the guide doesn't mention; the demo's browser smoke test shows how to verify it.
- **Either kernel**, with cached xeus environments and size checks for GitHub or GitLab Pages.

A Python API (`jl_forge.dependencies`, `notebooks`, `xeus`, `pyodide`, `wheels`, `selfhost`, `artifact`) sits behind the CLI.

**jl-forge is not a replacement for JupyterLite's build system.** Your build script still calls `jupyter lite build`, chooses the apps, and handles application-specific assets.

### Related projects

| Project | Relation |
|:--|:--|
| [jupyterlite-core](https://github.com/jupyterlite/jupyterlite), [jupyterlite-pyodide-kernel](https://github.com/jupyterlite/pyodide-kernel), [jupyterlite-xeus](https://github.com/jupyterlite/xeus) | The build system and kernels jl-forge drives |
| jupyterlite-pyodide-kernel's lock addon (0.8+) | Solves a custom `pyodide-lock.json` with uv; resolves better than `pyodide-wheels`, but doesn't prune or make the site offline, and Voici needs kernel 0.7.0; see [COMPATIBILITY.md](https://github.com/decitre/jl-forge/blob/main/docs/COMPATIBILITY.md#pyodide-kernel-08s-lock-addon) |
| [Voici](https://github.com/voila-dashboards/voici) | Dashboard app jl-forge's sites include |
| [jupyterlite-sphinx](https://github.com/jupyterlite/jupyterlite-sphinx) | JupyterLite embedded in Sphinx documentation, for docs rather than standalone sites |
| [Shinylive](https://github.com/posit-dev/py-shinylive), [marimo](https://github.com/marimo-team/marimo) | Static WebAssembly exports of their own app and notebook formats; Shinylive also prunes Pyodide |
| [pyodide-pack](https://github.com/pyodide/pyodide-pack) | Shrinks Pyodide apps by detecting the modules they use at run time, a finer cut than pruning whole packages |

<!-- Also related, not listed: jupyterlite-pyodide-lock (standalone lock addon,
     https://github.com/deathbeds/jupyterlite-pyodide-lock), repo2jupyterlite
     (https://pypi.org/project/repo2jupyterlite/). -->

**Best suited for:** projects publishing a Python package with notebooks as a static JupyterLite site.

> **Note:** jl-forge runs on the build machine (macOS or Linux). It installs nothing in the browser itself; see [docs/RUNTIME.md](https://github.com/decitre/jl-forge/blob/main/docs/RUNTIME.md).


## Feedback and Contributions

jl-forge is an early-stage project. Feedback is particularly welcome on:

- Build steps worth sharing that are still scripted per project.
- JupyterLite, jupyterlite-xeus or Pyodide kernel changes that break the build.
- Support for other apps (Voici, Notebook) and hosting targets.

Please share suggestions, bug reports, and use cases through [GitHub Issues](https://github.com/decitre/jl-forge/issues).

### AI-Assisted Development

Parts of this project were developed with the assistance of generative AI tools. The maintainer is responsible for the architecture, review, testing, and published code.

AI-assisted contributions are welcome, provided contributors understand, review, and test their changes and take responsibility for their submissions.

## Documentation

- **[Getting Started](https://github.com/decitre/jl-forge/blob/main/docs/DEVELOPMENT.md)** - Development setup, testing, demo build and release
- **[Usage Guide](https://github.com/decitre/jl-forge/blob/main/docs/USAGE.md)** - CLI reference, Python API and a complete build script
- **[Apps, Kernels & Version Constraints](https://github.com/decitre/jl-forge/blob/main/docs/COMPATIBILITY.md)** - Lab, Notebook and Voici on xeus-python and Pyodide: what works, pinned versions and why
- **[Runtime & Integration](https://github.com/decitre/jl-forge/blob/main/docs/RUNTIME.md)** - What runs where, and integration boundaries

## Example Output

The demo site below is not the tool: it is what jl-forge builds. CI runs [`examples/demo/build.sh`](examples/demo/build.sh) on one notebook and deploys both sites to GitHub Pages. They load nothing from other hosts, the Pyodide site ships a 23 MB pruned distribution, and the notebook reports which kernel runs it.

- **[xeus-python site][xeus-url]** — `jl_forge_demo` mounted from source into the conda prefix.
- **[Pyodide site][pyodide-url]** — `jl_forge_demo` installed from its wheel by the generated `install.py`.
- **Voici dashboards** — the same notebook as an app: [xeus-python](https://decitre.github.io/jl-forge/xeus/voici/render/demo.html), [Pyodide](https://decitre.github.io/jl-forge/pyodide/voici/render/demo.html).

## How It Works

```
┌───────────────────────────────────────────┐
│ pyproject.toml          notebooks/*.ipynb │
└──────┬──────────────────────────┬─────────┘
       │ jl-forge                 │ jl-forge notebooks
┌──────▼────────────────┐ ┌───────▼──────────────────┐
│ xeus-env / xeus-mount │ │ pyodide-install          │
│ conda prefix (wasm)   │ │ wheel + install.py       │
└──────┬────────────────┘ └───────┬──────────────────┘
       │ jupyter lite build       │ jupyter lite build
┌──────▼────────────────┐ ┌───────▼──────────────────┐
│ public/xeus/          │ │ public/pyodide/          │
└───────────────────────┘ └──────────────────────────┘
               static site → GitHub Pages
```

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.

## Citation

```bibtex
@software{jlforge2026,
  author = {Decitre, Emmanuel},
  title = {jl-forge: Build tooling for JupyterLite sites},
  year = {2026},
  url = {https://github.com/decitre/jl-forge}
}
```

## Acknowledgements

jl-forge builds on several open-source projects:

- [JupyterLite](https://jupyterlite.readthedocs.io/) — the browser-based Jupyter environment.
- [xeus-python](https://github.com/jupyter-xeus/xeus-python), [jupyterlite-xeus](https://github.com/jupyterlite/xeus) and [emscripten-forge](https://emscripten-forge.org/) — Python kernels and packages for the browser.
- [Pyodide](https://pyodide.org/) and [jupyterlite-pyodide-kernel](https://github.com/jupyterlite/pyodide-kernel).

---

[tests-badge]: https://github.com/decitre/jl-forge/actions/workflows/test.yml/badge.svg
[tests-url]: https://github.com/decitre/jl-forge/actions/workflows/test.yml
[codecov-badge]: https://img.shields.io/codecov/c/github/decitre/jl-forge/main?flag=python&label=Coverage&logo=codecov
[codecov-url]: https://codecov.io/gh/decitre/jl-forge
[ci-badge]: https://github.com/decitre/jl-forge/actions/workflows/build.yml/badge.svg
[ci-url]: https://github.com/decitre/jl-forge/actions/workflows/build.yml
[xeus-url]: https://decitre.github.io/jl-forge/xeus/lab/index.html?path=demo.ipynb
[pyodide-url]: https://decitre.github.io/jl-forge/pyodide/lab/index.html?path=demo.ipynb

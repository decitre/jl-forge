[![Tests][tests-badge]][tests-url]
[![py3.13 coverage][codecov-badge]][codecov-url]
[![Build demo site][ci-badge]][ci-url]

[![xeus-badge][xeus-badge]][xeus-url]
[![pyodide-badge][pyodide-badge]][pyodide-url]


# jl-forge

Package version: `0.1.0`

**Build steps for JupyterLite sites** — turn a Python project and its notebooks into xeus-python and Pyodide sites, ready for GitHub Pages.


## Quick Start

**Try the demo online** (no installation required):
- [Launch with xeus-python][xeus-url]
- [Launch with Pyodide][pyodide-url]

**Basic usage**, from a project's own build script:

```sh
jl-forge clean workspace                      # rm -rf, refused outside the cwd
jl-forge notebooks workspace/content --strip  # clear code cell outputs

# xeus-python kernel (needs micromamba)
jl-forge xeus-env --micromamba --root-prefix workspace/xeus --pyproject pyproject.toml
jupyter lite build --contents workspace/content \
  --XeusAddon.prefix=workspace/xeus/envs/xeus-kernels \
  --XeusAddon.mounts="$(jl-forge xeus-mount src/mypkg --prefix workspace/xeus/envs/xeus-kernels)"

# Pyodide kernel: install the project wheel via piplite
jl-forge pyodide-install --pyproject pyproject.toml --package-name mypkg --wheel-dir workspace/content
jl-forge notebooks workspace/content --pyodide-install

# after jupyter lite build: serve command and notebook URLs
jl-forge urls workspace/public
```

## Features

- **Both kernels**: xeus-python (conda prefix, source mount) and Pyodide (wheel + piplite `install.py`)
- **One dependency list**: kernel packages come from `[project.dependencies]` and extras in `pyproject.toml`
- **Correct dependency handling**: names normalized, duplicate constraints intersected, markers evaluated for emscripten
- **Notebook preparation**: strip outputs of code cells only; idempotent install line for Pyodide
- **No hard-coded Python version**: xeus mount paths follow the Python installed in the prefix
- **Voici dashboards**: demo and docs for both kernels; `jl-forge urls` lists the dashboard pages
- **Safe workspace reset**: `clean` refuses directories outside the project or that look like a project

## What is jl-forge?

jl-forge is a small library and CLI extracted from the JupyterLite builds of several projects. It provides:

- The steps around `jupyter lite build` that each project used to script by hand
- A Python API (`jl_forge.dependencies`, `notebooks`, `xeus`, `pyodide`) behind the CLI

**jl-forge is not a replacement for JupyterLite's build system.** Your build script still calls `jupyter lite build`, chooses the apps, and handles application-specific assets.

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
- **[Glossary](https://github.com/decitre/jl-forge/blob/main/docs/GLOSSARY.md)** - Key concepts and terminology

## Interactive Notebooks

The [demo](examples/demo) builds one notebook into both sites; it reports which kernel runs it.

- **[xeus-python demo][xeus-url]** — `jl_forge_demo` mounted from source into the conda prefix.
- **[Pyodide demo][pyodide-url]** — `jl_forge_demo` installed from its wheel by the generated `install.py`.
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
[codecov-badge]: https://img.shields.io/codecov/c/github/decitre/jl-forge/main?flag=python&label=py3.13%20cov&logo=codecov
[codecov-url]: https://codecov.io/gh/decitre/jl-forge
[ci-badge]: https://github.com/decitre/jl-forge/actions/workflows/build.yml/badge.svg
[ci-url]: https://github.com/decitre/jl-forge/actions/workflows/build.yml
[xeus-url]: https://decitre.github.io/jl-forge/xeus/lab/index.html?path=demo.ipynb
[pyodide-url]: https://decitre.github.io/jl-forge/pyodide/lab/index.html?path=demo.ipynb
[pyodide-badge]: https://jupyterlite.rtfd.io/en/latest/_static/badge.svg
[xeus-badge]: https://img.shields.io/badge/try-xeus--python-f7dc1e.svg

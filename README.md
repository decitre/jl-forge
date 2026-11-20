<img src="https://raw.githubusercontent.com/decitre/jl-forge/main/docs/logo.svg"
     alt="jl-forge — build steps for JupyterLite sites"
     width="300">

[![Tests][tests-badge]][tests-url]
[![Build demo][ci-badge]][ci-url]
[![Coverage][codecov-badge]][codecov-url]
[![xeus-badge][xeus-badge]][xeus-url]
[![pyodide-badge][pyodide-badge]][pyodide-url]
[![voici-badge][voici-badge]][voici-url]

Package version: `0.8.0`

**Build steps for JupyterLite sites** — turn a Python project and its notebooks into version-matched, pruned and fully offline xeus-python or Pyodide sites, sized for GitHub or GitLab Pages.

## Try it

[`examples/demo`](https://github.com/decitre/jl-forge/tree/main/examples/demo) builds one notebook into both sites, deployed to GitHub Pages by CI. They load nothing from other hosts.

- **[xeus-python site][xeus-url]**, **[Pyodide site][pyodide-url]**
- **Voici dashboards**: [xeus-python](https://decitre.github.io/jl-forge/xeus/voici/render/demo.html), [Pyodide](https://decitre.github.io/jl-forge/pyodide/voici/render/demo.html)

## Requirements

- Python >= 3.11 on the build machine (macOS or Linux); jl-forge installs nothing in the browser
- `jupyterlite-core` and a kernel package, in the same environment as jl-forge (not `pipx` or `uv tool`)
- [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html), for xeus-python sites

## Install

```sh
pip install 'jl-forge[xeus]' jupyterlite-core                                  # xeus-python site
pip install 'jl-forge[pyodide]' jupyterlite-core jupyterlite-pyodide-kernel    # Pyodide site
```

## Usage

`jupyter lite build` builds the site; jl-forge does what surrounds it, from your build script: dependencies from `pyproject.toml`, Pyodide pruned from 340 MB to 23 MB, xeus environments packed and cached, no request to other hosts, and a size check for Pages limits. It doesn't replace `jupyter lite build`; [when to use jl-forge](https://github.com/decitre/jl-forge/blob/main/docs/SCOPE.md) says when you can do without it.

The [Usage Guide](https://github.com/decitre/jl-forge/blob/main/docs/USAGE.md) has each command and a complete script for both kernels; the demo's [`build.sh`](https://github.com/decitre/jl-forge/blob/main/examples/demo/build.sh) is the smallest real one to adapt.

## Compatibility

| Site | Kernel | Apps | Python |
|:--|:--|:--|:--|
| xeus-python | `jupyterlite-xeus` 5.x | Lab, Notebook, Voici | 3.13 |
| Pyodide | `jupyterlite-pyodide-kernel==0.7.0` | Lab, Notebook, Voici | 3.13 |
| Pyodide | `jupyterlite-pyodide-kernel` 0.8.x | Lab, Notebook | 3.14 |

Each is built and smoke-tested in CI. [Why these versions](https://github.com/decitre/jl-forge/blob/main/docs/COMPATIBILITY.md), and how [Voici](https://github.com/decitre/jl-forge/blob/main/docs/VOICI.md) fits.

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

## Documentation

- **[Usage Guide](https://github.com/decitre/jl-forge/blob/main/docs/USAGE.md)** - CLI reference, Python API, compatibility guarantees, complete build script
- **[When to Use jl-forge](https://github.com/decitre/jl-forge/blob/main/docs/SCOPE.md)** - What JupyterLite provides, what jl-forge adds, related projects
- **[Voici Dashboards](https://github.com/decitre/jl-forge/blob/main/docs/VOICI.md)** - Set up, constraints and known problems
- **[Apps, Kernels & Version Constraints](https://github.com/decitre/jl-forge/blob/main/docs/COMPATIBILITY.md)** - Lab, Notebook and Voici on xeus-python and Pyodide
- **[Runtime & Integration](https://github.com/decitre/jl-forge/blob/main/docs/RUNTIME.md)** - What runs where
- **[Development](https://github.com/decitre/jl-forge/blob/main/docs/DEVELOPMENT.md)** - Setup, tests, release, feedback and AI-assisted contributions

## Contributing

jl-forge is an early-stage project; issues and pull requests are welcome. [DEVELOPMENT.md](https://github.com/decitre/jl-forge/blob/main/docs/DEVELOPMENT.md) covers the setup, tests and AI-assisted contributions.

## License and Citation

Apache License 2.0. See [LICENSE](https://github.com/decitre/jl-forge/blob/main/LICENSE) and [NOTICE](https://github.com/decitre/jl-forge/blob/main/NOTICE).

```bibtex
@software{jlforge2026,
  author = {Decitre, Emmanuel},
  title = {jl-forge: Build tooling for JupyterLite sites},
  year = {2026},
  url = {https://github.com/decitre/jl-forge}
}
```

Built on [JupyterLite](https://jupyterlite.readthedocs.io/), [xeus-python](https://github.com/jupyter-xeus/xeus-python), [jupyterlite-xeus](https://github.com/jupyterlite/xeus), [emscripten-forge](https://emscripten-forge.org/), [Pyodide](https://pyodide.org/) and [jupyterlite-pyodide-kernel](https://github.com/jupyterlite/pyodide-kernel).

[tests-badge]: https://github.com/decitre/jl-forge/actions/workflows/test.yml/badge.svg
[tests-url]: https://github.com/decitre/jl-forge/actions/workflows/test.yml
[codecov-badge]: https://img.shields.io/codecov/c/github/decitre/jl-forge/main?flag=python&label=Coverage&logo=codecov
[codecov-url]: https://codecov.io/gh/decitre/jl-forge
[ci-badge]: https://github.com/decitre/jl-forge/actions/workflows/build.yml/badge.svg
[ci-url]: https://github.com/decitre/jl-forge/actions/workflows/build.yml
[pyodide-badge]: https://img.shields.io/badge/try-Pyodide-f7dc1e.svg?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2OCIgaGVpZ2h0PSI2OCIgdmlld0JveD0iMCAwIDE3Ljk5MiAxNy45OTIiPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKC40NiAuNDQ4KSI+PGNpcmNsZSBjeD0iODMuNzI3IiBjeT0iODUuNjMzIiByPSI2LjU5OCIgc3R5bGU9ImZpbGw6I2Y3ZGMxZTtzdHJva2U6bm9uZTtzdHJva2Utd2lkdGg6LjI2NDU4MzMyIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtNzUuMTkxIC03OS4wMjUpIi8+PHJlY3Qgd2lkdGg9IjUuNjUzIiBoZWlnaHQ9IjEuMDEiIHg9IjgwLjgzMSIgeT0iOTIuMzQ0IiByeD0iLjQxMyIgcnk9Ii40MTMiIHN0eWxlPSJmaWxsOiNmOWY5Zjk7c3Ryb2tlOm5vbmU7c3Ryb2tlLXdpZHRoOjEuOTk5OTk5ODgiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC03NS4xOTEgLTc5LjAyNSkiLz48cmVjdCB3aWR0aD0iNS42NDEiIGhlaWdodD0iMS4wMzEiIHg9IjgwLjgzNyIgeT0iOTMuNjcxIiByeD0iLjQyMSIgcnk9Ii40MjEiIHN0eWxlPSJmaWxsOiNmOWY5Zjk7c3Ryb2tlOm5vbmU7c3Ryb2tlLXdpZHRoOjEuOTk5OTk5NzYiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC03NS4xOTEgLTc5LjAyNSkiLz48cmVjdCB3aWR0aD0iMy4yNCIgaGVpZ2h0PSIxLjAyIiB4PSI4Mi4wMzgiIHk9Ijk1LjAxOSIgcng9Ii40MTciIHJ5PSIuNDE3IiBzdHlsZT0iZmlsbDojZjlmOWY5O3N0cm9rZTpub25lO3N0cm9rZS13aWR0aDoxLjk5OTk5OTg4IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtNzUuMTkxIC03OS4wMjUpIi8+PGcgc3R5bGU9ImZpbGw6IzFhMWExYSI+PGcgc3R5bGU9ImZpbGw6IzFhMWExYTtzdHJva2Utd2lkdGg6LjI2NDU4MzM1Ij48cGF0aCBkPSJNODcuMDY1IDkwLjI4OXEtLjk5Ni0uMDQxLTEuNDc1LTEuMjE2LS4zNTYtLjg4NC0uMzU2LTIuMTY2IDAtLjA2Ni4wMDgtLjE3LjA1OC0uODcyLjMyMy0xLjYuNDMtMS4xNzMgMS4yMTUtMS4xNzMuMDQyIDAgLjA4Ny4wMDQuNzE1LjA0NS43MTUuODMgMCAuODU3LS43MzYgMS45MDItLjQ2Ny42NjYtLjk4IDEuMDguMTQxLjc4NS4zMSAxLjE3OC4zMTUuNzI3LjkzNS43MjcuMDQxIDAgLjA4Ny0uMDA4LjEzNi0uMDI1LjM4LS4xOTguMjM2LS4xNjIuMzY4LS4xNjIuMDU4IDAgLjExMi4wMzguMTIuMDgyLjEyLjIyMy0uMDA5LjIxNS0uMzA2LjQ0Mi0uMzcyLjI2OS0uODA3LjI2OXptLS4yOC01LjcwMXEtLjI0NS4wMDQtLjQzLjIxLS40NzIuNTM0LS41MTcgMi4yMy4yNDgtLjI1My40OTYtLjU5Ni42ODYtLjkzOS42ODYtMS41ODQgMC0uMDMzLS4wMTctLjA3OC0uMDY2LS4xODItLjIxOS0uMTgyeiIgYXJpYS1sYWJlbD0ibCIgc3R5bGU9ImZpbGw6IzFhMWExYTtzdHJva2Utd2lkdGg6LjI2NDU4MzM1IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtNzYuNDA5IC03OS40NzMpIi8+PC9nPjxwYXRoIGQ9Ik04NC45OTggODMuNjYzYS42OTQuNjk0IDAgMCAxLS42OTQuNjk1LjY5NC42OTQgMCAwIDEtLjY5NC0uNjk1LjY5NC42OTQgMCAwIDEgLjY5NC0uNjk0LjY5NC42OTQgMCAwIDEgLjY5NC42OTR6IiBzdHlsZT0iZmlsbDojMWExYTFhO3N0cm9rZTpub25lO3N0cm9rZS13aWR0aDouMjY0NTgzMzIiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC03Ni40MDkgLTc5LjQ3MykiLz48ZyBzdHlsZT0iZmlsbDojMWExYTFhO3N0cm9rZS13aWR0aDouMjY0NTgzMzUiPjxwYXRoIGQ9Ik04NC4xNTUgODQuNjY3cS4yNjkuMDA0LjI3Ny4zNWwtLjQ1OSAzLjI4M3ExLjAzNC0uNzkgMS4xNjItLjg5My4xNTMtLjEzMi4zMTQtLjEzNi4wNTggMCAuMTEyLjAzNy4xMi4wODMuMTIuMjExLS4wMDUuMTk5LS4yMjQuMzg1LS42MDcuNTEyLTEuNjA4IDEuMjZsLS4xOSAxLjM2OXEtLjAxMi4wOTUtLjAzNy4xODYtLjE5LjcyNy0uOTU1LjcyNy0uMzggMC0uNjctLjI4NS0uMjg1LS4yODUtLjI4NS0uNjQgMC0uMzczLjE3OC0uNjEyLjA5OS0uMTI0LjM4OC0uMzRsLjk5Mi0uNzQ0cS41MjUtMy40NjguNTM4LTMuNjQ2IDAtLjAyNS4wMDQtLjA0NS4wNDUtLjQ2Ny4zNDMtLjQ2N3ptLTEuMDg3IDUuNTM1LjA3LS41MDQtLjQ1OS4zNTFxLS4yOTguMjIzLS4zMDIuNDIyIDAgLjA3LjAyNS4xMzIuMDcuMTgyLjI2NS4xODIuMDc4IDAgLjE0LS4wMjUuMTk5LS4wODcuMjYtLjU1OHptLjg5Ny02LjMyNXEwLS4wNzQuMDM3LS4xNC4wODctLjE2Mi4yNjktLjE2Mi4wNzQgMCAuMTQ0LjAzNy4xNTguMDg3LjE1OC4yNjUgMCAuMDc0LS4wMzguMTQ1LS4wODYuMTU3LS4yNjQuMTU3LS4wNzUgMC0uMTQ1LS4wMzgtLjE2MS0uMDgyLS4xNjEtLjI2NHoiIGFyaWEtbGFiZWw9ImoiIHN0eWxlPSJmaWxsOiMxYTFhMWE7c3Ryb2tlLXdpZHRoOi4yNjQ1ODMzNSIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTc2LjQwOSAtNzkuNDczKSIvPjwvZz48L2c+PC9nPjwvc3ZnPiA=
[xeus-badge]: https://img.shields.io/badge/try-xeus--python-f7dc1e.svg?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0Ni43IDQ2LjciPgogIDxwYXRoCiAgICBmaWxsPSIjNDBCM0MzIgogICAgZD0iTTUgMGMyLjUuOCA0LjUgMiA0LjYgMi4xIDEuOSAxLjMgMy42IDMuMSA0LjggNS4xLjQuNiA1LjIgNy44IDguNiAxMi45LS44IDEuMi0xLjUgMi4zLTIuMSAzLjEgMC0uMS0uMS0uMS0uMS0uMkMxNy42IDE3LjkgMTEuNCA4LjYgMTEgNy45Yy0uOS0xLjMtMi0yLjUtMy41LTMuNCAwIDAtMS41LTEtMy41LTEuNkMzLjIgMi42IDEuOCAyLjQgMCAyLjJ2NDIuNGMxLjgtLjIgMy4yLS40IDQtLjcgMi0uNiAzLjUtMS42IDMuNS0xLjYgMS41LTEgMi43LTIuMiAzLjUtMy40LjQtLjcgNi42LTkuOSAxMC4xLTE1LjJDMjQgMTkuMSAzMS40IDguMSAzMS45IDcuM2MxLjItMiAyLjktMy44IDQuOC01LjEgMC0uMSAyLjEtMS4zIDQuNi0yLjFMNDEuOCAwSDV6CiAgICAgICBNNDYuNyAyLjJjLTEuOC4yLTMuMi40LTQgLjctMi4xLjYtMy42IDEuNi0zLjYgMS42LTEuNS45LTIuNiAyLjEtMy41IDMuNC0uNC43LTYuNiA5LjktMTAuMSAxNS4yLTIuOSA0LjQtMTAuMyAxNS41LTEwLjggMTYuMi0xLjIgMi0yLjkgMy44LTQuOCA1LjEgMCAuMS0yLjEgMS4zLTQuNiAyLjFsLS41LjFoMzYuOGwtLjQtLjFjLTIuNS0uOC00LjUtMi00LjYtMi4xLTEuOS0xLjMtMy42LTMuMS00LjgtNS4xLS40LS42LTUuMi03LjgtOC42LTEyLjkuOC0xLjIgMS41LTIuMyAyLjEtMy4xIDAgLjEuMS4xLjEuMiAzLjUgNS4zIDkuNyAxNC41IDEwLjEgMTUuMi45IDEuMyAyIDIuNSAzLjUgMy40IDAgMCAxLjUgMSAzLjUgMS42LjguMyAyLjIuNSA0IC43VjIuMnoiCiAgLz4KPC9zdmc+Cgo=
[voici-badge]: https://img.shields.io/badge/try-Voici-f7dc1e.svg
[voici-url]: https://decitre.github.io/jl-forge/xeus/voici/render/demo.html
[xeus-url]: https://decitre.github.io/jl-forge/xeus/lab/index.html?path=demo.ipynb
[pyodide-url]: https://decitre.github.io/jl-forge/pyodide/lab/index.html?path=demo.ipynb

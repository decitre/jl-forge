# Development Guide

This guide covers development setup, testing, building the demo site, and releasing jl-forge.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Python package and project manager (required)
- [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html) - Conda package manager (required for xeus-python builds)

**Supported Platforms**: macOS (Intel/Apple Silicon) and Linux. Windows is not currently supported.

## Installation

1. Clone the repository:
   ```shell
   git clone https://github.com/decitre/jl-forge.git
   cd jl-forge
   ```

2. Run the tests; uv creates `.venv` with the `dev` dependency group:
   ```shell
   uv run --group dev pytest
   ```

## Project Layout

| Path | Content |
|:-----|:--------|
| `src/jl_forge/dependencies.py` | Read `pyproject.toml` dependencies for an emscripten kernel |
| `src/jl_forge/notebooks.py` | Strip notebooks, prepend a line to the first code cell |
| `src/jl_forge/xeus.py` | Create the xeus-python prefix, compute `--XeusAddon.mounts` |
| `src/jl_forge/pyodide.py` | Find the project wheel, generate `install.py` |
| `src/jl_forge/cli.py` | `jl-forge` command line and `reset_workspace` |
| `tests/` | pytest suite, no network or micromamba needed |
| `examples/demo/` | Demo project, notebook, `build.sh` and `smoke_test.py` |
| `.github/workflows/test.yml` | Unit tests on Python 3.11–3.14; uploads coverage to Codecov |
| `.github/workflows/build.yml` | Builds the demo; deploys it to GitHub Pages from `main` |
| `codecov.yml` | Codecov status checks and pull request comments |
| `.github/workflows/release.yml` | PyPI release, on a published GitHub release or run manually |

## Development Tasks

### Running Tests

```bash
uv run --group dev pytest
```

On every supported Python, as in CI; uv downloads missing interpreters, and `--isolated` leaves `.venv` alone:

```bash
for v in 3.11 3.12 3.13 3.14; do uv run --isolated --python $v --group dev pytest -q; done
```

With coverage, as in CI:

```bash
uv run --group dev pytest --cov --cov-report=term-missing
```

Lint and format with ruff; CI runs the check form:

```bash
uv run --group dev ruff check src tests examples --fix && uv run --group dev ruff format src tests examples   # fix
uv run --group dev ruff check src tests examples && uv run --group dev ruff format src tests examples --check # check
```

`testpaths` is limited to `tests/`: the demo workspace contains conda packages whose own test files would otherwise be collected.

xeus tests replace `jupyterlite_xeus` and `micromamba` with fakes, so they check the commands jl-forge issues, not that the environment can be solved. The demo build covers the real thing.

### Building a Wheel

```bash
uv build
```

The wheel ships `LICENSE` and `NOTICE` in its `licenses/` metadata.

### Version Management

The version lives in `src/jl_forge/__init__.py`, read by hatchling. [bumpver](https://github.com/mbarkhau/bumpver), configured in `[tool.bumpver]` of `pyproject.toml`, keeps it in sync with `current_version` in `pyproject.toml` and the `Package version` line of `README.md`:

```bash
uv run --group dev bumpver update --set-version 0.2.0 --dry   # show the diff only
uv run --group dev bumpver update --set-version 0.2.0         # update, commit, tag 0.2.0, push
```

The version pattern is `MAJOR.MINOR.PATCH[PYTAGNUM]`, so pre-releases such as `0.2.0rc1` are accepted. `--patch`, `--minor` and `--major` increment instead of setting. bumpver refuses to run with uncommitted changes. It doesn't touch `release-notes.md`.

PyPI never accepts a version twice; 0.1.0 is already published.

## Building the JupyterLite Demo

```bash
examples/demo/build.sh
```

The build ends by printing the serve command and the URL of the notebook in each site (`jl-forge urls`). Run the command, then open a URL. The build:

1. Resets `examples/demo/workspace/` with `jl-forge clean`.
2. **xeus-python**: creates `workspace/venv-xeus`, a conda prefix from the demo's `pyproject.toml`, and a site mounting `src/jl_forge_demo` into it.
3. **Pyodide**: creates `workspace/venv-pyodide`, builds the demo wheel into the contents, generates `install.py`, and patches the notebook to call it.

Both sites include the JupyterLab, Notebook, file browser and Voici apps. The xeus-python environment comes from `~/.cache/jl-forge/xeus` once created, and is packed with `xeus-pack-config`; the Pyodide site self-hosts a pruned Pyodide (`pyodide-dist`) and the wheels piplite installs (`pyodide-wheels`), and `self-host` serves the remaining external files from the sites. `dedup` then hardlinks the files the two sites share, and `size` fails the build above GitHub Pages' 1 GB limit. Set `JL_FORGE_CACHE` to use another cache directory; CI caches it between runs. The demo notebook prints the kernel and Python version and exercises an ipywidgets round trip, including `Output` widgets.

Each kernel uses its own venv on purpose: `jupyter lite build` copies every installed labextension, so a shared venv would show both kernels in both sites.

The first build downloads the xeus-python environment from conda-forge and emscripten-forge and takes a few minutes.

### Browser Smoke Test

`examples/demo/smoke_test.py` opens each app of the built demo in Chrome (JupyterLab, Notebook and Voici, on xeus-python and Pyodide) and checks that:

- the notebook runs in the expected kernel (`kernel_info()` output);
- an ipywidgets button click updates a label and an `Output` widget through the kernel;
- `with output:` capture from a callback works, except in Voici with xeus-python, where it is expected to stay empty ([voici#127](https://github.com/voila-dashboards/voici/issues/127)); the test fails if that starts working, so the docs can be updated.

```bash
examples/demo/build.sh
uv run --group browser pytest examples/demo/smoke_test.py -v
```

It needs Google Chrome installed; Playwright drives it through its `chrome` channel, so `playwright install` isn't needed. It serves `workspace/public` itself on a free port, and skips when the demo isn't built. A full run takes about a minute; the first page of each site waits for the kernel download.

The unit test run doesn't collect it (`testpaths = ["tests"]`).

### Coverage on Codecov

`test.yml` runs the unit tests on Python 3.11 to 3.14, one after the other in a single job, on every push to a branch and every pull request. It then uploads the Python 3.13 coverage report to [Codecov](https://codecov.io/gh/decitre/jl-forge). The upload needs a `CODECOV_TOKEN` repository secret, the upload token shown in the repository settings on codecov.io. Without it, the upload step fails the job.

`codecov.yml` fails the project status when coverage on `main` drops by more than 1%; the patch status is off. The browser smoke test isn't part of the coverage: it runs the demo in a browser, not jl-forge's Python code.

### GitHub Pages Deployment

`build.yml` runs `examples/demo/build.sh` and the browser smoke test on pushes, pull requests and manual dispatch, and uploads `workspace/public` as the Pages artifact. Only pushes to `main` deploy.

Pages must be enabled once with GitHub Actions as its source (Settings → Pages), or:

```bash
gh api -X POST repos/decitre/jl-forge/pages -f build_type=workflow
```

## Releasing

1. Create a release branch from `main`, e.g. `git checkout -b release/0.2.0`.
2. In `release-notes.md`, rename the `Unreleased` heading to the version, and commit.
3. Run `uv run --group dev bumpver update --set-version 0.2.0`. It updates the version in `pyproject.toml`, `src/jl_forge/__init__.py` and `README.md`, commits, tags `0.2.0`, and pushes the branch and the tag.
4. Open a pull request; `build.yml` builds the demo and runs the browser smoke test.
5. Merge with a merge commit, not a squash, so the tagged commit stays in `main`'s history.
6. Publish a GitHub release for the tag, with the notes from `release-notes.md`. Publishing it, not saving a draft, starts the **Release** workflow: it builds and checks the distributions from the tag, then publishes to PyPI through trusted publishing. Publishing a version is irreversible. Without a GitHub release, run the workflow manually on `main` with `publish` checked; unchecked, it only builds and checks.

## Troubleshooting

### `TypeError: expected str, bytes or os.PathLike object, not NoneType` from empack?

empack looks for its default configuration under `sys.prefix/share/empack`. Ephemeral overlay environments such as `uv run --with jupyterlite-xeus` don't provide it. Install the build tools in a real venv.

### `FileNotFoundError` for the contents directory with `--lite-dir`?

`jupyter lite build` resolves a relative `--contents` path against `--lite-dir`. Pass absolute paths.

### Both kernels appear in the same site?

`jupyterlite-xeus` and `jupyterlite-pyodide-kernel` are installed in the same environment. Build each site from its own venv.

### `micromamba is needed…` or `micromamba not found on PATH`?

Both `jl-forge xeus-env` modes need micromamba on `PATH`: the first message comes from jupyterlite-xeus (default mode), the second from `--micromamba` mode.

### Voici shows "No kernel available" with Pyodide?

The browser console shows `Shared module @jupyterlab/pluginmanager doesn't exist in shared scope default`. jupyterlite-pyodide-kernel 0.7.1 and later need a module that voici-core 0.10.0's frontend doesn't share. Pin `jupyterlite-pyodide-kernel==0.7.0`, as the demo does; see [COMPATIBILITY.md](COMPATIBILITY.md#voici-with-pyodide-needs-jupyterlite-pyodide-kernel070).

### Widgets don't render in Pyodide JupyterLab or Notebook ("Exception opening new comm")?

The widget frontend is missing from the site. Install `jupyterlab_widgets` in the Pyodide build venv; see [COMPATIBILITY.md](COMPATIBILITY.md#widget-frontend-in-the-jupyterlab-and-notebook-apps).

### An `Output` widget stays empty in Voici with xeus-python?

`with output:` capture from callbacks doesn't work there ([voici#127](https://github.com/voila-dashboards/voici/issues/127)). Use `output.append_stdout(...)`; see [COMPATIBILITY.md](COMPATIBILITY.md#output-capture-in-voici-with-xeus-python).

### The demo reports "pyodide" in the xeus-python kernel?

xeus-python on emscripten also provides a `pyodide` module. Detect xeus-python with `importlib.util.find_spec("pyjs")` instead.

### `ModuleNotFoundError` in a Pyodide page, with a 404 for a `.whl` under `static/pyodide/`?

`pyodide-dist` pruned a distribution package that a notebook imports without the project declaring it. Add it to the project's dependencies or pass `--keep NAME`, then rebuild.

### `ModuleNotFoundError: No module named 'encodings'` in a Pyodide page?

The self-hosted distribution lacks `python_stdlib.zip`, the standard library. `pyodide-dist` keeps it; a hand-pruned distribution may not.

### A xeus build uses outdated packages?

`xeus-env --cache-dir` reuses an environment while its specs don't change, so unpinned specs aren't refreshed. Delete `~/.cache/jl-forge/xeus` (or its `<hash>` directory) to recreate it.

### `expected one python3.*/site-packages` from `xeus-mount`?

`--prefix` must be the environment itself (`<root-prefix>/envs/xeus-kernels`), not the root prefix, and the environment must be created first.

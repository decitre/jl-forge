# Runtime & Integration

jl-forge runs at build time. This page describes what it produces for each kernel, and where its responsibility ends.

## Where Things Run

| Stage | Runs on | Tools |
|:------|:--------|:------|
| Build | macOS or Linux, Python ≥ 3.11 | jl-forge, `jupyter lite build`, micromamba, uv/pip |
| Hosting | Any static web server (GitHub Pages, `python -m http.server`) | — |
| Execution | The visitor's browser | xeus-python or Pyodide kernel |

Installing jl-forge in a notebook kernel has no use; it doesn't run in the browser.

## Kernel Comparison

| | xeus-python | Pyodide |
|:--|:--|:--|
| Packages from | conda-forge + emscripten-forge, resolved at build time | Pyodide distribution (jsDelivr CDN, or the site with `pyodide-dist`) and PyPI, resolved in the browser by piplite |
| Your package | Mounted from source (`xeus-mount`) | Built wheel installed by `install.py` |
| When dependencies install | Before the site is published | On first notebook run, from the site with `pyodide-wheels`, else from PyPI |
| Notebook changes | None required | First code cell calls `install.py` |
| Python version | The one in the prefix (currently 3.13) | The one bundled with Pyodide |
| Build needs | micromamba | A wheel build (`uv build` or `python -m build`) |
| Apps and widgets | See [COMPATIBILITY.md](COMPATIBILITY.md) | See [COMPATIBILITY.md](COMPATIBILITY.md) |

Packages with compiled extensions must exist for emscripten: on emscripten-forge for xeus-python, in the Pyodide distribution for Pyodide. Pure-Python packages work with both.

## Requests to Other Hosts

What the demo's pages load from other hosts at run time, measured in Chrome:

| Request | Default | With jl-forge |
|:--|:--|:--|
| Pyodide runtime and its packages (jsDelivr) | Every Pyodide page | None: `pyodide-dist` |
| conda-to-PyPI name mapping (raw.githubusercontent.com) | Every xeus page | None: `self-host` |
| Font Awesome CSS (jsDelivr) | Voici pages | None: `self-host` |
| Packages missing from the Pyodide distribution (PyPI, via piplite) | Pyodide pages | None: `pyodide-wheels` |

With these commands, the demo's pages make no request to other hosts; the browser smoke test enforces it.

## One Kernel per Site

`jupyter lite build` copies every labextension installed in the build environment. Build each site from an environment containing only its kernel package; otherwise both kernels appear in both sites.

## Integration Boundaries

jl-forge does:

- Turn `pyproject.toml` dependencies into kernel package specs.
- Create the xeus-python prefix and compute its mount paths.
- Generate the Pyodide `install.py` and patch notebooks to call it.
- Strip notebooks and reset the build workspace safely.
- Self-host Pyodide and the other files sites fetch from other hosts; shrink and cache xeus environments.

jl-forge does not:

- Replace `jupyter lite build` or choose its apps (`lab`, `notebooks`, `voici`, ...); see [Voici Dashboards](USAGE.md#voici-dashboards).
- Handle application-specific assets: credentials files, model files, extra contents.
- Serve, compress, or deploy the site; the demo's GitHub Actions workflow does that for the demo only.
- Check that dependencies are available for emscripten before micromamba or piplite tries to install them.

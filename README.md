# jl-forge

Reusable tooling for building and publishing JupyterLite sites, including
notebook sites hosted on GitHub Pages.

This initial release provides the installable package and release infrastructure.
JupyterLite build helpers are planned; no build command is implemented yet.

## Installation

After the first successful PyPI release:

```sh
python -m pip install jl-forge
```

From a local checkout:

```sh
python -m pip install .
python -c "import jl_forge; print(jl_forge.__version__)"
```

Python 3.10 or later is required. The distribution is named `jl-forge`;
the import package is `jl_forge`.

## First release: configure trusted publishing

The workflow uses GitHub OIDC and requires no stored PyPI API token.
The repository alone does not configure PyPI or claim the project name.

1. Create a `pypi` environment in this repository under **Settings → Environments**.
   Restrict deployments to `main` and configure required reviewers if supported
   by your GitHub plan.
2. Sign in to PyPI and open <https://pypi.org/manage/account/publishing/>.
   Add a **pending publisher** for a new project with these exact values:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `jl-forge` |
   | GitHub owner | `decitre` |
   | Repository | `jl-forge` |
   | Workflow filename | `release.yml` |
   | Environment | `pypi` |

3. In GitHub **Actions → Release → Run workflow**, choose `main` and leave
   **publish** unchecked to build and validate the distributions only.
4. Review the artifacts. When you explicitly approve publication, manually run
   the workflow on `main` with **publish** checked. Approve the environment
   deployment too if reviewers are configured.

A pending publisher does not reserve the name. Only a successful upload creates
the PyPI project and claims the name, subject to PyPI's naming rules. A 404 from
PyPI does not guarantee that a name is usable: names can be prohibited or reserved.
No publication happens on pushes, tags, or a default manual run.

For an existing PyPI project, add the same publisher in its **Publishing** settings
instead of creating a pending publisher.

## Versioning and local checks

The initial version is `0.1.0`. Update `__version__` in
`src/jl_forge/__init__.py` before each subsequent release; published versions
cannot be overwritten. Keep the release commit on `main`.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade build twine
python -m build
python -m twine check --strict dist/*
python -m pip install dist/*.whl
```

See [PyPI's pending publisher instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [the Python Packaging User Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).

## License

Apache License 2.0; see [LICENSE](LICENSE).

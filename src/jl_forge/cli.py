# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""``jl-forge`` command line: build steps meant to be called from a project's build script."""

import argparse
import contextlib
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

from packaging.utils import canonicalize_name

from jl_forge import artifact, cache, dependencies, notebooks, pyodide, selfhost, wheels, xeus


def reset_workspace(workspace: Path, root: Path) -> None:
    """Delete and recreate ``workspace``, refusing anything not strictly inside ``root``."""
    workspace, root = Path(workspace).resolve(), Path(root).resolve()
    if workspace == root or root not in workspace.parents:
        raise ValueError(f"refusing to reset {workspace}: not strictly inside {root}")
    if (workspace / ".git").exists() or (workspace / "pyproject.toml").exists():
        raise ValueError(f"refusing to reset {workspace}: looks like a project directory")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)


def sites(public: Path) -> list[Path]:
    """JupyterLite sites in ``public``: the directory itself or its subdirectories with a jupyter-lite.json."""
    public = Path(public)
    return sorted(d for d in [public, *public.iterdir()] if d.is_dir() and (d / "jupyter-lite.json").is_file())


def site_urls(public: Path, base_url: str = "http://localhost:8000") -> list[str]:
    """URLs of each notebook in each JupyterLite site under ``public``, per app built."""
    public, base_url = Path(public), base_url.rstrip("/")
    urls = [f"{base_url}/"] if (public / "index.html").is_file() and not (public / "jupyter-lite.json").exists() else []
    for site in sites(public):
        prefix = "/".join(filter(None, [base_url, site.relative_to(public).as_posix().strip(".")]))
        for nb in sorted((site / "files").rglob("*.ipynb")):
            path = nb.relative_to(site / "files").as_posix()
            for app in ("lab", "notebooks"):
                if (site / app / "index.html").is_file():
                    urls.append(f"{prefix}/{app}/index.html?path={quote(path)}")
            voici = Path("voici/render", path).with_suffix(".html").as_posix()
            if (site / voici).is_file():
                urls.append(f"{prefix}/{voici}")
    return urls


def _clean(args) -> None:
    reset_workspace(args.workspace, args.root)


def _notebooks(args) -> None:
    for path in sorted(args.dir.glob("*.ipynb")):
        nb = notebooks.read(path)
        if args.strip:
            notebooks.strip(nb)
        if args.prepend and not notebooks.prepend_to_first_code_cell(nb, args.prepend):
            print(f"No code cell: {path.name}", file=sys.stderr)
        notebooks.write(path, nb)
        print(f"Prepared: {path.name}")


@contextlib.contextmanager
def _stdout_to_stderr():
    """Send stdout, including child processes', to stderr, keeping stdout for a result to capture."""
    sys.stdout.flush()
    saved = os.dup(1)
    os.dup2(2, 1)
    try:
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)


def _xeus_env(args) -> None:
    project = dependencies.load_project(args.pyproject)
    reqs = dependencies.collect_requirements(
        project, args.extras, baseline=xeus.XEUS_RUNTIME, exclude=set(args.exclude)
    )
    specs = dependencies.to_specs(reqs)
    print(specs, file=sys.stderr)
    options = dict(micromamba=args.micromamba, verbose=args.verbose)
    with _stdout_to_stderr():  # micromamba and jupyterlite-xeus print to stdout
        if args.cache_dir:
            prefix = xeus.cached_env(args.cache_dir, specs, **options)
        else:
            prefix = xeus.create_env(args.root_prefix, specs, **options)
    print(prefix.resolve())  # the only stdout line: pass it to --XeusAddon.prefix


def _xeus_pack_config(args) -> None:
    print(xeus.empack_config(args.out))


def _xeus_mount(args) -> None:
    print(xeus.mount(args.source, args.prefix))


def _pyodide_install(args) -> None:
    project = dependencies.load_project(args.pyproject)
    bundled = [Path(w).name for w in args.bundled_wheel]
    missing = [w for w in bundled if not (args.wheel_dir / w).is_file()]
    if missing:  # emfs: URLs resolve next to install.py
        raise SystemExit(f"bundled wheels not in {args.wheel_dir}: {', '.join(missing)}")
    exclude = {*args.exclude, *(w.split("-", 1)[0] for w in bundled)}
    reqs = dependencies.collect_requirements(project, args.extras, exclude=exclude)
    wheel = pyodide.find_wheel(args.wheel_dir, args.package_name)
    output = args.wheel_dir / "install.py"  # must sit next to the wheel for its emfs: URL to resolve
    output.write_text(pyodide.install_script(wheel.name, dependencies.to_specs(reqs), bundled), encoding="utf-8")
    print(f"Generated {output}")


def _pyodide_dist(args) -> None:
    version = args.version or pyodide.kernel_pyodide_version()
    tarball = pyodide.download(version, args.cache_dir)
    out = args.out.resolve()
    if args.no_prune:
        shutil.copyfile(tarball, out)
    else:
        names = set(pyodide.KERNEL_PACKAGES) | set(args.keep)
        if args.pyproject:
            project = dependencies.load_project(args.pyproject)
            names |= set(dependencies.collect_requirements(project, args.extras))
        lock = pyodide.cached_lock(version, args.cache_dir)
        kept, dropped = pyodide.prune(tarball, lock, pyodide.lock_closure(lock, names), out)
        print(f"Pyodide {version}: kept {kept} packages, dropped {dropped}", file=sys.stderr)
    print(out)  # the only stdout line: pass it to --pyodide


def _self_host(args) -> None:
    found = sites(args.public)
    if not found:
        raise ValueError(f"no JupyterLite site in {args.public}")
    for site in found:
        print("\n".join(selfhost.self_host(site, args.cache_dir)) or f"{site}: nothing fetched from other hosts")


def _dedup(args) -> None:
    linked, saved = artifact.dedup(args.public)
    print(f"{args.public}: hardlinked {linked} identical files, {artifact.human(saved)} less on disk")


def _size(args) -> None:
    total, unique = artifact.size(args.public)
    measured = unique if args.links_once else total
    print(f"{args.public}: {artifact.human(total)}, {artifact.human(unique)} counting hardlinked files once")
    if args.max is not None and measured > args.max:
        raise ValueError(f"{artifact.human(measured)} exceeds the {artifact.human(args.max)} limit")


def _pyodide_wheels(args) -> None:
    version = args.version or pyodide.kernel_pyodide_version()
    lock = pyodide.cached_lock(version, args.cache_dir / "pyodide")
    provided = {canonicalize_name(name) for name in lock["packages"]} | wheels.kernel_index_names()
    requirements = [*pyodide.KERNEL_REQUIREMENTS, *args.require]
    if args.pyproject:
        project = dependencies.load_project(args.pyproject)
        requirements += dependencies.to_specs(dependencies.collect_requirements(project, args.extras))
    bundled = wheels.bundle(
        requirements,
        provided,
        args.out_dir,
        args.cache_dir / "wheels",
        lock["info"]["python"],
        local_wheels=args.wheel,
        strip={canonicalize_name(n) for n in args.strip_requires},
        index=args.index_url,
    )
    print(
        f"{args.out_dir}: {len(bundled)} wheels for Pyodide {version}: "
        + (", ".join(w.name for w in bundled) or "none needed")
    )


def _urls(args) -> None:
    print(f"Serve: python -m http.server {args.port} --directory {args.public}")
    print("\n".join(site_urls(args.public, f"http://localhost:{args.port}")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jl-forge", description=__doc__)
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("clean", help="Safely delete and recreate a build workspace")
    p.add_argument("workspace", type=Path)
    p.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Directory the workspace must be inside (default: cwd)"
    )
    p.set_defaults(func=_clean)

    p = sub.add_parser("notebooks", help="Strip and/or patch the notebooks of a directory in place")
    p.add_argument("dir", type=Path)
    p.add_argument("--strip", action="store_true", help="Clear code cell outputs and widget state")
    p.add_argument("--prepend", metavar="LINE", help="Prepend LINE to the first code cell (idempotent)")
    p.add_argument(
        "--pyodide-install",
        dest="prepend",
        action="store_const",
        const=pyodide.INSTALL_LINE,
        help="Same as --prepend with the install.py call generated by pyodide-install",
    )
    p.set_defaults(func=_notebooks)

    p = sub.add_parser("xeus-env", help="Create a xeus-python prefix from pyproject.toml dependencies")
    where = p.add_mutually_exclusive_group(required=True)
    where.add_argument(
        "--root-prefix",
        type=Path,
        help=f"micromamba root; the environment is created in <ROOT_PREFIX>/envs/{xeus.ENV_NAME}",
    )
    where.add_argument(
        "--cache-dir",
        type=Path,
        help="Create the environment once in this micromamba root, and reuse it while the "
        "specs and channels stay the same",
    )
    p.add_argument("--pyproject", type=Path, required=True)
    p.add_argument("--extras", nargs="*", default=[])
    p.add_argument("--exclude", nargs="*", default=[])
    p.add_argument(
        "--micromamba", action="store_true", help="Run micromamba from jl-forge rather than through jupyterlite-xeus"
    )
    p.add_argument("--verbose", action="store_true", help="Show micromamba solver output (-vvv); needs --micromamba")
    p.set_defaults(func=_xeus_env)

    p = sub.add_parser(
        "xeus-pack-config",
        help="Write an empack config that also leaves out files a browser "
        "kernel never uses, for --XeusAddon.empack_config",
    )
    p.add_argument("--out", type=Path, required=True, help="Output YAML; its absolute path is printed")
    p.set_defaults(func=_xeus_pack_config)

    p = sub.add_parser("xeus-mount", help="Print a --XeusAddon.mounts value for a source package")
    p.add_argument("source", type=Path)
    p.add_argument("--prefix", type=Path, required=True, help="The xeus env prefix")
    p.set_defaults(func=_xeus_mount)

    p = sub.add_parser("pyodide-install", help="Write install.py next to the project wheel")
    p.add_argument("--pyproject", type=Path, required=True)
    p.add_argument("--package-name", required=True)
    p.add_argument("--wheel-dir", type=Path, required=True)
    p.add_argument("--extras", nargs="*", default=[])
    p.add_argument("--exclude", nargs="*", default=[], help="e.g. aiohttp, replaced by pyfetch in Pyodide")
    p.add_argument(
        "--bundled-wheel",
        action="append",
        default=[],
        help="Extra wheel in --wheel-dir to install as emfs: with deps=False (repeatable)",
    )
    p.set_defaults(func=_pyodide_install)

    p = sub.add_parser(
        "pyodide-dist",
        help="Self-host Pyodide: write the distribution the kernel loads, "
        "pruned to the packages the site uses, for jupyter lite build --pyodide",
    )
    p.add_argument("--out", type=Path, required=True, help="Output .tar.bz2; its absolute path is printed")
    p.add_argument("--pyproject", type=Path, help="Keep the project's dependencies the distribution provides")
    p.add_argument("--extras", nargs="*", default=[])
    p.add_argument("--keep", nargs="*", default=[], help="More distribution packages the notebooks import")
    p.add_argument("--version", help="Pyodide release (default: the one the installed kernel loads)")
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=cache.DEFAULT_DIR / "pyodide",
        help="Where full distributions are downloaded once (default: %(default)s)",
    )
    p.add_argument("--no-prune", action="store_true", help="Ship the full distribution (~430 MB)")
    p.set_defaults(func=_pyodide_dist)

    p = sub.add_parser(
        "pyodide-wheels",
        help="Bundle the wheels piplite would fetch from PyPI into the site; "
        "run in the Pyodide build venv, write them to <lite-dir>/pypi",
    )
    p.add_argument("--out-dir", type=Path, required=True, help="Usually <lite-dir>/pypi, indexed by jupyter lite build")
    p.add_argument("--pyproject", type=Path, help="Bundle the project's dependencies")
    p.add_argument("--extras", nargs="*", default=[])
    p.add_argument("--require", nargs="*", default=[], metavar="REQ", help="More requirements, e.g. 'ipyleaflet>=0.19'")
    p.add_argument(
        "--wheel",
        nargs="*",
        default=[],
        type=Path,
        metavar="PATH",
        help="Local wheels to bundle, e.g. from a private index; their dependencies are followed",
    )
    p.add_argument(
        "--strip-requires",
        nargs="*",
        default=[],
        metavar="NAME",
        help="Bundle these without their dependency metadata, so piplite installs them alone",
    )
    p.add_argument("--index-url", default=wheels.PYPI, help="JSON API base URL (default: %(default)s)")
    p.add_argument("--version", help="Pyodide release (default: the one the installed kernel loads)")
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=cache.DEFAULT_DIR,
        help="Where Pyodide releases and wheels are kept (default: %(default)s)",
    )
    p.set_defaults(func=_pyodide_wheels)

    p = sub.add_parser(
        "self-host",
        help="Serve from the built sites the files they still fetch from other hosts (xeus name mapping, Font Awesome)",
    )
    p.add_argument("public", type=Path, help="Site output directory, or a directory of sites")
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=cache.DEFAULT_DIR / "self-host",
        help="Where downloads are kept between builds (default: %(default)s)",
    )
    p.set_defaults(func=_self_host)

    p = sub.add_parser("dedup", help="Hardlink identical files in the built sites (run it last)")
    p.add_argument("public", type=Path, help="Site output directory, or a directory of sites")
    p.set_defaults(func=_dedup)

    p = sub.add_parser("size", help="Print the size of the built sites; fail above --max")
    p.add_argument("public", type=Path, help="Site output directory, or a directory of sites")
    p.add_argument("--max", type=artifact.parse_size, help="Limit, e.g. 1G or 1000M (powers of 1024)")
    p.add_argument(
        "--links-once",
        action="store_true",
        help="Count hardlinked files once, as GitLab Pages' "
        "archive stores them; GitHub Pages' uploader stores every copy in full",
    )
    p.set_defaults(func=_size)

    p = sub.add_parser("urls", help="Print the serve command and the URLs of each notebook in the built sites")
    p.add_argument("public", type=Path, help="Site output directory, or a directory of sites")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=_urls)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (ValueError, RuntimeError) as e:
        parser.exit(1, f"jl-forge: error: {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

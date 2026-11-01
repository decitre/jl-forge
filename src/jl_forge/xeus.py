# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Create a xeus-python emscripten prefix, usable as ``--XeusAddon.prefix``."""

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

XEUS_RUNTIME = ["xeus-python", "xeus-python-shell", "xeus-python-shell-lite"]
XEUS_CHANNELS = [
    "https://conda.anaconda.org/conda-forge",
    "https://repo.prefix.dev/emscripten-forge-dev",
]
ENV_NAME = "xeus-kernels"
PLATFORM = "emscripten-wasm32"
# Files empack packs by default that a browser kernel never uses, added to its default exclusions.
# empack matches with fnmatch, where "*" also crosses "/".
EMPACK_EXCLUDES = [
    "lib/libpython*.a",  # static library; the kernel binary is already linked
    "include/*",  # C headers
    "*/tkinter/*",  # no Tk in a browser
    "*/jedi/third_party/typeshed/stubs/*",  # stubs of non-stdlib packages; the stdlib stubs stay for completion
    "*/jedi/third_party/django-stubs/*",
    "*.dist-info/RECORD",  # installed-file lists, only used to uninstall
]


def env_prefix(root_prefix: Path, env_name: str = ENV_NAME) -> Path:
    return Path(root_prefix) / "envs" / env_name


def create_env(
    root_prefix: Path,
    specs: list[str],
    channels: list[str] = XEUS_CHANNELS,
    env_name: str = ENV_NAME,
    micromamba: bool = False,
    verbose: bool = False,
) -> Path:
    """Solve ``specs`` for emscripten-wasm32 into ``<root_prefix>/envs/<env_name>`` and return that prefix.

    jupyterlite-xeus creates the environment, unless ``micromamba`` is set: micromamba then
    runs from here, with its solver output when ``verbose``.
    """
    root_prefix = Path(root_prefix)
    prefix = env_prefix(root_prefix, env_name)
    if micromamba:
        _run_micromamba(micromamba_args(prefix, root_prefix, specs, channels), root_prefix, verbose)
    else:
        from jupyterlite_xeus.create_conda_env import create_conda_env_from_specs

        create_conda_env_from_specs(env_name=env_name, root_prefix=root_prefix, specs=specs, channels=channels)
    return prefix


def cached_env(cache_dir: Path, specs: list[str], channels: list[str] = XEUS_CHANNELS, **create_kwargs) -> Path:
    """Environment for ``specs`` and ``channels``, created once under ``cache_dir`` and reused afterwards.

    Each set of specs gets its own root prefix, keeping the usual environment name the site's paths
    use; the downloaded packages are shared through ``<cache_dir>/pkgs``.
    """
    key = hashlib.sha256(json.dumps([PLATFORM, sorted(specs), list(channels)]).encode()).hexdigest()[:16]
    root = Path(cache_dir) / key
    complete = root / "complete"
    if complete.exists():
        print(f"Reusing {env_prefix(root)}", file=sys.stderr)
        return env_prefix(root)
    shutil.rmtree(root, ignore_errors=True)  # left by an interrupted creation
    os.environ.setdefault("CONDA_PKGS_DIRS", str(Path(cache_dir) / "pkgs"))
    prefix = create_env(root, specs, channels, **create_kwargs)
    complete.touch()
    return prefix


def empack_config(out: Path) -> Path:
    """Write empack's default config plus ``EMPACK_EXCLUDES`` to ``out``, for ``--XeusAddon.empack_config``."""
    import yaml  # installed with jupyterlite-xeus, like empack
    from empack.pack import DEFAULT_CONFIG_PATH

    if DEFAULT_CONFIG_PATH is None:
        raise RuntimeError("empack's default config not found; install jupyterlite-xeus in a virtual environment")
    config = yaml.safe_load(Path(DEFAULT_CONFIG_PATH).read_text())
    config.setdefault("default", {}).setdefault("exclude_patterns", []).extend({"pattern": p} for p in EMPACK_EXCLUDES)
    out = Path(out)
    out.write_text(json.dumps(config, indent=1) + "\n")  # JSON is valid YAML
    return out.resolve()


def micromamba_args(prefix: Path, root_prefix: Path, specs: list[str], channels: list[str]) -> list[str]:
    """``micromamba`` arguments creating ``prefix``; the flags match those jupyterlite-xeus uses."""
    channel_args = [arg for channel in channels for arg in ("--channel", channel)]
    return [
        "create",
        "--yes",
        "--platform",
        PLATFORM,
        "--root-prefix",
        str(root_prefix),
        "--prefix",
        str(prefix),
        "--relocate-prefix",
        "",
        "--no-pyc",
        *channel_args,
        *specs,
    ]


def _run_micromamba(args: list[str], root_prefix: Path, verbose: bool) -> None:
    exe = shutil.which("micromamba")
    if exe is None:
        raise RuntimeError(
            "micromamba not found on PATH; see "
            "https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html"
        )
    root_prefix.mkdir(parents=True, exist_ok=True)
    command = [exe, *args, *(["-vvv"] if verbose else [])]
    print("+", shlex.join(command))
    subprocess.run(command, check=True)


def site_packages(prefix: Path) -> str:
    """In-kernel site-packages path, derived from the Python actually installed in ``prefix``."""
    found = sorted(p.name for p in (Path(prefix) / "lib").glob("python3.*") if (p / "site-packages").is_dir())
    if len(found) != 1:
        raise ValueError(f"expected one python3.*/site-packages under {prefix}/lib; found {found or 'none'}")
    return f"/lib/{found[0]}/site-packages"


def mount(source: Path, prefix: Path) -> str:
    """``--XeusAddon.mounts`` value mounting a source package into the kernel's site-packages."""
    source = Path(source).resolve()
    return f"{source}:{site_packages(prefix)}/{source.name}"

# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Create a xeus-python emscripten prefix, usable as ``--XeusAddon.prefix``."""

import shlex
import shutil
import subprocess
from pathlib import Path

XEUS_RUNTIME = ["xeus-python", "xeus-python-shell", "xeus-python-shell-lite"]
XEUS_CHANNELS = [
    "https://conda.anaconda.org/conda-forge",
    "https://repo.prefix.dev/emscripten-forge-dev",
]
ENV_NAME = "xeus-kernels"
PLATFORM = "emscripten-wasm32"


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

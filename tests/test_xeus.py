import sys
import types
from pathlib import Path

import pytest

from jl_forge import cli, xeus


def test_micromamba_args_target_the_browser_platform():
    args = xeus.micromamba_args(Path("/r/envs/k"), Path("/r"), ["numpy<2"], ["chan-a", "chan-b"])
    assert args[:2] == ["create", "--yes"]
    options = dict(zip(args[2:], args[3:]))
    assert options["--platform"] == "emscripten-wasm32"
    assert options["--prefix"] == "/r/envs/k" and options["--root-prefix"] == "/r"
    assert options["--relocate-prefix"] == "" and "--no-pyc" in args
    assert args[-5:] == ["--channel", "chan-a", "--channel", "chan-b", "numpy<2"]


@pytest.fixture
def fake_micromamba(monkeypatch):
    runs = []
    monkeypatch.setattr(xeus.shutil, "which", lambda name: f"/opt/bin/{name}")
    monkeypatch.setattr(xeus.subprocess, "run", lambda command, check: runs.append(command) if check else None)
    return runs


@pytest.mark.parametrize("verbose", [False, True])
def test_create_env_with_micromamba(fake_micromamba, tmp_path, verbose):
    root = tmp_path / "root"
    prefix = xeus.create_env(root, ["xeus-python"], micromamba=True, verbose=verbose)
    assert prefix == root / "envs" / xeus.ENV_NAME and root.is_dir()
    (command,) = fake_micromamba
    assert command[0] == "/opt/bin/micromamba"
    assert command[1:] == xeus.micromamba_args(prefix, root, ["xeus-python"], xeus.XEUS_CHANNELS) + (["-vvv"] if verbose else [])


def test_create_env_without_micromamba_on_path(monkeypatch, tmp_path):
    monkeypatch.setattr(xeus.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="micromamba not found"):
        xeus.create_env(tmp_path, [], micromamba=True)


def test_cli_xeus_env_delegates_to_jupyterlite_xeus(monkeypatch, tmp_path):
    received = []
    module = types.ModuleType("jupyterlite_xeus.create_conda_env")
    module.create_conda_env_from_specs = lambda **kwargs: received.append(kwargs)
    monkeypatch.setitem(sys.modules, "jupyterlite_xeus", types.ModuleType("jupyterlite_xeus"))
    monkeypatch.setitem(sys.modules, "jupyterlite_xeus.create_conda_env", module)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["numpy"]\n[project.optional-dependencies]\nlab = ["xeus-python>=0.17"]\n')

    cli.main(["xeus-env", "--root-prefix", str(tmp_path / "root"), "--pyproject", str(pyproject), "--extras", "lab"])

    (kwargs,) = received
    assert kwargs["env_name"] == xeus.ENV_NAME and kwargs["channels"] == xeus.XEUS_CHANNELS
    assert kwargs["specs"] == ["xeus-python>=0.17", "xeus-python-shell", "xeus-python-shell-lite", "numpy"]


def test_mount_uses_installed_python(tmp_path):
    prefix = tmp_path / "env"
    (prefix / "lib" / "python3.13" / "site-packages").mkdir(parents=True)
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    assert xeus.mount(src, prefix) == f"{src.resolve()}:/lib/python3.13/site-packages/pkg"
    (prefix / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
    with pytest.raises(ValueError, match="expected one"):
        xeus.site_packages(prefix)

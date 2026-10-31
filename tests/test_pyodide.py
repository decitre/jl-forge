import pytest

from jl_forge.cli import main
from jl_forge.pyodide import find_wheel


def test_find_wheel(tmp_path):
    (tmp_path / "my_pkg-1.0-py3-none-any.whl").touch()
    (tmp_path / "other-1.0-py3-none-any.whl").touch()
    assert find_wheel(tmp_path, "My-Pkg").name == "my_pkg-1.0-py3-none-any.whl"
    (tmp_path / "my_pkg-2.0-py3-none-any.whl").touch()
    with pytest.raises(ValueError, match="found 2"):
        find_wheel(tmp_path, "my-pkg")


def test_cli_writes_executable_install_script(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["tqdm>=4", "aiohttp"]\n')
    (tmp_path / "my_pkg-1.0-py3-none-any.whl").touch()
    main(["pyodide-install", "--pyproject", str(tmp_path / "pyproject.toml"), "--package-name", "my-pkg",
          "--wheel-dir", str(tmp_path), "--exclude", "aiohttp"])
    src = (tmp_path / "install.py").read_text()
    compile(src, "install.py", "exec")
    assert "packages = ['emfs:my_pkg-1.0-py3-none-any.whl', 'tqdm>=4']" in src

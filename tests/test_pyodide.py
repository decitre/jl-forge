import io
import json
import sys
import tarfile

import pytest

from jl_forge import pyodide
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
    main(
        [
            "pyodide-install",
            "--pyproject",
            str(tmp_path / "pyproject.toml"),
            "--package-name",
            "my-pkg",
            "--wheel-dir",
            str(tmp_path),
            "--exclude",
            "aiohttp",
        ]
    )
    src = (tmp_path / "install.py").read_text()
    compile(src, "install.py", "exec")
    assert "emfs_wheels = ['emfs:my_pkg-1.0-py3-none-any.whl']" in src
    assert "await piplite.install(wheel, deps=False, keep_going=True)" in src
    assert "packages = ['tqdm>=4']" in src


def test_cli_bundled_wheels_install_without_deps(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["dep-a>=1", "Dep_B", "orjson"]\n')
    for name in ("my_pkg-1.0", "dep_a-1.0", "dep_b-2.0"):
        (tmp_path / f"{name}-py3-none-any.whl").touch()
    args = ["pyodide-install", "--pyproject", str(tmp_path / "pyproject.toml"), "--package-name", "my-pkg"]
    args += ["--wheel-dir", str(tmp_path), "--bundled-wheel", "dep_a-1.0-py3-none-any.whl"]
    main([*args, "--bundled-wheel", str(tmp_path / "dep_b-2.0-py3-none-any.whl")])
    src = (tmp_path / "install.py").read_text()
    compile(src, "install.py", "exec")
    wheels = ", ".join(f"'emfs:{n}-py3-none-any.whl'" for n in ("my_pkg-1.0", "dep_a-1.0", "dep_b-2.0"))
    assert f"emfs_wheels = [{wheels}]" in src
    assert "await piplite.install(wheel, deps=False, keep_going=True)" in src
    assert "packages = ['orjson']" in src
    with pytest.raises(SystemExit, match="missing.whl"):
        main([*args, "--bundled-wheel", "missing.whl"])


LOCK = {
    "info": {"python": "3.13.2"},
    "packages": {
        "ipython": {"file_name": "ipython-9.0-py3-none-any.whl", "depends": ["prompt_toolkit", "pure-eval"]},
        "prompt-toolkit": {"file_name": "prompt_toolkit-3.0-py3-none-any.whl", "depends": ["wcwidth"]},
        "pure-eval": {"file_name": "pure_eval-0.2-py3-none-any.whl", "depends": []},
        "wcwidth": {"file_name": "wcwidth-0.2-py3-none-any.whl", "depends": []},
        "numpy": {"file_name": "numpy-2.2-cp313-wasm32.whl", "depends": []},
        "numpy-tests": {"file_name": "numpy-tests.tar", "depends": ["numpy"]},
        "libgdal": {"file_name": "libgdal-3.8.zip", "depends": []},
    },
}


def _dist(path, extra=()):
    """Write a small Pyodide-like distribution tarball."""
    files = {
        "pyodide.js": b"js",
        "pyodide.asm.wasm": b"wasm",
        "pyodide-lock.json": json.dumps(LOCK).encode(),
        "python_stdlib.zip": b"stdlib",
        "test_dummy-1.0-py3-none-any.whl": b"fixture",
    }
    for entry in LOCK["packages"].values():
        files[entry["file_name"]] = b"x"
    files["numpy-2.2-cp313-wasm32.whl.metadata"] = b"m"
    with tarfile.open(path, "w:bz2") as tar:
        dirinfo = tarfile.TarInfo("pyodide")
        dirinfo.type = tarfile.DIRTYPE
        tar.addfile(dirinfo)
        for name, data in [*files.items(), *extra]:
            info = tarfile.TarInfo(name if name.startswith(("/", "..", "pyodide/", "x/")) else f"pyodide/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def test_lock_closure_follows_depends_with_normalized_names():
    assert pyodide.lock_closure(LOCK, ["IPython", "absent"]) == {"ipython", "prompt-toolkit", "pure-eval", "wcwidth"}


def test_prune_keeps_runtime_and_kept_archives_only(tmp_path):
    src, out = _dist(tmp_path / "pyodide-1.0.tar.bz2"), tmp_path / "pruned.tar.bz2"
    lock = pyodide.read_lock(src)
    kept, dropped = pyodide.prune(src, lock, pyodide.lock_closure(lock, ["ipython"]), out)
    assert (kept, dropped) == (4, 3)
    with tarfile.open(out) as tar:
        names = sorted(tar.getnames())
    assert names == sorted(
        [
            "pyodide",
            "pyodide/pyodide.js",
            "pyodide/pyodide.asm.wasm",
            "pyodide/pyodide-lock.json",
            "pyodide/python_stdlib.zip",
            "pyodide/ipython-9.0-py3-none-any.whl",
            "pyodide/prompt_toolkit-3.0-py3-none-any.whl",
            "pyodide/pure_eval-0.2-py3-none-any.whl",
            "pyodide/wcwidth-0.2-py3-none-any.whl",
        ]
    )
    assert not list(tmp_path.glob("*.part"))
    assert set(pyodide.read_lock(out)["packages"]) == {"ipython", "prompt-toolkit", "pure-eval", "wcwidth"}


@pytest.mark.parametrize("bad", ["../evil", "/abs", "x/outside", "pyodide/../../evil"])
def test_untrusted_members_are_rejected(tmp_path, bad):
    src = _dist(tmp_path / "d.tar.bz2", extra=[(bad, b"!")])
    with pytest.raises(ValueError, match="unexpected member"):
        pyodide.prune(src, LOCK, set(), tmp_path / "out.tar.bz2")


def test_download_uses_cache(tmp_path, monkeypatch):
    cached = _dist(tmp_path / "pyodide-1.0.tar.bz2")
    monkeypatch.setattr(pyodide.cache.urllib.request, "urlopen", lambda url: pytest.fail("network used"))
    assert pyodide.download("1.0", tmp_path) == cached


def test_kernel_version_needs_the_kernel(monkeypatch):
    monkeypatch.setitem(sys.modules, "jupyterlite_pyodide_kernel", None)
    with pytest.raises(RuntimeError, match="pass --version"):
        pyodide.kernel_pyodide_version()


def test_cli_pyodide_dist(tmp_path, capsys):
    _dist(tmp_path / "pyodide-1.0.tar.bz2")
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["numpy>=2"]\n')
    main(
        [
            "pyodide-dist",
            "--version",
            "1.0",
            "--cache-dir",
            str(tmp_path),
            "--pyproject",
            str(tmp_path / "pyproject.toml"),
            "--keep",
            "wcwidth",
            "--out",
            str(tmp_path / "out.tar.bz2"),
        ]
    )
    assert capsys.readouterr().out == f"{(tmp_path / 'out.tar.bz2').resolve()}\n"
    with tarfile.open(tmp_path / "out.tar.bz2") as tar:
        wheels = sorted(n for n in tar.getnames() if n.endswith((".whl", ".metadata")))
    # project dependency (numpy), --keep (wcwidth) and the kernel's boot packages (ipython and its closure)
    assert wheels == [
        "pyodide/ipython-9.0-py3-none-any.whl",
        "pyodide/numpy-2.2-cp313-wasm32.whl",
        "pyodide/numpy-2.2-cp313-wasm32.whl.metadata",
        "pyodide/prompt_toolkit-3.0-py3-none-any.whl",
        "pyodide/pure_eval-0.2-py3-none-any.whl",
        "pyodide/wcwidth-0.2-py3-none-any.whl",
    ]

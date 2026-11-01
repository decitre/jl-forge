import base64
import hashlib
import io
import json
import zipfile

import pytest
from packaging.specifiers import SpecifierSet

from jl_forge import pyodide, wheels


def make_wheel(directory, name, version="1.0", requires=()):
    """A minimal pure-Python wheel with a valid RECORD."""
    dist = f"{name.replace('-', '_')}-{version}"
    path = directory / f"{dist}-py3-none-any.whl"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n" + "".join(
        f"Requires-Dist: {r}\n" for r in requires
    )
    files = {f"{name.replace('-', '_')}/__init__.py": b"", f"{dist}.dist-info/METADATA": metadata.encode()}
    record = (
        "".join(
            f"{n},sha256={base64.urlsafe_b64encode(hashlib.sha256(d).digest()).rstrip(b'=').decode()},{len(d)}\n"
            for n, d in files.items()
        )
        + f"{dist}.dist-info/RECORD,,\n"
    )
    with zipfile.ZipFile(path, "w") as zf:
        for n, d in {**files, f"{dist}.dist-info/RECORD": record.encode()}.items():
            zf.writestr(n, d)
    return path


def test_requires_and_strip_requires_keep_record_valid(tmp_path):
    wheel = make_wheel(tmp_path, "app", requires=["numpy>=2", "tqdm; extra == 'progress'"])
    assert [str(r) for r in wheels.requires(wheel)] == ["numpy>=2", 'tqdm; extra == "progress"']
    out = tmp_path / "out" / wheel.name
    out.parent.mkdir()
    wheels.strip_requires(wheel, out)
    assert wheels.requires(out) == []
    with zipfile.ZipFile(out) as zf:
        meta = zf.read("app-1.0.dist-info/METADATA")
        record = zf.read("app-1.0.dist-info/RECORD").decode()
    digest = base64.urlsafe_b64encode(hashlib.sha256(meta).digest()).rstrip(b"=").decode()
    assert f"app-1.0.dist-info/METADATA,sha256={digest},{len(meta)}" in record.splitlines()
    assert b"Version: 1.0" in meta


def test_pure_wheel_picks_newest_matching(monkeypatch):
    def wheel(name, yanked=False):
        return {"filename": name, "url": f"https://files/{name}", "yanked": yanked}

    releases = {
        "3.0": [wheel("x-3.0-py3-none-any.whl")],  # excluded by the specifier
        "2.1b1": [wheel("x-2.1b1-py3-none-any.whl")],  # prerelease
        "2.0": [wheel("x-2.0-cp313-cp313-manylinux.whl")],  # not pure
        "1.9": [wheel("x-1.9-py3-none-any.whl", yanked=True)],
        "1.8": [wheel("x-1.8-py3-none-any.whl"), {"filename": "x-1.8.tar.gz", "url": "u"}],
        "bogus version": [wheel("x-0-py3-none-any.whl")],
    }
    monkeypatch.setattr(
        wheels.urllib.request, "urlopen", lambda url: io.BytesIO(json.dumps({"releases": releases}).encode())
    )
    assert wheels.pure_wheel("x", SpecifierSet("<3")) == (
        "https://files/x-1.8-py3-none-any.whl",
        "x-1.8-py3-none-any.whl",
    )
    with pytest.raises(ValueError, match="no pure-Python wheel"):
        wheels.pure_wheel("x", SpecifierSet(">5"))


def test_bundle_follows_dependencies(tmp_path, monkeypatch):
    index = tmp_path / "index"
    index.mkdir()
    available = {
        "ipywidgets": make_wheel(
            index,
            "ipywidgets",
            "8.1",
            [
                "comm>=0.1",
                "traitlets",
                "colorama; sys_platform == 'win32'",
                "jupyterlab-widgets; python_version >= '3.12'",
                "extra-dep; extra == 'full'",
            ],
        ),
        "comm": make_wheel(index, "comm", "0.2"),
        "jupyterlab-widgets": make_wheel(index, "jupyterlab-widgets", "3.0"),
        "extra-dep": make_wheel(index, "extra-dep", "1.0"),
        "private": make_wheel(index, "private", "1.0", ["comm"]),
    }
    monkeypatch.setattr(wheels, "pure_wheel", lambda name, spec, index: (name, available[name].name))
    monkeypatch.setattr(wheels.cache, "download", lambda url, path: available[url])
    local = make_wheel(tmp_path, "inhouse", "2.0", ["unreachable-dep"])

    bundled = wheels.bundle(
        ["ipywidgets>=8", "private"],
        provided={"traitlets"},
        out_dir=tmp_path / "pypi",
        cache_dir=tmp_path / "cache",
        python_version="3.13.2",
        local_wheels=[local],
        strip={"inhouse"},
    )
    # traitlets provided by Pyodide, colorama for Windows only, extra-dep only with the [full] extra,
    # comm once, inhouse bundled without its dependencies
    assert sorted(w.name for w in bundled) == sorted(
        [
            "ipywidgets-8.1-py3-none-any.whl",
            "comm-0.2-py3-none-any.whl",
            "jupyterlab_widgets-3.0-py3-none-any.whl",
            "private-1.0-py3-none-any.whl",
            "inhouse-2.0-py3-none-any.whl",
        ]
    )
    assert wheels.requires(tmp_path / "pypi" / "inhouse-2.0-py3-none-any.whl") == []

    bundled = wheels.bundle(["ipywidgets[full]"], {"traitlets"}, tmp_path / "pypi2", tmp_path / "cache", "3.11.0")
    names = {w.name for w in bundled}
    assert "extra_dep-1.0-py3-none-any.whl" in names and "jupyterlab_widgets-3.0-py3-none-any.whl" not in names


def test_kernel_index_names(tmp_path):
    index = tmp_path / wheels.KERNEL_INDEX
    with pytest.raises(RuntimeError, match="not found"):
        wheels.kernel_index_names(tmp_path)
    index.parent.mkdir(parents=True)
    index.write_text('{"piplite": {}, "pyodide_kernel": {}, "widgetsnbextension": {}}')
    assert wheels.kernel_index_names(tmp_path) == {"piplite", "pyodide-kernel", "widgetsnbextension"}


def test_cached_lock_reads_the_release_once(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(pyodide, "download", lambda version, cache_dir: calls.append(version) or tmp_path / "x")
    monkeypatch.setattr(pyodide, "read_lock", lambda path: {"info": {"python": "3.13.2"}, "packages": {}})
    assert pyodide.cached_lock("1.0", tmp_path) == pyodide.cached_lock("1.0", tmp_path)
    assert calls == ["1.0"]

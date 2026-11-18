import base64
import hashlib
import io
import json
import shutil
import zipfile

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from jl_forge import pyodide, wheels
from jl_forge.cli import main

resolve = wheels.resolve


@pytest.fixture(autouse=True)
def no_solve(monkeypatch):
    """bundle() tests use a fake index; uv would hit the real one. resolve() is tested on its own."""
    monkeypatch.setattr(wheels, "resolve", lambda *args: {})


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


def test_required_names_evaluates_markers_and_requested_extras(tmp_path):
    make_wheel(tmp_path, "botocore", requires=["urllib3>=1.25", "jmespath", "awscrt; extra == 'crt'"])
    make_wheel(tmp_path, "boto3", requires=["botocore", "colorama; sys_platform == 'win32'"])
    make_wheel(tmp_path, "s3transfer", requires=["botocore[extra-x]", "dep-x; extra == 'other'"])
    make_wheel(tmp_path, "lib", requires=["numpy; extra == 'extra-x'"])
    make_wheel(tmp_path, "app", requires=["lib[extra-x]"])
    # urllib3 needed by botocore; awscrt only with botocore[crt], nobody asks for it; numpy via lib[extra-x]
    assert wheels.required_names(tmp_path, "3.13.2") == {"urllib3", "jmespath", "botocore", "lib", "numpy"}
    # a requirement of the project asks for botocore[crt]
    assert "awscrt" in wheels.required_names(tmp_path, "3.13.2", ["botocore[crt]>=1"])


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


def test_cli_pyodide_wheels_always_bundles_kernel_requirements(tmp_path, monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(
        pyodide, "cached_lock", lambda version, cache_dir: {"info": {"python": "3.13.2"}, "packages": {}}
    )
    monkeypatch.setattr(wheels, "kernel_index_names", lambda: set())
    monkeypatch.setattr(wheels, "bundle", lambda requirements, *a, **kw: seen.extend(requirements) or [])
    main(["pyodide-wheels", "--version", "1.0", "--out-dir", str(tmp_path), "--require", "tqdm"])
    assert seen == ["comm", "tqdm"]


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_resolve_rejects_conflicting_requirements_and_skips_provided(tmp_path):
    a = make_wheel(tmp_path, "a", "1.0", ["c<1", "traitlets>=99"])
    c = make_wheel(tmp_path, "c", "2.0")
    with pytest.raises(ValueError, match="conflicting"):
        resolve([str(a), str(c)], {"traitlets"}, "3.13.0")
    pins = resolve([str(make_wheel(tmp_path, "b", "1.0", ["traitlets>=99"]))], {"traitlets"}, "3.13.0")
    assert "traitlets" not in pins


def test_bundle_falls_back_to_secondary_index(tmp_path, monkeypatch):
    wheel = make_wheel(tmp_path, "private", "1.0")

    def pure_wheel(name, spec, index):
        if index != "https://intranet/pypi":
            raise ValueError("not here")
        return name, wheel.name

    monkeypatch.setattr(wheels, "pure_wheel", pure_wheel)
    monkeypatch.setattr(wheels.cache, "download", lambda url, path: wheel)
    bundled = wheels.bundle(
        ["private"],
        set(),
        tmp_path / "out",
        tmp_path / "cache",
        "3.13.0",
        indexes=(wheels.PYPI, "https://intranet/pypi"),
    )
    assert [w.name for w in bundled] == [wheel.name]


def test_bundle_rejects_requirement_the_distribution_cannot_satisfy(tmp_path, monkeypatch):
    wheel = make_wheel(tmp_path, "needs-numpy", "1.0", ["numpy>=3"])
    monkeypatch.setattr(wheels, "pure_wheel", lambda name, spec, index: (name, wheel.name))
    monkeypatch.setattr(wheels.cache, "download", lambda url, path: wheel)
    args = (["needs-numpy"], {"numpy"}, tmp_path / "out", tmp_path / "cache", "3.13.0")
    with pytest.raises(ValueError, match=r"numpy>=3.*provides numpy 2\.0"):
        wheels.bundle(*args, provided_versions={"numpy": Version("2.0")})
    assert wheels.bundle(*args, provided_versions={"numpy": Version("3.1")})


def test_resolve_needs_uv(monkeypatch):
    monkeypatch.setattr(wheels.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="uv not found"):
        resolve(["a"], set(), "3.13.0")


def test_bundle_reports_every_index_that_failed(tmp_path, monkeypatch):
    def pure_wheel(name, spec, index):
        raise ValueError(f"not on {index}")

    monkeypatch.setattr(wheels, "pure_wheel", pure_wheel)
    with pytest.raises(ValueError, match="not on a; not on b"):
        wheels.bundle(["x"], set(), tmp_path / "out", tmp_path / "cache", "3.13.0", indexes=("a", "b"))


def test_lock_versions_canonicalizes_names_and_skips_unparsable():
    lock = {"packages": {"Typing_Extensions": {"version": "4.12.2"}, "odd": {"version": "not a version"}}}
    assert pyodide.lock_versions(lock) == {"typing-extensions": Version("4.12.2")}

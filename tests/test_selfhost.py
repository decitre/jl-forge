import io
import tarfile

import pytest

from jl_forge import selfhost
from jl_forge.cli import main


@pytest.fixture
def downloads(tmp_path, monkeypatch):
    """Serve the mapping and a Font Awesome package from local files instead of the network."""
    mapping = tmp_path / "dl" / "compressed_mapping.json"
    mapping.parent.mkdir()
    mapping.write_text("{}")
    tgz = tmp_path / "dl" / "fontawesome.tgz"
    with tarfile.open(tgz, "w:gz") as tar:
        for name in [
            "package/css/all.min.css",
            "package/css/v4-shims.min.css",
            "package/LICENSE.txt",
            "package/webfonts/fa-solid-900.woff2",
            "package/webfonts/fa-solid-900.ttf",
            "package/js/all.js",
        ]:
            info = tarfile.TarInfo(name)
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))
    files = {selfhost.MAPPING_URL.decode(): mapping, selfhost.FONTAWESOME_TGZ: tgz}
    monkeypatch.setattr(selfhost.cache, "download", lambda url, path: files[url])


def _site(root):
    (root / "lab").mkdir(parents=True)
    (root / "voici" / "render").mkdir(parents=True)
    (root / "ext" / "static").mkdir(parents=True)
    (root / "jupyter-lite.json").write_text("{}")
    (root / "lab" / "index.html").write_text("<html></html>")
    (root / "voici" / "render" / "demo.html").write_text(
        f'<link href="{selfhost.FONTAWESOME_CDN.decode()}css/all.min.css">'
    )
    (root / "ext" / "static" / "worker.js").write_text(f'fetch("{selfhost.MAPPING_URL.decode()}")')
    return root


def test_self_host_rewrites_and_places_files(tmp_path, downloads):
    site = _site(tmp_path / "public" / "xeus")
    assert len(selfhost.self_host(site, tmp_path / "cache")) == 2
    assert (site / "ext" / "static" / "worker.js").read_text() == 'fetch("compressed_mapping.json")'
    for d in ["lab", "voici/render", "ext/static"]:  # pages and the worker resolve it relative to themselves
        assert (site / d / selfhost.MAPPING).exists()
    assert (
        site / "voici/render/demo.html"
    ).read_text() == '<link href="../../static/fontawesome-free/css/all.min.css">'
    fa = site / selfhost.FONTAWESOME_DIR
    assert sorted(str(p.relative_to(fa)) for p in fa.rglob("*") if p.is_file()) == [
        "LICENSE.txt",
        "css/all.min.css",
        "css/v4-shims.min.css",
        "webfonts/fa-solid-900.woff2",
    ]
    assert selfhost.self_host(site, tmp_path / "cache") == []  # nothing left to do


def test_cli_self_host(tmp_path, downloads, capsys):
    _site(tmp_path / "public" / "xeus")
    main(["self-host", str(tmp_path / "public"), "--cache-dir", str(tmp_path / "cache")])
    assert "Font Awesome served for 1 pages" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["self-host", str(tmp_path / "public" / "xeus" / "lab")])

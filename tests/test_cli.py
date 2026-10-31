import pytest

from jl_forge.cli import reset_workspace


def test_reset_workspace(tmp_path):
    ws = tmp_path / "workspace"
    (ws / "old").mkdir(parents=True)
    reset_workspace(ws, tmp_path)
    assert ws.is_dir() and not any(ws.iterdir())


@pytest.mark.parametrize("target", [".", "..", "../sibling"])
def test_reset_workspace_refuses_outside_root(tmp_path, target):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ValueError, match="not strictly inside"):
        reset_workspace(root / target, root)


def test_reset_workspace_refuses_project_dir(tmp_path):
    (tmp_path / "sub" / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="project directory"):
        reset_workspace(tmp_path / "sub", tmp_path)
    assert (tmp_path / "sub" / ".git").exists()


def test_site_urls(tmp_path):
    from jl_forge.cli import site_urls

    (tmp_path / "index.html").touch()
    for site, apps in {"xeus": ["lab", "notebooks"], "pyodide": ["lab"]}.items():
        for app in apps:
            (tmp_path / site / app).mkdir(parents=True)
            (tmp_path / site / app / "index.html").touch()
        (tmp_path / site / "jupyter-lite.json").touch()
        (tmp_path / site / "files" / "sub").mkdir(parents=True)
        (tmp_path / site / "files" / "demo.ipynb").touch()
        (tmp_path / site / "files" / "sub" / "a b.ipynb").touch()
    (tmp_path / "xeus" / "voici" / "render").mkdir(parents=True)
    (tmp_path / "xeus" / "voici" / "render" / "demo.html").touch()
    base = "http://localhost:8000"
    assert site_urls(tmp_path) == [
        f"{base}/",
        f"{base}/pyodide/lab/index.html?path=demo.ipynb",
        f"{base}/pyodide/lab/index.html?path=sub/a%20b.ipynb",
        f"{base}/xeus/lab/index.html?path=demo.ipynb",
        f"{base}/xeus/notebooks/index.html?path=demo.ipynb",
        f"{base}/xeus/voici/render/demo.html",
        f"{base}/xeus/lab/index.html?path=sub/a%20b.ipynb",
        f"{base}/xeus/notebooks/index.html?path=sub/a%20b.ipynb",
    ]
    assert site_urls(tmp_path / "xeus", base + "/")[0] == f"{base}/lab/index.html?path=demo.ipynb"

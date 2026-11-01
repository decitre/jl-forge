import os

import pytest

from jl_forge import artifact
from jl_forge.cli import main


def _tree(root):
    for path, data in {"a/x.js": b"same", "b/x.js": b"same", "b/y.js": b"other", "c/z.js": b"same", "e": b""}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(data)
    (root / "d").mkdir()
    (root / "d" / "e2").write_bytes(b"")  # empty files aren't linked
    return root


def test_dedup_links_identical_files(tmp_path):
    root = _tree(tmp_path)
    assert artifact.size(root) == (17, 17)  # 3 x 'same' + 'other'
    assert artifact.dedup(root) == (2, 8)
    assert os.path.samefile(root / "a/x.js", root / "c/z.js") and (root / "c/z.js").read_bytes() == b"same"
    assert not os.path.samefile(root / "a/x.js", root / "b/y.js")
    assert artifact.size(root) == (17, 9)
    assert artifact.dedup(root) == (0, 0)
    assert not list(root.rglob("*.jl-forge-link"))


@pytest.mark.parametrize(
    ("text", "n"),
    [("1G", 1024**3), ("1000M", 1000 * 1024**2), ("500kb", 500 * 1024), ("2.5MiB", int(2.5 * 1024**2)), ("123", 123)],
)
def test_parse_size(text, n):
    assert artifact.parse_size(text) == n


def test_parse_size_rejects_garbage():
    with pytest.raises(ValueError):
        artifact.parse_size("1T")


def test_cli_size_limit(tmp_path, capsys):
    root = _tree(tmp_path)
    main(["dedup", str(root)])
    main(["size", str(root), "--max", "9", "--links-once"])
    assert "counting hardlinked files once" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["size", str(root), "--max", "9"])  # every copy counts by default

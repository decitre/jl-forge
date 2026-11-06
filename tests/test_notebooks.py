from jl_forge.cli import main
from jl_forge.notebooks import prepend_to_first_code_cell, read, strip, write


def _nb():
    return {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# t"]},
            {
                "cell_type": "code",
                "metadata": {},
                "source": "x = 1\ny = 2",
                "outputs": [{"x": 1}],
                "execution_count": 3,
            },
        ],
        "metadata": {"widgets": {}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def test_strip_only_touches_code_cells():
    nb = strip(_nb())
    assert nb["cells"][0] == {"cell_type": "markdown", "metadata": {}, "source": ["# t"]}
    assert nb["cells"][1]["outputs"] == [] and nb["cells"][1]["execution_count"] is None
    assert "widgets" not in nb["metadata"]


def test_prepend_is_idempotent_and_roundtrips(tmp_path):
    nb = _nb()
    assert prepend_to_first_code_cell(nb, "import x")
    assert prepend_to_first_code_cell(nb, "import x\n")
    assert nb["cells"][1]["source"] == ["import x\n", "x = 1\n", "y = 2"]
    path = tmp_path / "a.ipynb"
    write(path, nb)
    assert read(path) == nb


def test_prepend_without_code_cell():
    assert not prepend_to_first_code_cell({"cells": [{"cell_type": "markdown", "source": []}]}, "x")


def test_cli_notebooks_recurses_into_subdirectories(tmp_path, capsys):
    for rel in ("top.ipynb", "ch1/sub.ipynb", ".ipynb_checkpoints/top-checkpoint.ipynb"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        write(tmp_path / rel, _nb())
    main(["notebooks", str(tmp_path), "--strip", "--prepend", "x"])
    assert capsys.readouterr().out == "Prepared: ch1/sub.ipynb\nPrepared: top.ipynb\n"
    code = read(tmp_path / "ch1/sub.ipynb")["cells"][1]
    assert code["outputs"] == [] and code["source"][0] == "x\n"
    assert read(tmp_path / ".ipynb_checkpoints/top-checkpoint.ipynb")["cells"][1]["outputs"]

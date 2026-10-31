from jl_forge.dependencies import collect_requirements, to_specs


def test_merges_constraints_and_canonicalizes_names():
    project = {
        "dependencies": ["Requests>=2", "numpy[extra]>=1.20; python_version>='3'"],
        "optional-dependencies": {"lab": ["requests<3", "My_Pkg==1.0"]},
    }
    reqs = collect_requirements(project, ["lab", "missing"], baseline=["xeus-python"])
    assert to_specs(reqs) == ["xeus-python", "requests<3,>=2", "numpy>=1.20", "my-pkg==1.0"]


def test_markers_evaluated_for_emscripten_and_exclude():
    project = {"dependencies": ["pywin32; sys_platform == 'win32'", "pyodide-only; sys_platform == 'emscripten'", "aiohttp"]}
    assert to_specs(collect_requirements(project, exclude={"AIOHTTP"})) == ["pyodide-only"]

"""Tiny package mounted (xeus) or installed as a wheel (Pyodide) in the demo site."""

import platform
import sys
from importlib.util import find_spec

from packaging.version import Version


def kernel_info() -> str:
    kind = "xeus-python" if find_spec("pyjs") else "pyodide"  # xeus-python also has a pyodide module
    return f"{kind} on {sys.platform}, Python {Version(platform.python_version())}"

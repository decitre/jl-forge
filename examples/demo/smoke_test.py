# Copyright 2026 Emmanuel Decitre
# SPDX-License-Identifier: Apache-2.0

"""Browser smoke test of the built demo: each app runs demo.ipynb in each kernel.

Run after build.sh, from the repository root:

    uv run --group browser pytest examples/demo/smoke_test.py

Needs Google Chrome installed (Playwright's "chrome" channel).
"""

import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

PUBLIC = Path(__file__).parent / "workspace" / "public"
KERNEL_INFO = re.compile(r"(xeus-python|pyodide) on emscripten, Python 3\.\d+\.\d+")
KERNEL_START_MS = 240_000  # first load downloads the kernel and its packages
WIDGET_MS = 60_000

# (site, app page, kernel reported by the notebook, `with output:` capture works)
PAGES = [
    ("xeus", "lab/index.html?path=demo.ipynb", "xeus-python", True),
    ("xeus", "notebooks/index.html?path=demo.ipynb", "xeus-python", True),
    ("xeus", "voici/render/demo.html", "xeus-python", False),  # voici#127, see docs/COMPATIBILITY.md
    ("pyodide", "lab/index.html?path=demo.ipynb", "pyodide", True),
    ("pyodide", "notebooks/index.html?path=demo.ipynb", "pyodide", True),
    ("pyodide", "voici/render/demo.html", "pyodide", True),
]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    if not (PUBLIC / "index.html").is_file():
        pytest.skip(f"{PUBLIC} not built; run examples/demo/build.sh first")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=PUBLIC))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    yield page
    page.close()
    if errors:
        print("console errors:", *errors[-5:], sep="\n  ")


def _run_all_cells(page: Page) -> None:
    page.wait_for_selector(".jp-CodeCell", timeout=KERNEL_START_MS)
    page.click("li.lm-MenuBar-item:has-text('Run')")
    page.click("li.lm-Menu-item:has-text('Run All Cells')")  # queued until the kernel is ready


@pytest.mark.parametrize(("site", "path", "kernel", "capture_works"), PAGES, ids=[f"{s}-{p.split('/')[0]}" for s, p, *_ in PAGES])
def test_demo_notebook(page, base_url, site, path, kernel, capture_works):
    page.goto(f"{base_url}/{site}/{path}")
    if not path.startswith("voici/"):  # Voici runs the notebook on load
        _run_all_cells(page)

    page.wait_for_function("re => new RegExp(re).test(document.body.innerText)", arg=KERNEL_INFO.pattern, timeout=KERNEL_START_MS)
    assert KERNEL_INFO.search(page.inner_text("body")).group(1) == kernel

    button = page.locator("button.jupyter-button", has_text="Click me")
    button.wait_for(timeout=WIDGET_MS)
    button.click()
    page.locator(".widget-label", has_text=re.compile(r"^clicked$")).wait_for(timeout=WIDGET_MS)
    page.locator(".widget-output", has_text="appended from the callback").wait_for(timeout=WIDGET_MS)

    captured = page.locator(".widget-output", has_text="captured from the callback")
    if capture_works:
        captured.wait_for(timeout=WIDGET_MS)
    else:
        page.wait_for_timeout(10_000)
        assert captured.count() == 0, "`with output:` capture now works here: update PAGES and docs/COMPATIBILITY.md"

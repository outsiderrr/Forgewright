"""Browser smoke test (T-3.6a / v1.0 F16 mandatory).

Boots the FastAPI app on a real ephemeral port via uvicorn, drives it
with Playwright headless Chromium, and verifies:

  * the index page renders
  * ``/api/scenes`` populates the left nav
  * a click selects a scene and renders the mermaid graph as ``<svg>``
  * the validator panel + A/R/S buttons are present

Skipped (not failed) if Playwright isn't installed — local dev opt-in.
For the A-phase deliverable, install with:

    pip install playwright
    python -m playwright install chromium

Screenshots are saved under ``--screenshot-dir`` (default
``tools/review_ui/tests/_screenshots/``) for the PR description.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from contextlib import closing
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright

import uvicorn  # noqa: E402  — only after the importorskip gate

from tools.review_ui.server import build_app  # noqa: E402


SCREENSHOT_DIR = Path(__file__).resolve().parent / "_screenshots"


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _UvicornInThread:
    def __init__(self, app, host: str, port: int) -> None:
        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.host = host
        self.port = port

    def __enter__(self) -> "_UvicornInThread":
        self.thread.start()
        for _ in range(50):
            if self.server.started:
                return self
            time.sleep(0.1)
        raise RuntimeError("uvicorn did not start within 5s")

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


@pytest.fixture
def live_server(fixture_batch_dir: Path, fixture_scenes_dir: Path):
    app = build_app(batch_dir=fixture_batch_dir, scenes_dir=fixture_scenes_dir)
    port = _free_port()
    with _UvicornInThread(app, "127.0.0.1", port) as srv:
        yield f"http://{srv.host}:{srv.port}"


def _ensure_screenshot_dir() -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOT_DIR


def test_browser_smoke_full_walk(live_server: str) -> None:
    """End-to-end smoke: load index, click scene, verify mermaid SVG, screenshot."""
    out = _ensure_screenshot_dir()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover — env-dependent
            pytest.skip(f"chromium not installed for playwright: {exc}")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        console_msgs: list[str] = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

        page.goto(live_server)
        page.wait_for_selector("#scene-list .scene-row", timeout=10_000)

        # View 1: scene list (full app first paint)
        page.screenshot(path=str(out / "01_scene_list.png"), full_page=True)

        # View 2: graph view — click the s_alpha row, wait for mermaid SVG
        page.click("text=s_alpha")
        page.wait_for_selector(
            "#graph-container svg", timeout=10_000,
            state="attached",
        )
        # mermaid badge should reflect render source
        badge_text = page.text_content("#graph-source-badge")
        assert badge_text and "graph:" in badge_text, badge_text
        assert "vendor" in badge_text or "cdn" in badge_text or "fallback" in badge_text, badge_text
        page.screenshot(path=str(out / "02_graph_mermaid_svg.png"), full_page=True)

        # View 3: validator panel — switch to topology tab + ensure JSON content
        page.click("#validator-tabs .tab[data-tab='topology']")
        topo = page.text_content("#validator-topology")
        assert topo and "pure_topology_pass" in topo, topo
        page.screenshot(path=str(out / "03_validator_topology.png"), full_page=True)

        # View 4: A/R/S panel — type a reject reason, screenshot ready-to-submit state
        page.fill("#reject-reason", "smoke test reject reason (not submitted)")
        page.screenshot(path=str(out / "04_review_ars.png"), full_page=True)

        # Bonus: ASCII fallback view also renders (covers F17 fallback path)
        page.click(".format-btn[data-format='ascii']")
        page.wait_for_selector("#graph-container pre", timeout=5_000)
        page.screenshot(path=str(out / "05_graph_ascii_fallback.png"), full_page=True)

        # Persist the console log alongside the screenshots for the PR description.
        (out / "console.log").write_text("\n".join(console_msgs), encoding="utf-8")

        browser.close()


def test_browser_smoke_review_post_persists(live_server: str, fixture_batch_dir: Path) -> None:
    """Drive the A button end-to-end and verify the JSONL log gains a row."""
    log_path = fixture_batch_dir / "scene_review_log.jsonl"
    assert not log_path.exists()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"chromium not installed for playwright: {exc}")
        page = browser.new_page()
        page.goto(live_server)
        page.wait_for_selector("#scene-list .scene-row")
        page.click("text=s_alpha")
        page.wait_for_selector("#btn-accept:not([disabled])")
        page.click("#btn-accept")
        # The flash message becomes "已写入 scene_review_log.jsonl" once the POST round-trips.
        page.wait_for_selector("#review-flash.success", timeout=5_000)
        browser.close()
    rows = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(r.get("scene_id") == "s_alpha" and r.get("accepted") is True for r in rows)

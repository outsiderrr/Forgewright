"""Browser smoke test (T-3.6a / v1.0 F16 mandatory).

Boots the FastAPI app on a real ephemeral port via uvicorn, drives it
with Playwright headless Chromium, and verifies the four MVP views plus
the review C-phase regression matrix:

  * mermaid SVG actually renders (DOM ``<svg>``)
  * vendor + ASCII fallback paths both reachable
  * `[A]` / `[R]` / `[S]` all round-trip into ``scene_review_log.jsonl``
  * content/ scenes leave A/R/S disabled (review C-3.1 read-only gate)

Skipped (not failed) if Playwright isn't installed — local dev opt-in.
For the A-phase deliverable, install with:

    pip install playwright
    python -m playwright install chromium-headless-shell

Screenshots are saved under ``tools/review_ui/tests/_screenshots/`` for
the PR description.
"""
from __future__ import annotations

import json
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


@pytest.fixture
def live_server_full(
    fixture_batch_with_playtest: Path,
    fixture_scenes_dir: Path,
    fixture_visuals: Path,
    fixture_ontology: Path,
):
    """Live uvicorn for T-3.6b integrations (visuals + playtest + ontology)."""
    from tools.review_ui.data import ReviewDataLoader

    loader = ReviewDataLoader(
        batch_dir=fixture_batch_with_playtest,
        scenes_dir=fixture_scenes_dir,
        visuals_dir=fixture_visuals,
        ontology_path=fixture_ontology,
    )
    app = build_app(batch_dir=fixture_batch_with_playtest, scenes_dir=fixture_scenes_dir)
    app.state.loader = loader
    port = _free_port()
    with _UvicornInThread(app, "127.0.0.1", port) as srv:
        yield f"http://{srv.host}:{srv.port}"


def _ensure_screenshot_dir() -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOT_DIR


def _launch(p):
    try:
        return p.chromium.launch(headless=True)
    except Exception as exc:  # pragma: no cover — env-dependent
        pytest.skip(f"chromium not installed for playwright: {exc}")


def test_browser_smoke_full_walk(live_server: str) -> None:
    """End-to-end smoke: load index, click scene, verify mermaid SVG, screenshot."""
    out = _ensure_screenshot_dir()
    with sync_playwright() as p:
        browser = _launch(p)
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
        page.wait_for_selector("#graph-container svg", timeout=10_000, state="attached")
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

        # F17 fallback: ASCII view also renders
        page.click(".format-btn[data-format='ascii']")
        page.wait_for_selector("#graph-container pre", timeout=5_000)
        page.screenshot(path=str(out / "05_graph_ascii_fallback.png"), full_page=True)

        (out / "console.log").write_text("\n".join(console_msgs), encoding="utf-8")
        browser.close()


def test_browser_smoke_arsk_round_trips(live_server: str, fixture_batch_dir: Path) -> None:
    """Review C-3.2 + C-4.1 — `[A]`, `[R]`, `[S]` all persist + status reflects.

    Walks the matrix in one session so the test enumerates every button
    that the prior smoke skipped (only `[A]` was covered before).
    """
    log_path = fixture_batch_dir / "scene_review_log.jsonl"
    assert not log_path.exists()
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page()
        page.goto(live_server)
        page.wait_for_selector("#scene-list .scene-row")

        # 1. Accept s_alpha
        page.click("text=s_alpha")
        page.wait_for_selector("#btn-accept:not([disabled])")
        page.click("#btn-accept")
        page.wait_for_selector("#review-flash.success", timeout=5_000)
        # The auto-advance flips selection; reselect s_alpha to issue [R].
        page.wait_for_timeout(900)  # let the 700ms setTimeout(nextScene) settle
        page.click("text=s_alpha")
        page.wait_for_selector("#btn-reject:not([disabled])")

        # 2. Reject s_alpha
        page.fill("#reject-reason", "smoke: reject pacing")
        page.click("#btn-reject")
        page.wait_for_selector("#review-flash.success", timeout=5_000)
        page.wait_for_timeout(900)
        page.click("text=s_alpha")
        page.wait_for_selector("#btn-skip:not([disabled])")

        # 3. Skip s_alpha (review C-3.2: must POST + persist accepted=null)
        page.fill("#reject-reason", "smoke: defer to next session")
        page.click("#btn-skip")
        page.wait_for_selector("#review-flash.success", timeout=5_000)
        page.wait_for_timeout(900)

        browser.close()

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    accepted = [r for r in rows if r.get("scene_id") == "s_alpha" and r.get("accepted") is True]
    rejected = [r for r in rows if r.get("scene_id") == "s_alpha" and r.get("accepted") is False]
    skipped = [r for r in rows if r.get("scene_id") == "s_alpha" and r.get("accepted") is None]
    assert accepted and accepted[-1]["scene_id"] == "s_alpha"
    assert rejected and rejected[-1]["reason"] == "smoke: reject pacing"
    assert skipped and skipped[-1]["reason"] == "smoke: defer to next session"


def test_browser_smoke_unreviewable_disables_buttons(live_server: str) -> None:
    """Review C-3.1 — UI must disable A/R/S for content scenes + failed batch rows."""
    out = _ensure_screenshot_dir()
    with sync_playwright() as p:
        browser = _launch(p)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(live_server)
        page.wait_for_selector("#scene-list .scene-row")

        def open_scene_via_nav(scene_id: str) -> None:
            page.click(f".scene-row[data-scene-id='{scene_id}']")
            # Wait for the detail panel to swap to the new scene_id; the title
            # reflects what's actually loaded, so we poll on it.
            page.wait_for_function(
                "id => document.getElementById('scene-title').textContent.includes(id)",
                arg=scene_id,
                timeout=5_000,
            )

        # Content scene: demo_scene
        open_scene_via_nav("demo_scene")
        page.wait_for_selector("#not-reviewable-note:not([style*='display: none'])", timeout=5_000)
        for sel in ("#btn-accept", "#btn-reject", "#btn-skip"):
            assert page.get_attribute(sel, "disabled") is not None, sel
        note = page.text_content("#not-reviewable-note") or ""
        assert "content/" in note, note
        page.screenshot(path=str(out / "06_review_disabled_content.png"), full_page=True)

        # Failed batch row: iter_1 (fixture_batch_dir failure envelope)
        open_scene_via_nav("iter_1")
        page.wait_for_function(
            "() => (document.getElementById('not-reviewable-note').textContent || '').includes('failed batch row')",
            timeout=5_000,
        )
        for sel in ("#btn-accept", "#btn-reject", "#btn-skip"):
            assert page.get_attribute(sel, "disabled") is not None, sel
        note = page.text_content("#not-reviewable-note") or ""
        assert "failed batch row" in note, note
        page.screenshot(path=str(out / "07_review_disabled_failed.png"), full_page=True)

        browser.close()


# ---------------------------------------------------------------------------
# T-3.6b RUI-INT-5: integrations smoke + 5-view screenshots (mandatory).
# ---------------------------------------------------------------------------


def test_browser_smoke_integrations_full_walk(live_server_full: str) -> None:
    """End-to-end smoke for the four T-3.6b integrations.

    Walks every panel that ships in this PR:

      1. Visual asset thumbnails (right pane)
      2. Playtest panel — populated path (s_alpha → playtest_001/)
      3. Playtest panel — F13 degrade (a scene with no run)
      4. Stale list (refresh with changed_ontology_ids → demo_scene flagged)
      5. Chapter / act tree in the left nav (toggle from list view)

    Saves screenshots under ``_screenshots/`` for the PR description.
    """
    out = _ensure_screenshot_dir()
    with sync_playwright() as p:
        browser = _launch(p)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        console_msgs: list[str] = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

        page.goto(live_server_full)
        page.wait_for_selector("#scene-list .scene-row", timeout=10_000)

        # --- View 1: visuals (RUI-INT-1) — click s_alpha, wait for thumbnails
        page.click("text=s_alpha")
        page.wait_for_selector("#visuals-content .visual-card img", timeout=10_000)
        # Both groups must render
        assert page.text_content("#visuals-content").strip().count("出场角色") + \
               page.text_content("#visuals-content").strip().count("场景背景") >= 2
        page.screenshot(path=str(out / "08_visuals.png"), full_page=True)

        # --- View 2: playtest with data (RUI-INT-2)
        page.click("#main-tabs .tab[data-tab='playtest']")
        page.wait_for_selector(".playtest-header", timeout=10_000)
        playtest_text = page.text_content("#playtest-panel") or ""
        assert "playtest_001" in playtest_text, playtest_text
        assert "p001" in playtest_text or "p002" in playtest_text
        page.screenshot(path=str(out / "09_playtest_populated.png"), full_page=True)

        # --- View 3: playtest F13 degrade — open demo_scene (no playtest run)
        page.click(".scene-row[data-scene-id='demo_scene']")
        page.wait_for_function(
            "() => document.getElementById('scene-title').textContent.includes('demo_scene')",
            timeout=5_000,
        )
        page.click("#main-tabs .tab[data-tab='playtest']")
        page.wait_for_selector(".playtest-empty", timeout=10_000)
        empty_text = page.text_content("#playtest-panel") or ""
        assert "未跑 playtest" in empty_text, empty_text
        assert "python -m generator.playtest" in empty_text
        page.screenshot(path=str(out / "10_playtest_degrade.png"), full_page=True)

        # --- View 4: stale list (RUI-INT-3) — open the panel + refresh
        page.evaluate("document.getElementById('stale-panel').open = true")
        page.fill("#stale-ontology", "char_vellin")
        page.click("#stale-refresh")
        page.wait_for_selector(".stale-item .stale-item-link", timeout=10_000)
        stale_html = page.text_content("#stale-list") or ""
        assert "demo_scene" in stale_html, stale_html
        # Toggle badge should reflect non-zero count
        toggle_text = page.text_content("#stale-toggle") or ""
        assert "Stale (1)" in toggle_text or "Stale (1" in toggle_text, toggle_text
        # Click the stale link → scene-main shows the red banner
        page.click(".stale-item .stale-item-link")
        page.wait_for_selector("#stale-banner:not([hidden])", timeout=5_000)
        banner_text = page.text_content("#stale-banner") or ""
        assert "stale" in banner_text.lower(), banner_text
        page.screenshot(path=str(out / "11_stale_list_and_banner.png"), full_page=True)

        # --- View 5: chapter / act grouping (RUI-INT-4)
        page.click("#nav-mode .nav-btn[data-nav='chapter']")
        page.wait_for_selector("#scene-tree .chapter-group", timeout=5_000)
        tree_text = page.text_content("#scene-tree") or ""
        assert "chap_intro" in tree_text, tree_text
        assert "act_arrival" in tree_text, tree_text
        # s_alpha (with scene_anchor=scene_alpha) must appear under the act
        assert "s_alpha" in tree_text, tree_text
        # Click s_alpha from the chapter view to verify the chapter link header.
        # Wait on title + link content rather than visibility — selectScene is
        # async and the link can briefly render with the previous scene's data.
        page.click("#scene-tree .scene-row[data-scene-id='s_alpha']")
        page.wait_for_function(
            "() => (document.getElementById('scene-chapter-link').textContent || '').includes('chap_intro')",
            timeout=5_000,
        )
        link_text = page.text_content("#scene-chapter-link") or ""
        assert "chap_intro" in link_text, link_text
        page.screenshot(path=str(out / "12_chapter_tree.png"), full_page=True)

        (out / "console_integrations.log").write_text(
            "\n".join(console_msgs), encoding="utf-8"
        )
        browser.close()
